from __future__ import annotations

import os

import pytest


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_file(client, sample_xlsx_path):
    with open(sample_xlsx_path, "rb") as f:
        response = client.post("/api/upload", files={"file": ("test.xlsx", f, "application/octet-stream")})
    assert response.status_code == 200
    data = response.json()
    assert data["item_count"] > 0
    assert data["file_id"]
    assert data["file_name"] == "test.xlsx"


def test_list_files_after_upload(client, sample_xlsx_path):
    with open(sample_xlsx_path, "rb") as f:
        client.post("/api/upload", files={"file": ("test.xlsx", f, "application/octet-stream")})

    response = client.get("/api/files")
    assert response.status_code == 200
    files = response.json()
    assert len(files) == 1
    assert files[0]["item_count"] > 0


def test_get_file_items(client, sample_xlsx_path):
    with open(sample_xlsx_path, "rb") as f:
        upload = client.post("/api/upload", files={"file": ("test.xlsx", f, "application/octet-stream")})
    file_id = upload.json()["file_id"]

    response = client.get(f"/api/files/{file_id}/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    assert items[0]["description"]


def test_match_items(client, sample_xlsx_path, second_sample_path):
    # Upload two files
    with open(sample_xlsx_path, "rb") as f:
        client.post("/api/upload", files={"file": ("file1.xlsx", f, "application/octet-stream")})
    with open(second_sample_path, "rb") as f:
        client.post("/api/upload", files={"file": ("file2.xlsx", f, "application/octet-stream")})

    response = client.post("/api/match", json={
        "description": "gips-kartonski zidovi i obloge",
        "quantity": 120,
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["matches"]) > 0
    assert data["stats"]["avgPrice"] > 0

    # First match should have high similarity
    assert data["matches"][0]["similarity"] > 0.8

    # Should have quantity comparison
    assert data["matches"][0]["quantity_comparison"] is not None


def test_delete_file(client, sample_xlsx_path):
    with open(sample_xlsx_path, "rb") as f:
        upload = client.post("/api/upload", files={"file": ("test.xlsx", f, "application/octet-stream")})
    file_id = upload.json()["file_id"]

    response = client.delete(f"/api/files/{file_id}")
    assert response.status_code == 200

    # Verify deleted
    response = client.get(f"/api/files/{file_id}")
    assert response.status_code == 404
