from fastapi import APIRouter

from app.api.routes import indexing_jobs, raw_documents, repositories

api_router = APIRouter()
api_router.include_router(repositories.router)
api_router.include_router(indexing_jobs.router)
api_router.include_router(raw_documents.router)
