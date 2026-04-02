from backend.features.documents.schemas import DocumentUploadResponse, DocumentStatusResponse
from backend.features.documents.service import DocumentService
from backend.api.dependencies import get_db, get_current_user
from fastapi import APIRouter, Depends, UploadFile, File
from typing import List
import backend.core.exceptions as exceptions
from utils.logger import get_logger
from asyncpg import Connection

logger = get_logger("features.documents.router")

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    try:
        return await DocumentService.process_document(file, user_id, db)
    except (exceptions.ForbiddenException, exceptions.UnsupportedMediaTypeException, exceptions.PayloadTooLargeException):
        raise
    except Exception as e:
        logger.error(f"Document Upload Error: {e}")
        raise exceptions.InternalServerException()


@router.get("/status/{doc_id}", response_model=DocumentStatusResponse)
async def get_document_status(
    doc_id: int,
    user_id: str = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    try:
        return await DocumentService.get_document_status(doc_id, user_id, db)
    except exceptions.ResourceNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document status for doc {doc_id}: {e}")
        raise exceptions.InternalServerException()


@router.get("/", response_model=List[DocumentStatusResponse])
async def get_all_user_documents(
    user_id: str = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    try:
        return await DocumentService.get_user_documents(user_id, db)
    except Exception as e:
        logger.error(f"Error fetching documents list for user {user_id}: {e}")
        raise exceptions.InternalServerException()


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    user_id: str = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    try:
        await DocumentService.delete_document(doc_id, user_id, db)
        return {"detail": "Document deleted successfully"}
    except exceptions.ResourceNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {doc_id} for user {user_id}: {e}")
        raise exceptions.InternalServerException()
