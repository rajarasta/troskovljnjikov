"""RAG service for BoQ item search using ChromaDB + sentence-transformers."""
from __future__ import annotations

from typing import Any

import chromadb
from chromadb.utils import embedding_functions

_COLLECTION_NAME = "boq_items"
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_client = chromadb.PersistentClient(path="./data/chromadb")
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=_MODEL_NAME)
_collection = _client.get_or_create_collection(
    name=_COLLECTION_NAME,
    embedding_function=_ef,
    metadata={"hnsw:space": "cosine"},
)


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
    """Embed and store BoQ items in ChromaDB. Returns count indexed."""
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
    _collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def search(
    query_text: str,
    top_k: int = 20,
    file_id_exclude: str | None = None,
) -> list[dict[str, Any]]:
    """Search for similar BoQ items. Returns list of {id, distance, metadata}."""
    if not query_text.strip():
        return []
    where = {"file_id": {"$ne": file_id_exclude}} if file_id_exclude else None
    try:
        results = _collection.query(
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
    _collection.delete(where={"file_id": file_id})
