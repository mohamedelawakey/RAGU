from pydantic import BaseModel
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    message: str


class DocumentStatusResponse(BaseModel):
    id: int
    filename: str
    status: str
    upload_date: datetime
