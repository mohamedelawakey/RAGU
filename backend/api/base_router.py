from backend.features.documents import documents_router as docs_router
from backend.features.chat import chat_router
from backend.features.auth import auth_router
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(docs_router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(auth_router)
