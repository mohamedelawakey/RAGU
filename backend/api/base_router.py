from backend.features.dashboard.router import router as dashboard_router
from backend.features.documents import documents_router as docs_router
from backend.features.contact.router import router as contact_router
from backend.features.chat import chat_router
from backend.features.auth import auth_router
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(docs_router, prefix="/documents", tags=["Documents"])
api_router.include_router(contact_router, prefix="/contact", tags=["Contact"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(auth_router)
