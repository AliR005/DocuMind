from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.models import Chunk, Document  # noqa: F401 - register models in Base.metadata

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.include_router(health_router, prefix=settings.api_v1_prefix)
