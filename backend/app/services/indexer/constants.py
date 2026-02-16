"""Column patterns, known units, and other indexer constants."""

from __future__ import annotations

import re

COLUMN_PATTERNS: dict[str, list[str]] = {
    "itemNumber": [
        "r.br", "rbr", "r.b.", "rb", "redni broj", "redni",
        "item", "no", "no.", "number",
        "pozicija", "poz", "poz.",
        "šifra", "sifra", "oznaka",
        "kod", "code",
        "br.st", "br.st.", "broj stavke",
    ],
    "description": [
        "opis", "opis radova", "opis stavke",
        "description", "desc", "desc.",
        "naziv", "naziv stavke", "naziv radova",
        "stavka", "radovi", "rad",
        "kratki opis", "tekst stavke",
        "work", "item", "text", "tekst",
    ],
    "descriptionLong": [
        "dugi opis", "long description", "detailed description",
    ],
    "unit": [
        "jed", "jed.", "j.m.", "jm", "j.m", "jedinica", "jedinica mjere",
        "mjera", "mj", "mj.", "jed.mj", "jed.mj.",
        "unit", "uom", "u.o.m",
    ],
    "quantity": [
        "kol", "kol.", "količina", "kolicina", "količ.",
        "quantity", "qty", "qty.",
        "amount", "iznos kol", "broj",
    ],
    "unitPrice": [
        "jedinična cijena", "jedinicna cijena",
        "jed. cijena", "jed.cijena", "jed.cij", "jed.cij.",
        "cij", "cijena", "cij.",
        "j.c.", "jc", "j.c",
        "price", "unit price", "rate",
    ],
    "total": [
        "ukupna cijena", "ukupno", "ukup", "uk.", "ukup.",
        "total", "sum", "suma",
        "iznos", "vrijednost", "svega",
        "uc", "u.c", "u.c.",
    ],
}

MAX_HEADER_SEARCH_ROWS: int = 25

NON_BOQ_SHEET_PATTERNS: list[str] = [
    "naslovnica", "opći uvjeti", "opci uvjeti", "općiuvjeti",
    "export info", "cover", "general conditions",
]

KAUFLAND_CODE_RE = re.compile(r"^\d{3}(\.\d{3}(\.\d{5})?)?$")

KNOWN_UNITS: set[str] = {
    "m", "m2", "m²", "m3", "m³", "kom", "komad", "komplet", "kpl", "kg",
    "l", "lit", "set", "pauš", "paušal", "pau", "h", "sat", "dan",
    "cm", "mm", "km", "t", "ton", "%", "m1", "ml",
}

# Date patterns found in Croatian BoQ filenames
DATE_PATTERNS: list[tuple[str, str | None]] = [
    (r"(\d{4})-(\d{1,2})-(\d{1,2})", "%Y-%m-%d"),        # 2025-06-09
    (r"(\d{1,2})\.(\d{1,2})\.(\d{4})", "%d.%m.%Y"),       # 1.12.2025
    (r"(\d{1,2})\.(\d{1,2})\.(\d{2})\b", "%d.%m.%y"),     # 7.4.24
    (r"(\d{2})(\d{2})(\d{4})", None),                      # DDMMYYYY
]
