import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


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
    monkeypatch.setattr("app.main.engine", test_engine)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def upload_text(client, filename: str, text: str):
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": (filename, text.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 201
    return response.json()


def test_ask_returns_best_chunk_filename_and_relevance_score(client):
    upload_text(client, "garden.txt", "Local garden notes mention flowers and trees.")
    target = upload_text(
        client,
        "astronomy-notes.txt",
        "A quasar telescope observes distant galaxies and stars.",
    )

    response = client.post(
        "/api/v1/questions/ask", json={"question": "quasar telescope"}
    )

    assert response.status_code == 200
    result = response.json()
    assert result["answer"] == target["chunks"][0]["content"]
    assert result["source_filename"] == "astronomy-notes.txt"
    assert result["relevance_score"] > 0


def test_ask_rejects_blank_question(client):
    response = client.post("/api/v1/questions/ask", json={"question": "   "})

    assert response.status_code == 422


def test_ask_reports_when_there_are_no_documents(client):
    response = client.post(
        "/api/v1/questions/ask", json={"question": "quasar telescope"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No documents are available"


def test_ask_reports_when_no_document_is_relevant(client):
    upload_text(client, "garden.txt", "Local garden notes mention flowers and trees.")

    response = client.post(
        "/api/v1/questions/ask", json={"question": "quasar telescope"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No relevant document found"
