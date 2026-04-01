from backend.mq.producers.ingestion_producer import IngestionProducer
from backend.core.exceptions import (
    ForbiddenException,
    PayloadTooLargeException,
    UnsupportedMediaTypeException,
    ResourceNotFoundException
)
from utils.logger import get_logger
from backend.config import Config
from fastapi import UploadFile
from asyncpg import Connection
import uuid
import os

logger = get_logger("features.documents.service")

os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

try:
    from pymilvus import Collection
except ImportError:
    Collection = None


class DocumentService:
    @staticmethod
    async def verify_user_quota(user_id: str, db: Connection):
        count = await db.fetchval(Config.CHECK_USER_DOCUMENT_QUOTA_QUERY, user_id)
        if count >= Config.MAX_FILES_PER_USER:
            raise ForbiddenException(
                detail=f"Upload quota exceeded. Max {Config.MAX_FILES_PER_USER} documents allowed per user."
            )

    @staticmethod
    async def secure_save_upload(file: UploadFile, user_id: str) -> str:
        if file.content_type != "application/pdf":
            raise UnsupportedMediaTypeException(
                detail="Only PDF files are supported."
            )

        first_bytes = await file.read(5)
        if first_bytes != b"%PDF-":
            raise UnsupportedMediaTypeException(
                detail="File is not a valid PDF document (magic bytes mismatch)."
            )

        safe_filename = f"{uuid.uuid4()}.pdf"
        user_dir = os.path.join(Config.UPLOAD_DIR, user_id)
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, safe_filename)

        total_size = len(first_bytes)
        try:
            with open(file_path, "wb") as f:
                f.write(first_bytes)
                while chunk := await file.read(1024 * 1024):
                    total_size += len(chunk)
                    if total_size > Config.MAX_FILE_SIZE_BYTES:
                        raise PayloadTooLargeException(
                            detail="File size exceeds the 50MB limit."
                        )
                    f.write(chunk)
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e

        return file_path

    @staticmethod
    async def process_document(file: UploadFile, user_id: str, db: Connection) -> dict:
        await DocumentService.verify_user_quota(user_id, db)

        file_path = await DocumentService.secure_save_upload(file, user_id)

        doc_id = await db.fetchval(
            Config.INSERT_DOCUMENT_QUERY,
            user_id, file.filename, file_path
        )

        await IngestionProducer.publish_ingestion_job(
            file_path=file_path,
            user_id=user_id,
            document_id=doc_id
        )

        logger.info(f"Document {doc_id} uploaded securely for user {user_id}. Job published.")

        return {
            "id": doc_id,
            "filename": file.filename,
            "status": "pending",
            "message": "Document uploaded securely and queued for processing."
        }

    @staticmethod
    async def get_document_status(doc_id: int, user_id: str, db: Connection) -> dict:
        record = await db.fetchrow(
            Config.GET_DOCUMENT_STATUS_QUERY,
            doc_id, user_id
        )
        if not record:
            raise ResourceNotFoundException(
                detail="Document not found or access denied."
            )

        return dict(record)

    @staticmethod
    async def get_user_documents(user_id: str, db: Connection) -> list:
        records = await db.fetch(
            Config.GET_USER_DOCUMENTS_QUERY,
            user_id
        )
        return [dict(r) for r in records]

    @staticmethod
    async def delete_document(doc_id: int, user_id: str, db: Connection) -> bool:
        file_path = await db.fetchval(
            Config.DELETE_DOCUMENT_QUERY,
            doc_id, user_id
        )

        if not file_path:
            raise ResourceNotFoundException(detail="Document not found or access denied.")

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted physical file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete physical file {file_path}: {e}")

        if Collection:
            try:
                collection_name = os.getenv("COLLECTION_NAME", "edu_chunks")
                collection = Collection(collection_name)
                collection.delete(f"document_id == {doc_id}")
                logger.info(f"Deleted Milvus vectors for document {doc_id}")
            except Exception as e:
                logger.error(f"Failed to delete Milvus vectors for document {doc_id}: {e}")

        return True
