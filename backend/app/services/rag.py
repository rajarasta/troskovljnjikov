"""RAG service for BoQ item search using ChromaDB + sentence-transformers.

Supports dual-level indexing:
- Composite units: indexed by parent_description (search entity)
- Simple items: indexed by fullDescription (direct match)
"""
from __future__ import annotations

import logging
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "boq_items"
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_client = chromadb.PersistentClient(path="./data/chromadb")
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=_MODEL_NAME)
_collection = None


def _get_collection():
    """Get or recreate the ChromaDB collection (resilient to external deletion)."""
    global _collection
    if _collection is not None:
        try:
            _collection.count()
            return _collection
        except Exception:
            logger.warning("ChromaDB collection stale, recreating...")
            _collection = None
    _collection = _client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=_ef,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def _build_chunk(item: dict[str, Any], parent_desc: str | None = None) -> str:
    """Build a structured text chunk from a BoQ item."""
    parts: list[str] = []
    if parent_desc:
        parts.append(f"[Section: {parent_desc}]")
    num = item.get("itemNumber") or ""
    desc = item.get("description", "")
    full = item.get("fullDescription") or ""
    if num:
        parts.append(f"{num}. {desc}")
    else:
        parts.append(desc)
    if full and len(full) > len(desc):
        parts.append(full)
    unit = item.get("unit") or ""
    qty = item.get("quantity", 0)
    if unit or qty:
        parts.append(f"Unit: {unit} | Qty: {qty}")
    return "\n".join(parts)


def index_items(
    file_id: str,
    items: list[dict[str, Any]],
    parent_map: dict[str, str] | None = None,
) -> int:
    """Embed and store BoQ items in ChromaDB. Returns count indexed.

    Backward-compatible entry point — indexes all items as before.
    """
    if not items:
        return 0
    parent_map = parent_map or {}
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    for item in items:
        item_id = item.get("id") or f"{file_id}:{item.get('sheetName', '')}:{item['row']}"
        parent_desc = parent_map.get(item.get("parentItemNumber", ""))
        chunk = _build_chunk(item, parent_desc)
        ids.append(item_id)
        documents.append(chunk)
        metadatas.append({
            "file_id": file_id,
            "unit": item.get("unit") or "",
            "item_number": item.get("itemNumber") or "",
            "unit_price": float(item.get("unitPrice") or 0),
            "quantity": float(item.get("quantity") or 0),
        })
    _get_collection().upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def index_for_search(
    file_id: str,
    items: list[dict[str, Any]],
    units: list[dict[str, Any]],
    file_date: str | None = None,
) -> int:
    """Dual-level indexing for price history search.

    - Composite units: embed parent_description, ID = unit:{file_id}:{unit_id}
    - Simple items (not composite subs): embed fullDescription, ID = item:{file_id}:{item_id}
    - Skips: section headers, composite sub-items, subtotal rows

    Returns count indexed.
    """
    if not items and not units:
        return 0

    # Build set of parent numbers from units (for identifying composite sub-items)
    unit_parent_numbers = {u.get("parentItemNumber", "") for u in units}

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    # Build lookup of unit_id -> child item IDs for enrichment
    unit_item_ids: dict[str, set[str]] = {}
    for unit in units:
        uid = unit.get("id", "")
        unit_item_ids[uid] = set(unit.get("itemIds") or [])

    # Index composite units by enriched description (parent + sub-item summaries)
    for unit in units:
        parent_desc = unit.get("parentDescription") or unit.get("parentTitle") or ""
        if not parent_desc.strip():
            continue
        unit_id = unit.get("id", "")
        doc_id = f"unit:{file_id}:{unit_id}"

        # Enrich with sub-item descriptions
        child_ids = unit_item_ids.get(unit_id, set())
        sub_descs: list[str] = []
        for item in items:
            item_id = item.get("id") or f"{file_id}:{item.get('sheetName', '')}:{item['row']}"
            if item_id in child_ids:
                desc = (item.get("description") or "").strip()
                if desc:
                    sub_descs.append(desc)
        unit_doc = parent_desc
        if sub_descs:
            unit_doc = f"{parent_desc}\n{' | '.join(sub_descs)}"

        ids.append(doc_id)
        documents.append(unit_doc)
        metadatas.append({
            "file_id": file_id,
            "entity_type": "unit",
            "unit_id": unit_id,
            "file_date": file_date or "",
            "unit": "",
            "item_number": unit.get("parentItemNumber", ""),
            "unit_price": 0.0,
            "quantity": 0.0,
        })

    # Index composite_sub items individually (previously skipped)
    for item in items:
        item_type = item.get("itemType", "simple")
        if item_type != "composite_sub":
            continue
        item_id = item.get("id") or f"{file_id}:{item.get('sheetName', '')}:{item['row']}"
        doc_id = f"sub:{file_id}:{item_id}"
        full_desc = item.get("fullDescription") or item.get("description", "")
        if not full_desc.strip():
            continue
        ids.append(doc_id)
        documents.append(full_desc)
        metadatas.append({
            "file_id": file_id,
            "entity_type": "item",
            "item_id": item_id,
            "file_date": file_date or "",
            "unit": item.get("unit") or "",
            "item_number": item.get("itemNumber") or "",
            "unit_price": float(item.get("unitPrice") or 0),
            "quantity": float(item.get("quantity") or 0),
        })

    # Index simple items (skip composite sub-items and section headers)
    for item in items:
        item_type = item.get("itemType", "simple")
        if item_type in ("section_header", "composite_sub"):
            continue

        # Skip items whose parent is a known unit parent (composite sub-items)
        parent_num = item.get("parentItemNumber")
        if parent_num and parent_num in unit_parent_numbers:
            continue

        item_id = item.get("id") or f"{file_id}:{item.get('sheetName', '')}:{item['row']}"
        doc_id = f"item:{file_id}:{item_id}"
        full_desc = item.get("fullDescription") or item.get("description", "")
        if not full_desc.strip():
            continue

        ids.append(doc_id)
        documents.append(full_desc)
        metadatas.append({
            "file_id": file_id,
            "entity_type": "item",
            "item_id": item_id,
            "file_date": file_date or "",
            "unit": item.get("unit") or "",
            "item_number": item.get("itemNumber") or "",
            "unit_price": float(item.get("unitPrice") or 0),
            "quantity": float(item.get("quantity") or 0),
        })

    if ids:
        _get_collection().upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def search(
    query_text: str,
    top_k: int = 20,
    file_id_exclude: str | None = None,
) -> list[dict[str, Any]]:
    """Search for similar BoQ items. Returns list of {id, similarity, metadata}."""
    if not query_text.strip():
        return []
    where = {"file_id": {"$ne": file_id_exclude}} if file_id_exclude else None
    try:
        results = _get_collection().query(
            query_texts=[query_text],
            n_results=top_k,
            where=where,
        )
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    if not results["ids"] or not results["ids"][0]:
        return []
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i] if results["distances"] else 0.0
        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
        out.append({
            "id": doc_id,
            "similarity": round(1.0 - distance, 4),
            "metadata": metadata,
        })
    return out


def delete_file(file_id: str) -> None:
    """Remove all items for a file from the index."""
    _get_collection().delete(where={"file_id": file_id})


def delete_all() -> None:
    """Remove all items from the index (for rebuild)."""
    global _collection
    _client.delete_collection(_COLLECTION_NAME)
    _collection = None  # Force re-creation on next access
