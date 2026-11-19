from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models import Chunk, Document


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    document: Document
    score: float


class SearchService:
    """Rank persisted document chunks by TF-IDF cosine similarity."""

    def __init__(
        self, session: Session, min_relevance_threshold: float | None = None
    ) -> None:
        self.session = session
        self.min_relevance_threshold = (
            get_settings().min_relevance_threshold
            if min_relevance_threshold is None
            else min_relevance_threshold
        )
        if not 0.0 <= self.min_relevance_threshold <= 1.0:
            raise ValueError("min_relevance_threshold must be between 0 and 1")

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Return up to ``limit`` matches, best first; return [] below threshold."""
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        if not query or not query.strip():
            return []

        chunks = list(
            self.session.scalars(
                select(Chunk)
                .options(joinedload(Chunk.document))
                .order_by(Chunk.id)
            ).all()
        )
        if not chunks:
            return []

        corpus = [chunk.content for chunk in chunks]
        try:
            vectorizer = TfidfVectorizer()
            corpus_vectors = vectorizer.fit_transform(corpus)
        except ValueError:
            # sklearn raises for empty corpora or vocabularies (for example, punctuation only).
            return []

        query_vector = vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, corpus_vectors).ravel()
        ranked_indices = sorted(
            range(len(chunks)), key=lambda index: (-similarities[index], chunks[index].id)
        )

        results = []
        for index in ranked_indices:
            score = float(similarities[index])
            if score < self.min_relevance_threshold:
                break
            chunk = chunks[index]
            results.append(SearchResult(chunk=chunk, document=chunk.document, score=score))
            if len(results) == limit:
                break
        return results
