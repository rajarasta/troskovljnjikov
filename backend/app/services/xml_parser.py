"""XML Parser — deterministic parsing of LogiKal/Pantheon XML project exports.

No LLM involvement. Pure Python XML parsing using ElementTree.
Functions are exposed as tools for the xml_resolver agent.

Supports two XML formats:
1. **LogiKal** (window/door manufacturing) — root tag ``logiObj``:
   - <Position> elements = window/door units with Qty, Calculation price
   - <OptimizedProfile> = aluminium profiles with lengths, prices per meter
   - <Accessory> = fittings, screws, seals with qty and unit prices
   - <ArticleSummary> = aggregated totals
   - Data is in **attributes**, not child elements

2. **Generic Pantheon/gala** (construction BOQ) — root tags like ``Projekt``:
   - <Artikel/Stavka> elements with child <Naziv>, <Kolicina>, <Cijena>
   - Data is in **child elements**
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------


def _is_logikal(root: ET.Element) -> bool:
    """Detect if this is a LogiKal XML export."""
    tag = _tag_lower(root)
    return (
        tag == "logiobj"
        or root.attrib.get("ObjectName", "").startswith("Projekt")
        or root.attrib.get("LogiKalVersion") is not None
    )


# ---------------------------------------------------------------------------
# Tag helpers (for generic Pantheon format)
# ---------------------------------------------------------------------------

_NAME_TAGS = {"naziv", "name", "opis", "description", "tekst", "text"}
_QTY_TAGS = {"kolicina", "qty", "quantity", "kol"}
_UNIT_TAGS = {"jedinicamjere", "jm", "unit", "jed", "mjernajedinica"}
_PRICE_TAGS = {"cijena", "price", "jedcijena", "unitprice"}
_CODE_TAGS = {"sifra", "code", "id", "artikelid", "artiklid", "rbr"}
_SECTION_TAGS = {
    "skupina", "poglavlje", "chapter", "section", "group",
    "kategorija", "category", "razina", "level",
}
_ITEM_TAGS = {
    "artikel", "artikl", "item", "stavka", "pozicija",
    "red", "row", "lineitem",
}
_LIST_TAGS = {
    "artikli", "items", "stavke", "pozicije",
    "troskovnik", "boq", "specifikacija",
}


def _tag_lower(element: ET.Element) -> str:
    """Get the tag name without namespace, lowercased."""
    tag = element.tag
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    return tag.lower()


def _find_child_text(parent: ET.Element, tag_set: set[str]) -> str:
    """Find the first child whose tag matches the set and return its text."""
    for child in parent:
        if _tag_lower(child) in tag_set:
            return (child.text or "").strip()
    return ""


def _find_child_float(parent: ET.Element, tag_set: set[str]) -> float | None:
    """Find the first child whose tag matches and return as float."""
    text = _find_child_text(parent, tag_set)
    if not text:
        return None
    text = text.replace(",", ".")
    text = re.sub(r"\.(?=\d{3})", "", text)
    try:
        return float(text)
    except ValueError:
        return None


def _parse_price_attr(value: str) -> float:
    """Parse a LogiKal price attribute like '2.362 EUR' → 2.362."""
    if not value:
        return 0.0
    parts = value.strip().split()
    try:
        return float(parts[0])
    except (ValueError, IndexError):
        return 0.0


# ===================================================================
# Public API
# ===================================================================


def parse_pantheon_xml(file_bytes: bytes) -> dict[str, Any]:
    """Parse a LogiKal or Pantheon/gala XML export into structured project data.

    Returns:
        {
            "project_name": str,
            "format": "logikal" | "generic",
            "sections": [...],
            "raw_items": [...],
            "positions": [...],       (LogiKal only)
            "profiles_summary": [...], (LogiKal only)
            "accessories_summary": [...], (LogiKal only)
            "metadata": {...}
        }
    """
    root = ET.fromstring(file_bytes)

    if _is_logikal(root):
        return _parse_logikal(root)
    return _parse_generic(root)


def extract_material_items(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract material line items from parsed XML.

    Filters to items that have at least a description with 3+ chars.
    """
    items = parsed.get("raw_items", [])
    return [
        item for item in items
        if item.get("description") and len(item["description"].strip()) >= 3
    ]


def xml_list_sections(file_bytes: bytes) -> list[str]:
    """List all section/chapter names in the XML. Agent tool."""
    root = ET.fromstring(file_bytes)
    if _is_logikal(root):
        # For LogiKal: return position names and lot groups
        sections = []
        lots: set[str] = set()
        for pos in root.findall("Position"):
            name = pos.attrib.get("Name", "")
            lot = pos.attrib.get("Lot", "")
            if name:
                sections.append(f"Position {name}")
            if lot and lot not in lots:
                lots.add(lot)
                sections.append(f"Lot: {lot}")
        # Add summary sections
        if root.find("ArticleSummary") is not None:
            sections.append("ArticleSummary (profiles + accessories + glass)")
        if root.find("FreeCosts") is not None:
            sections.append("FreeCosts")
        return sections

    sections = _extract_sections_generic(root)
    return [s["name"] for s in sections if s["name"]]


