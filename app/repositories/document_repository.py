from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Chunk, Document


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_sha256(self, content_sha256: str) -> Document | None:
        return self.session.scalar(
            select(Document).where(Document.content_sha256 == content_sha256)
        )

    def create(
        self,
        *,
        filename: str,
        content_type: str | None,
        content_sha256: str,
        size_bytes: int,
        chunks: list[str],
    ) -> Document:
        document = Document(
            filename=filename,
            content_type=content_type,
            content_sha256=content_sha256,
            size_bytes=size_bytes,
            chunks=[Chunk(content=content, chunk_index=index) for index, content in enumerate(chunks)],
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def list(self) -> list[Document]:
        return list(
            self.session.scalars(
                select(Document).options(selectinload(Document.chunks)).order_by(Document.id)
            ).all()
        )
