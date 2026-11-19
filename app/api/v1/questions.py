from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Document
from app.schemas.question import QuestionRequest, QuestionResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/ask", response_model=QuestionResponse)
def ask_question(
    request: QuestionRequest, session: Session = Depends(get_db)
) -> QuestionResponse:
    has_documents = session.scalar(select(Document.id).limit(1)) is not None
    if not has_documents:
        raise HTTPException(status_code=404, detail="No documents are available")

    results = SearchService(session).search(request.question, limit=1)
    if not results:
        raise HTTPException(status_code=404, detail="No relevant document found")

    best_match = results[0]
    return QuestionResponse(
        answer=best_match.chunk.content,
        source_filename=best_match.document.filename,
        relevance_score=best_match.score,
    )