def xml_extract_nodes(file_bytes: bytes, xpath: str) -> list[dict[str, Any]]:
    """Extract nodes matching an XPath expression or tag name. Agent tool."""
    root = ET.fromstring(file_bytes)
    try:
        matches = root.findall(xpath)
    except SyntaxError:
        matches = [el for el in root.iter() if _tag_lower(el) == xpath.lower()]

    results: list[dict[str, Any]] = []
    for el in matches[:100]:
        results.append({
            "tag": _tag_lower(el),
            "text": (el.text or "").strip()[:500],
            "attributes": dict(el.attrib),
            "children_count": len(list(el)),
            "child_tags": [_tag_lower(c) for c in el][:20],
        })
    return results


def xml_get_bom_items(file_bytes: bytes) -> list[dict[str, Any]]:
    """Extract Bill of Materials items from the XML. Agent tool."""
    root = ET.fromstring(file_bytes)
    if _is_logikal(root):
        return _extract_logikal_bom(root)
    return _extract_items_recursive_generic(root)


# ===================================================================
# LogiKal format parser
# ===================================================================


def _parse_logikal(root: ET.Element) -> dict[str, Any]:
    """Parse a LogiKal window/door project XML."""
    project_name = root.attrib.get("Order", "")
    lot = ""

    # Extract positions (window/door units)
    positions: list[dict[str, Any]] = []
    for pos in root.findall("Position"):
        lot = pos.attrib.get("Lot", lot)
        positions.append(_parse_logikal_position(pos))

    # Extract article summary (aggregated profiles + accessories)
    profiles_summary = _extract_logikal_profiles_summary(root)
    accessories_summary = _extract_logikal_accessories_summary(root)

    # Build raw_items from all profiles + accessories (deduplicated)
    raw_items = _extract_logikal_bom(root)

    # Calculation summary
    all_calc = root.find(".//AllCalculation")
    total_price = _parse_price_attr(all_calc.attrib.get("Price", "0")) if all_calc is not None else 0

    return {
        "project_name": project_name or "LogiKal Project",
        "format": "logikal",
        "sections": [
            {"name": f"Lot: {lot}", "path": "Position", "item_count": len(positions)},
        ],
        "raw_items": raw_items,
        "positions": positions,
        "profiles_summary": profiles_summary,
        "accessories_summary": accessories_summary,
        "metadata": {
            "root_tag": "logiobj",
            "format": "logikal",
            "logikal_version": root.attrib.get("LogiKalVersion", ""),
            "order": root.attrib.get("Order", ""),
            "total_price": total_price,
            "total_price_currency": "EUR",
            "position_count": len(positions),
            "total_elements": sum(1 for _ in root.iter()),
            "section_count": 1,
            "item_count": len(raw_items),
            "profile_types": len(profiles_summary),
            "accessory_types": len(accessories_summary),
        },
    }


def _parse_logikal_position(pos: ET.Element) -> dict[str, Any]:
    """Parse a single LogiKal <Position> element."""
    calc = pos.find("Calculation")
    price = _parse_price_attr(calc.attrib.get("Price", "0")) if calc is not None else 0
    currency = calc.attrib.get("Currency", "EUR") if calc is not None else "EUR"

    # Collect profiles for this position
    profiles: list[dict[str, Any]] = []
    profiles_el = pos.find("Profiles")
    if profiles_el is not None:
        for p in profiles_el:
            profiles.append({
                "number": p.attrib.get("Number", ""),
                "name": p.attrib.get("Name", ""),
                "qty": int(p.attrib.get("Qty", "0") or "0"),
                "length": float(p.attrib.get("Length", "0") or "0"),
                "used_length": float(p.attrib.get("UsedLength", "0") or "0"),
                "price_per_unit": _parse_price_attr(p.attrib.get("Price", "0")),
                "weight_per_m": float(p.attrib.get("Weight", "0") or "0"),
            })

    # Collect accessories for this position
    accessories: list[dict[str, Any]] = []
    acc_el = pos.find("Accessories")
    if acc_el is not None:
        for a in acc_el:
            accessories.append({
                "number": a.attrib.get("Number", ""),
                "name": a.attrib.get("Name", ""),
                "qty": int(a.attrib.get("Qty", "0") or "0"),
                "price_per_unit": _parse_price_attr(a.attrib.get("Price", "0")),
            })

    # Glass
    glass: list[dict[str, Any]] = []
    glass_el = pos.find("Glass")
    if glass_el is not None:
        for g in glass_el:
            glass.append({
                "name": g.attrib.get("Name", g.attrib.get("GlassType", "")),
                "width": float(g.attrib.get("Width", "0") or "0"),
                "height": float(g.attrib.get("Height", "0") or "0"),
                "price": _parse_price_attr(g.attrib.get("Price", "0")),
            })

    return {
        "name": pos.attrib.get("Name", ""),
        "id": pos.attrib.get("Id", ""),
        "qty": int(pos.attrib.get("Qty", "1") or "1"),
        "lot": pos.attrib.get("Lot", ""),
        "price": price,
        "currency": currency,
        "width": float(pos.attrib.get("Width", "0") or "0"),
        "height": float(pos.attrib.get("Height", "0") or "0"),
        "profiles": profiles,
        "accessories": accessories,
        "glass": glass,
        "serie": pos.find("Serie").attrib.get("Name", "") if pos.find("Serie") is not None else "",
    }


