"""Tests for preset CRUD and canonical export."""
from __future__ import annotations


def test_list_default_presets(client):
    """Default presets are seeded on startup."""
    res = client.get("/api/presets")
    assert res.status_code == 200
    presets = res.json()
    assert len(presets) >= 6
    assert all(p["is_default"] for p in presets[:6])


def test_create_custom_preset(client):
    """User can create a custom preset."""
    res = client.post("/api/presets", json={
        "name": "Test preset",
        "description": "For testing",
        "groups": ["core", "annotation"],
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test preset"
    assert data["is_default"] is False
    assert "annotation" in data["groups"]


def test_delete_default_preset_blocked(client):
    """Cannot delete a default preset."""
    res = client.get("/api/presets")
    default_id = res.json()[0]["id"]
    res = client.delete(f"/api/presets/{default_id}")
    assert res.status_code == 403


def test_delete_custom_preset(client):
    """Can delete a user-created preset."""
    create = client.post("/api/presets", json={
        "name": "Temp",
        "groups": ["core"],
    })
    pid = create.json()["id"]
    res = client.delete(f"/api/presets/{pid}")
    assert res.status_code == 204


def test_canonical_export_with_preset(client, sample_xlsx_path):
    """Export XLSX using a preset produces a valid file."""
    with open(sample_xlsx_path, "rb") as f:
        upload = client.post("/api/upload", files={"file": ("test.xlsx", f)})
    file_id = upload.json()["file_id"]

    res = client.get(f"/api/export/{file_id}/xlsx?preset_id=simple")
    assert res.status_code == 200
    assert "spreadsheetml" in res.headers["content-type"]

    res = client.get(f"/api/export/{file_id}/xlsx?preset_id=puni_pregled")
    assert res.status_code == 200


def test_export_unknown_preset_404(client, sample_xlsx_path):
    """Export with nonexistent preset returns 404."""
    with open(sample_xlsx_path, "rb") as f:
        upload = client.post("/api/upload", files={"file": ("test.xlsx", f)})
    file_id = upload.json()["file_id"]

    res = client.get(f"/api/export/{file_id}/xlsx?preset_id=nonexistent")
    assert res.status_code == 404
