from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    retry_message_id: Optional[str] = None


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class ChatRenameRequest(BaseModel):
    title: str
