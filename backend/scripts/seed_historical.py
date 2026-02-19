"""Seed historical BoQ data from a folder of Excel files.

Scans a folder for .xlsx/.xls files, parses them with the existing indexer,
classifies items, resolves dates, stores in SQLite, and indexes in ChromaDB.

Usage:
    # From backend/ directory:
    uv run python -m scripts.seed_historical [--rebuild] [FOLDER_PATH]

    # Default folder: vanjski-podaci/primjeri-excel-ponuda/
    # --rebuild: wipe DB and ChromaDB, then re-index everything
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from hashlib import md5
from pathlib import Path

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, create_tables, engine
from app.models.boq import BoQFile, BoQItem, BoQUnit
from app.services.boq_indexer import index_file, resolve_file_date
from app.services.rag import delete_all as rag_delete_all, index_for_search


def _find_repo_root() -> str:
    """Find the main git repo root (works inside worktrees too)."""
    import subprocess
    try:
        # git worktree: commondir points to the main repo's .git
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=os.path.dirname(__file__),
            text=True,
        ).strip()
        return str(Path(common).resolve().parent)
    except Exception:
        # Fallback: 4 levels up from scripts/ -> backend/ -> boq-matcher/ -> .worktrees/ -> repo
        return str(Path(__file__).resolve().parent.parent.parent.parent.parent)


DEFAULT_FOLDER = os.path.join(
    _find_repo_root(), "vanjski-podaci", "primjeri-excel-ponuda"
)


def _deterministic_id(file_path: str) -> str:
    """Generate a deterministic UUID from file path (safe to re-run)."""
    return str(uuid.UUID(md5(file_path.encode()).hexdigest()))


def seed(folder_path: str, rebuild: bool = False) -> None:
    create_tables()
    db = SessionLocal()

    if rebuild:
        print("Rebuilding: dropping all tables and recreating...")
        db.close()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        rag_delete_all()
        print("Done. Starting fresh.")

    folder = Path(folder_path).resolve()
    if not folder.is_dir():
        print(f"Error: {folder} is not a directory")
        sys.exit(1)

    supported = {".xlsx", ".xls"}
    files = sorted(
        f for f in folder.iterdir()
        if f.suffix.lower() in supported and not f.name.startswith("~")
    )

    print(f"Found {len(files)} Excel files in {folder}")

    success_count = 0
    error_count = 0
    total_items = 0
    total_units = 0

    for i, file_path in enumerate(files, 1):
        file_name = file_path.name
        file_id = _deterministic_id(str(file_path))

        # Skip if already indexed (unless rebuilding)
        if not rebuild:
            existing = db.query(BoQFile).filter(BoQFile.id == file_id).first()
            if existing:
                print(f"  [{i}/{len(files)}] SKIP (already indexed): {file_name}")
                continue

        # Resolve date
        file_date, date_source = resolve_file_date(file_name, str(file_path))

        print(f"  [{i}/{len(files)}] Indexing: {file_name}", end="")
        if file_date:
            print(f" (date: {file_date.strftime('%Y-%m-%d')}, source: {date_source})", end="")
        print("...", end=" ", flush=True)

        try:
            file_bytes = file_path.read_bytes()
            result = index_file(
                file_path=file_id,
                file_bytes=file_bytes,
                file_date=file_date,
            )

            if not result["success"]:
                print(f"FAILED: {result.get('error', 'Unknown error')}")
                error_count += 1
                continue

            items = result["items"]
            units = result.get("units", [])

            # Persist file record
            db_file = BoQFile(
                id=file_id,
                file_name=file_name,
                file_path=str(file_path),
                stored_path=str(file_path),
                file_type=file_path.suffix.lstrip(".").lower(),
                file_date=file_date,
                date_source=date_source,
                sheet_count=result["file"].get("sheetCount", 0),
                item_count=result["file"].get("itemCount", 0),
                project_name=result["file"].get("projectName"),
                missing_data=result["file"].get("missingData"),
            )
            db.add(db_file)

            # Persist items
            for item_data in items:
                item_id = f"{file_id}:{item_data.get('sheetName', '')}:{item_data['row']}"
                db_item = BoQItem(
                    id=item_id,
                    file_id=file_id,
                    sheet_name=item_data.get("sheetName"),
                    row=item_data["row"],
                    item_number=item_data.get("itemNumber"),
                    description=item_data["description"],
                    full_description=item_data.get("fullDescription"),
                    parent_item_number=item_data.get("parentItemNumber"),
                    unit=item_data.get("unit"),
                    quantity=item_data.get("quantity", 0),
                    unit_price=item_data.get("unitPrice", 0),
                    total=item_data.get("total", 0),
                    project_name=item_data.get("projectName"),
                    date=item_data.get("date"),
                    item_type=item_data.get("itemType"),
                )
                db.add(db_item)

            # Persist units
            for unit_data in units:
                db_unit = BoQUnit(
                    id=unit_data["id"],
                    file_id=file_id,
                    sheet_name=unit_data["sheetName"],
                    parent_item_number=unit_data["parentItemNumber"],
                    parent_title=unit_data.get("parentTitle"),
                    parent_description=unit_data.get("parentDescription"),
                    start_row=unit_data["startRow"],
                    end_row=unit_data["endRow"],
                    item_ids=unit_data["itemIds"],
                    subtotal=unit_data.get("subtotal"),
                    item_count=unit_data.get("itemCount", 0),
                )
                db.add(db_unit)

            db.commit()

            # RAG indexing (dual-level)
            date_str = file_date.strftime("%Y-%m-%d") if file_date else None
            indexed = index_for_search(
                file_id=file_id,
                items=items,
                units=units,
                file_date=date_str,
            )

            print(f"OK ({len(items)} items, {len(units)} units, {indexed} indexed)")
            success_count += 1
            total_items += len(items)
            total_units += len(units)

        except Exception as exc:
            print(f"ERROR: {exc}")
            error_count += 1
            db.rollback()

    db.close()

    print(f"\n{'='*60}")
    print(f"Seed complete: {success_count} files indexed, {error_count} errors")
    print(f"Total: {total_items} items, {total_units} units")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed historical BoQ data")
    parser.add_argument("folder", nargs="?", default=DEFAULT_FOLDER, help="Folder with Excel files")
    parser.add_argument("--rebuild", action="store_true", help="Wipe and rebuild from scratch")
    args = parser.parse_args()
    seed(args.folder, args.rebuild)