def _extract_logikal_profiles_summary(root: ET.Element) -> list[dict[str, Any]]:
    """Extract profile summary from ArticleSummary/AllProfiles."""
    all_profiles = root.find(".//AllProfiles")
    if all_profiles is None:
        return []

    profiles: list[dict[str, Any]] = []
    for p in all_profiles:
        if _tag_lower(p) != "optimizedprofile":
            continue
        profiles.append({
            "number": p.attrib.get("Number", ""),
            "name": p.attrib.get("Name", ""),
            "qty": int(p.attrib.get("Qty", "0") or "0"),
            "length": float(p.attrib.get("Length", "0") or "0"),
            "used_length": float(p.attrib.get("UsedLength", "0") or "0"),
            "price_per_unit": _parse_price_attr(p.attrib.get("Price", "0")),
            "weight_per_m": float(p.attrib.get("Weight", "0") or "0"),
            "profile_cost_ordered": float(p.attrib.get("ProfileCostOrdered", "0") or "0"),
            "profile_cost_needed": float(p.attrib.get("ProfileCostNeeded", "0") or "0"),
            "material": p.attrib.get("MaterialDescription", ""),
            "color": "",
        })
        # Get color
        color_el = p.find("Color")
        if color_el is not None:
            profiles[-1]["color"] = color_el.attrib.get("Description", "")

    return profiles


def _extract_logikal_accessories_summary(root: ET.Element) -> list[dict[str, Any]]:
    """Extract accessory summary from ArticleSummary/AllAccessories."""
    all_acc = root.find(".//AllAccessories")
    if all_acc is None:
        return []

    accessories: list[dict[str, Any]] = []
    for a in all_acc:
        accessories.append({
            "number": a.attrib.get("Number", ""),
            "name": a.attrib.get("Name", ""),
            "qty": int(a.attrib.get("Qty", "0") or "0"),
            "price_per_unit": _parse_price_attr(a.attrib.get("Price", "0")),
        })
    return accessories


def _extract_logikal_bom(root: ET.Element) -> list[dict[str, Any]]:
    """Extract a flat BOM from LogiKal XML (profiles + accessories + positions).

    Returns one entry per unique article/profile, with aggregated quantities.
    Also includes position-level entries (the window/door units themselves).
    """
    items: list[dict[str, Any]] = []
    seen: dict[str, int] = {}  # number -> index in items

    # 1. Profiles from ArticleSummary
    for p in _extract_logikal_profiles_summary(root):
        number = p["number"]
        price = p["price_per_unit"]
        cost = p["profile_cost_needed"]

        if number in seen:
            # Aggregate quantities
            idx = seen[number]
            items[idx]["qty"] += p["qty"]
            items[idx]["used_length"] = items[idx].get("used_length", 0) + p["used_length"]
        else:
            seen[number] = len(items)
            items.append({
                "code": number,
                "description": p["name"],
                "qty": p["qty"],
                "unit": "m" if p["used_length"] > 0 else "kom",
                "used_length": p["used_length"],
                "price": price,
                "total_cost": cost,
                "weight_per_m": p["weight_per_m"],
                "section": "Profiles",
                "item_type": "profile",
                "color": p.get("color", ""),
                "xml_path": "ArticleSummary/AllProfiles/OptimizedProfile",
                "attributes": {},
            })

    # 2. Accessories from ArticleSummary
    for a in _extract_logikal_accessories_summary(root):
        number = a["number"]
        if number in seen:
            idx = seen[number]
            items[idx]["qty"] += a["qty"]
        else:
            seen[number] = len(items)
            items.append({
                "code": number,
                "description": a["name"],
                "qty": a["qty"],
                "unit": "kom",
                "price": a["price_per_unit"],
                "total_cost": a["price_per_unit"] * a["qty"],
                "section": "Accessories",
                "item_type": "accessory",
                "xml_path": "ArticleSummary/AllAccessories/Accessory",
                "attributes": {},
            })

    # 3. Positions (the window/door units themselves — top-level)
    for pos in root.findall("Position"):
        calc = pos.find("Calculation")
        price = _parse_price_attr(calc.attrib.get("Price", "0")) if calc is not None else 0
        name = pos.attrib.get("Name", "")
        qty = int(pos.attrib.get("Qty", "1") or "1")
        serie = pos.find("Serie")
        serie_name = serie.attrib.get("Longname", serie.attrib.get("Name", "")) if serie is not None else ""

        desc = f"Position {name}"
        if serie_name:
            desc += f" ({serie_name})"

        items.append({
            "code": f"POS-{pos.attrib.get('Id', name)}",
            "description": desc,
            "qty": qty,
            "unit": "kom",
            "price": price,
            "total_cost": price * qty,
            "section": "Positions",
            "item_type": "position",
            "xml_path": "Position",
            "attributes": {
                "lot": pos.attrib.get("Lot", ""),
                "width": pos.attrib.get("Width", ""),
                "height": pos.attrib.get("Height", ""),
            },
        })

    return items


