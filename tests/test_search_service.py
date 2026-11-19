import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.document_repository import DocumentRepository
from app.services.search_service import SearchService


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_document(session, filename: str, text: str):
    return DocumentRepository(session).create(
        filename=filename,
        content_type="text/plain",
        content_sha256=filename.ljust(64, "0")[:64],
        size_bytes=len(text.encode("utf-8")),
        chunks=[text],
    )


def test_search_returns_chunk_with_its_correct_source_document(session):
    add_document(
        session,
        "garden.txt",
        "The common project notes describe an orchard and a local garden.",
    )
    target = add_document(
        session,
        "astronomy.txt",
        "The common project notes describe an orchard and a rare quasar telescope.",
    )

    results = SearchService(session, min_relevance_threshold=0.05).search(
        "quasar telescope"
    )

    assert results
    assert results[0].document.id == target.id
    assert results[0].document.filename == "astronomy.txt"
    assert results[0].chunk.document_id == target.id
    assert results[0].score > 0.05


def test_search_ranks_all_matching_chunks_by_relevance(session):
    weak_match = add_document(session, "general.txt", "Notes about a telescope.")
    strong_match = add_document(
        session,
        "space.txt",
        "A quasar telescope studies a distant quasar in deep space.",
    )

    results = SearchService(session, min_relevance_threshold=0.01).search("quasar telescope")

    assert [result.document.id for result in results] == [strong_match.id, weak_match.id]
    assert results[0].score >= results[1].score


def test_search_returns_no_results_below_threshold(session):
    add_document(session, "garden.txt", "Flowers, soil, trees and watering.")

    results = SearchService(session, min_relevance_threshold=0.1).search("quasar telescope")

    assert results == []


def test_search_handles_blank_or_unusable_query(session):
    add_document(session, "notes.txt", "Ordinary project notes.")
    service = SearchService(session, min_relevance_threshold=0.1)

    assert service.search("   ") == []
    assert service.search("!!!") == []


def test_search_ignores_query_terms_missing_from_corpus(session):
    add_document(session, "garden.txt", "The local garden has flowers and trees.")
    target = add_document(
        session,
        "astronomy.txt",
        "A quasar telescope observes distant stars and galaxies.",
    )
    service = SearchService(session, min_relevance_threshold=0.05)

    results = service.search("quasar telescope zorbax")

    assert results
    assert results[0].document.id == target.id
    assert results[0].document.filename == "astronomy.txt"
    assert service.search("zorbax quuxplugh") == []


def test_search_validates_limit_and_threshold(session):
    with pytest.raises(ValueError):
        SearchService(session, min_relevance_threshold=1.1)
    with pytest.raises(ValueError):
        SearchService(session).search("query", limit=0)
