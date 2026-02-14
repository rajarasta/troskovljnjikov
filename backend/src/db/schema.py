"""SQLite schema for historic BoQ storage."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    client TEXT DEFAULT '',
    location TEXT DEFAULT '',
    import_date TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    format TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS standard_units (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    expected_sub_items TEXT NOT NULL DEFAULT '[]',
    expected_units TEXT NOT NULL DEFAULT '[]',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS standard_units_fts USING fts5(
    label,
    description,
    expected_sub_items,
    content=standard_units,
    content_rowid=rowid,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS standard_units_ai AFTER INSERT ON standard_units BEGIN
    INSERT INTO standard_units_fts(rowid, label, description, expected_sub_items)
    VALUES (new.rowid, new.label, new.description, new.expected_sub_items);
END;

CREATE TRIGGER IF NOT EXISTS standard_units_ad AFTER DELETE ON standard_units BEGIN
    INSERT INTO standard_units_fts(standard_units_fts, rowid, label, description, expected_sub_items)
    VALUES ('delete', old.rowid, old.label, old.description, old.expected_sub_items);
END;

CREATE TABLE IF NOT EXISTS historic_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    item_number TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    parent_section TEXT DEFAULT '',
    parent_chapter TEXT DEFAULT '',
    taxonomy_id TEXT REFERENCES standard_units(id)
);

CREATE TABLE IF NOT EXISTS historic_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL REFERENCES historic_units(id),
    item_number TEXT NOT NULL,
    description TEXT DEFAULT '',
    unit_of_measure TEXT NOT NULL DEFAULT '',
    quantity REAL NOT NULL DEFAULT 0,
    unit_price REAL,
    total REAL
);

CREATE VIRTUAL TABLE IF NOT EXISTS historic_units_fts USING fts5(
    title,
    description,
    content=historic_units,
    content_rowid=id,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS historic_units_ai AFTER INSERT ON historic_units BEGIN
    INSERT INTO historic_units_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS historic_units_ad AFTER DELETE ON historic_units BEGIN
    INSERT INTO historic_units_fts(historic_units_fts, rowid, title, description)
    VALUES ('delete', old.id, old.title, old.description);
END;

CREATE INDEX IF NOT EXISTS idx_historic_lines_unit
    ON historic_lines(unit_of_measure);

CREATE INDEX IF NOT EXISTS idx_historic_units_project
    ON historic_units(project_id);

CREATE INDEX IF NOT EXISTS idx_historic_units_taxonomy
    ON historic_units(taxonomy_id);
"""