# ===================================================================
# Generic Pantheon/gala format parser (fallback)
# ===================================================================


def _parse_generic(root: ET.Element) -> dict[str, Any]:
    """Parse a generic Pantheon/gala XML where data is in child elements."""
    root_tag = _tag_lower(root)

    project_name = _find_child_text(root, {"naziv", "name", "projekt", "project"})
    if not project_name:
        project_name = _find_child_text(root, {"naslov", "title"})

    sections = _extract_sections_generic(root)
    raw_items = _extract_items_recursive_generic(root)

    return {
        "project_name": project_name or root_tag,
        "format": "generic",
        "sections": sections,
        "raw_items": raw_items,
        "metadata": {
            "root_tag": root_tag,
            "format": "generic",
            "total_elements": sum(1 for _ in root.iter()),
            "section_count": len(sections),
            "item_count": len(raw_items),
        },
    }


def _extract_sections_generic(
    root: ET.Element, path: str = "",
) -> list[dict[str, Any]]:
    """Recursively find section/chapter elements in generic format."""
    sections: list[dict[str, Any]] = []

    for child in root:
        tag = _tag_lower(child)
        current_path = f"{path}/{child.tag}" if path else child.tag

        if tag in _SECTION_TAGS or tag in _LIST_TAGS:
            name = _find_child_text(child, _NAME_TAGS)
            if not name:
                name = child.attrib.get("naziv", child.attrib.get("name", tag))

            item_count = sum(
                1 for el in child.iter() if _tag_lower(el) in _ITEM_TAGS
            )

            sections.append({
                "name": name,
                "path": current_path,
                "item_count": item_count,
                "tag": tag,
            })
            sections.extend(_extract_sections_generic(child, current_path))
        else:
            sections.extend(_extract_sections_generic(child, current_path))

    return sections


def _extract_items_recursive_generic(
    root: ET.Element, section: str = "",
) -> list[dict[str, Any]]:
    """Recursively extract item elements from generic XML."""
    items: list[dict[str, Any]] = []

    for child in root:
        tag = _tag_lower(child)

        current_section = section
        if tag in _SECTION_TAGS:
            sec_name = _find_child_text(child, _NAME_TAGS)
            if sec_name:
                current_section = sec_name

        if tag in _ITEM_TAGS:
            item = _parse_generic_item(child, current_section)
            if item:
                items.append(item)
        elif tag in _LIST_TAGS:
            items.extend(_extract_items_recursive_generic(child, current_section))
        else:
            items.extend(_extract_items_recursive_generic(child, current_section))

    return items


def _parse_generic_item(
    element: ET.Element, section: str = "",
) -> dict[str, Any] | None:
    """Parse a single item element from generic format."""
    description = _find_child_text(element, _NAME_TAGS)
    if not description:
        description = (element.text or "").strip()

    code = _find_child_text(element, _CODE_TAGS)
    if not code:
        code = element.attrib.get("id", element.attrib.get("sifra", ""))

    qty = _find_child_float(element, _QTY_TAGS)
    unit = _find_child_text(element, _UNIT_TAGS)
    price = _find_child_float(element, _PRICE_TAGS)

    if not description:
        return None

    return {
        "code": code,
        "description": description,
        "qty": qty or 0.0,
        "unit": unit or "kom",
        "price": price,
        "section": section,
        "xml_path": element.tag,
        "attributes": dict(element.attrib),
    }
