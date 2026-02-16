"""
Master column registry for canonical BoQ export.

Each column belongs to a group. A preset activates groups.
Individual column overrides can toggle columns on/off beyond the preset.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnDef:
    key: str
    group: str
    label_hr: str        # Croatian header name
    col_type: str        # "string" | "text" | "float" | "image" | "enum" | "date"
    fmt: str             # Excel number format or alignment hint
    width: int           # Column width in characters
    always_on: bool = False


COLUMN_REGISTRY: list[ColumnDef] = [
    # ── core (always on) ──────────────────────────────────────────
    ColumnDef("item_number",  "core", "R.br.",        "string", "left",      10, True),
    ColumnDef("description",  "core", "Opis stavke",  "text",   "left",      50, True),
    ColumnDef("unit",         "core", "Jed.mj.",      "string", "center",     8, True),
    ColumnDef("quantity",     "core", "Količina",     "float",  '#,##0.00',  12, True),
    ColumnDef("unit_price",   "core", "Jed. cijena",  "float",  '#,##0.00',  14, True),
    ColumnDef("total",        "core", "Ukupno",       "float",  '#,##0.00',  14, True),

    # ── mat_rad ───────────────────────────────────────────────────
    ColumnDef("material_price", "mat_rad", "Cijena materijala", "float", '#,##0.00', 14),
    ColumnDef("labor_price",    "mat_rad", "Cijena rada",       "float", '#,##0.00', 14),
    ColumnDef("material_total", "mat_rad", "Ukupno materijal",  "float", '#,##0.00', 14),
    ColumnDef("labor_total",    "mat_rad", "Ukupno rad",        "float", '#,##0.00', 14),

    # ── annotation ────────────────────────────────────────────────
    ColumnDef("notes",        "annotation", "Bilješke",     "text",  "left",  30),
    ColumnDef("drawing",      "annotation", "Crtež",        "image", "left",  15),
    ColumnDef("llm_response", "annotation", "LLM odgovor",  "text",  "left",  30),

    # ── status ────────────────────────────────────────────────────
    ColumnDef("status",     "status", "Status", "enum",  "center",    12),
    ColumnDef("updated_at", "status", "Datum",  "date",  "DD.MM.YYYY", 12),

    # ── meta ──────────────────────────────────────────────────────
    ColumnDef("full_description",   "meta", "Puni opis",        "text",   "left",   50),
    ColumnDef("parent_item_number", "meta", "Nadređena stavka", "string", "left",   12),
    ColumnDef("item_type",          "meta", "Tip stavke",       "enum",   "center", 12),
]

# Lookup by key
_BY_KEY: dict[str, ColumnDef] = {c.key: c for c in COLUMN_REGISTRY}

# Lookup by group
_BY_GROUP: dict[str, list[ColumnDef]] = {}
for c in COLUMN_REGISTRY:
    _BY_GROUP.setdefault(c.group, []).append(c)


def resolve_columns(
    groups: list[str],
    include_columns: list[str] | None = None,
    exclude_columns: list[str] | None = None,
) -> list[ColumnDef]:
    """
    Resolve a list of active groups + per-column overrides into
    the final ordered list of columns for export/display.
    """
    include_columns = set(include_columns or [])
    exclude_columns = set(exclude_columns or [])

    active_keys: set[str] = set()
    for group in groups:
        for col in _BY_GROUP.get(group, []):
            active_keys.add(col.key)

    # Apply overrides
    active_keys |= include_columns
    active_keys -= exclude_columns

    # Always keep always_on columns
    for col in COLUMN_REGISTRY:
        if col.always_on:
            active_keys.add(col.key)

    # Return in registry order
    return [c for c in COLUMN_REGISTRY if c.key in active_keys]


def get_all_groups() -> list[str]:
    """Return all distinct group names in registry order."""
    seen: set[str] = set()
    groups: list[str] = []
    for c in COLUMN_REGISTRY:
        if c.group not in seen:
            seen.add(c.group)
            groups.append(c.group)
    return groups
