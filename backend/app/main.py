from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.db.session import dispose_engine
from app.services.qdrant_service import qdrant_service


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await qdrant_service.close()
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="RAG-powered historical bug-fix retrieval platform",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
