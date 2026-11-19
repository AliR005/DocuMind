import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Document
from app.repositories.document_repository import DocumentRepository
from app.services.chunking import split_text

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentOut(BaseModel):
    id: int
    filename: str
    content_type: str | None
    content_sha256: str
    size_bytes: int
    created_at: object
    chunks: list["ChunkOut"]

    model_config = ConfigDict(from_attributes=True)


class ChunkOut(BaseModel):
    id: int
    content: str
    chunk_index: int

    model_config = ConfigDict(from_attributes=True)


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...), session: Session = Depends(get_db)
) -> Document:
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=415, detail="Only TXT files are supported")

    settings = get_settings()
    content = await file.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="File exceeds the maximum allowed size")
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="File is empty")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must use UTF-8 encoding") from exc

    content_sha256 = hashlib.sha256(content).hexdigest()
    repository = DocumentRepository(session)
    if repository.get_by_sha256(content_sha256):
        raise HTTPException(status_code=409, detail="This document has already been uploaded")

    chunks = split_text(text, settings.chunk_size, settings.chunk_overlap)
    try:
        return repository.create(
            filename=file.filename,
            content_type=file.content_type,
            content_sha256=content_sha256,
            size_bytes=len(content),
            chunks=chunks,
        )
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="This document has already been uploaded"
        ) from exc


@router.get("", response_model=list[DocumentOut])
def list_documents(session: Session = Depends(get_db)) -> list[Document]:
    return DocumentRepository(session).list()
