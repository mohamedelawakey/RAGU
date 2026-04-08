from backend.api.dependencies import get_current_user
from backend.features.chat.service import ChatService
from fastapi.responses import StreamingResponse
import backend.core.exceptions as exceptions
from backend.features.chat.schemas import (
    ChatMessageResponse, ChatRenameRequest,
    ChatRequest, ChatSessionResponse,
)
from backend.core.rate_limit import RateLimit
from fastapi import APIRouter, Depends
from utils.logger import get_logger
from typing import List

logger = get_logger("features.chat.router")

router = APIRouter()


@router.post("/query", dependencies=[Depends(RateLimit(times=3, seconds=60))])
async def chat_query(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        return StreamingResponse(
            ChatService.stream_chat(request.query, user_id, request.session_id, request.retry_message_id),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Chat Query API Error: {e}")
        raise exceptions.InternalServerException()


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_user_sessions(user_id: str = Depends(get_current_user)):
    try:
        return await ChatService.get_user_chat_sessions(user_id)
    except Exception as e:
        logger.error(f"Error fetching user sessions: {e}")
        raise exceptions.InternalServerException()


@router.get("/sessions/{session_id}", response_model=List[ChatMessageResponse])
async def get_session_messages(session_id: str, user_id: str = Depends(get_current_user)):
    try:
        return await ChatService.get_chat_messages(session_id, user_id)
    except ValueError:
        raise exceptions.ResourceNotFoundException()
    except Exception as e:
        logger.error(f"Error fetching session context: {e}")
        raise exceptions.InternalServerException()


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(get_current_user)):
    try:
        await ChatService.delete_session(session_id, user_id)
        return {"status": "success", "message": "Session deleted"}
    except ValueError:
        raise exceptions.ResourceNotFoundException()
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise exceptions.InternalServerException()


@router.put("/sessions/{session_id}")
async def rename_session(session_id: str, request: ChatRenameRequest, user_id: str = Depends(get_current_user)):
    try:
        await ChatService.rename_session(session_id, user_id, request.title)
        return {"status": "success", "message": "Session renamed"}
    except ValueError:
        raise exceptions.ResourceNotFoundException()
    except Exception as e:
        logger.error(f"Error renaming session: {e}")
        raise exceptions.InternalServerException()
