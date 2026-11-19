from datetime import datetime

import pytest
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(test_engine)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # Prevent application startup from creating the default local database.
    monkeypatch.setattr("app.main.engine", test_engine)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def test_upload_and_list_document_with_overlapping_chunks(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.documents.get_settings",
        lambda: type(
            "Settings", (), {"max_upload_size_bytes": 1000, "chunk_size": 6, "chunk_overlap": 2}
        )(),
    )
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.txt", b"abcdefghij", "text/plain")},
    )

    assert response.status_code == 201
    document = response.json()
    assert document["filename"] == "notes.txt"
    assert [chunk["content"] for chunk in document["chunks"]] == ["abcdef", "efghij"]
    assert [chunk["chunk_index"] for chunk in document["chunks"]] == [0, 1]
    datetime.fromisoformat(document["created_at"])

    listing = client.get("/api/v1/documents")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [document["id"]]

    openapi = client.get("/openapi.json").json()
    created_at_schema = openapi["components"]["schemas"]["DocumentOut"]["properties"]["created_at"]
    assert created_at_schema == {"type": "string", "format": "date-time", "title": "Created At"}


def test_rejects_non_txt_file(client):
    response = client.post("/api/v1/documents/upload", files={"file": ("notes.pdf", b"text")})
    assert response.status_code == 415


def test_rejects_empty_file(client):
    response = client.post("/api/v1/documents/upload", files={"file": ("empty.txt", b"")})
    assert response.status_code == 400


@pytest.mark.parametrize("text", [" \t\r\n", "\u00a0\u2003"])
def test_rejects_files_containing_only_whitespace(client, text):
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("whitespace.txt", text.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 400


def test_rejects_invalid_utf8(client):
    response = client.post("/api/v1/documents/upload", files={"file": ("bad.txt", b"\xff")})
    assert response.status_code == 400


def test_rejects_file_over_size_limit(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.documents.get_settings",
        lambda: type(
            "Settings", (), {"max_upload_size_bytes": 3, "chunk_size": 6, "chunk_overlap": 2}
        )(),
    )
    response = client.post("/api/v1/documents/upload", files={"file": ("large.txt", b"four")})
    assert response.status_code == 413


def test_rejects_duplicate_by_sha256(client):
    payload = {"file": ("first.txt", b"same content", "text/plain")}
    assert client.post("/api/v1/documents/upload", files=payload).status_code == 201
    duplicate = client.post(
        "/api/v1/documents/upload",
        files={"file": ("renamed.txt", b"same content", "text/plain")},
    )
    assert duplicate.status_code == 409
