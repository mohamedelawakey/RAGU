from pipeline.retrieval.chat_retriever import ChatMemoryRetriever
from backend.db.connections.postgres import PostgresDBConnection
from pipeline.orchestrator.orchestrator import RAGPipeline
from utils.logger import get_logger
from backend.config import Config
from typing import AsyncGenerator
import asyncio
import uuid
import json
import re

logger = get_logger("features.chat.service")


def is_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text))


class ChatService:
    @staticmethod
    async def get_user_chat_sessions(user_id: str) -> list:
        async with PostgresDBConnection.get_db_connection() as conn:
            records = await conn.fetch(Config.GET_USER_CHAT_SESSIONS_QUERY, user_id)
            return [dict(r) for r in records]

    @staticmethod
    async def get_chat_messages(session_id: str, user_id: str) -> list:
        async with PostgresDBConnection.get_db_connection() as conn:
            session = await conn.fetchrow("SELECT id FROM chat_sessions WHERE id = $1 AND user_id = $2", session_id, user_id)
            if not session:
                raise ValueError("Session not found or forbidden")
            records = await conn.fetch(Config.GET_CHAT_MESSAGES_QUERY, session_id)
            return [dict(r) for r in records]

    @staticmethod
    async def delete_session(session_id: str, user_id: str) -> None:
        async with PostgresDBConnection.get_db_connection() as conn:
            result = await conn.execute(Config.DELETE_CHAT_SESSION_QUERY, session_id, user_id)
            if result == "DELETE 0":
                raise ValueError("Session not found or forbidden")

    @staticmethod
    async def rename_session(session_id: str, user_id: str, new_title: str) -> None:
        async with PostgresDBConnection.get_db_connection() as conn:
            result = await conn.execute(
                Config.RENAME_CHAT_SESSION_QUERY,
                new_title,
                session_id,
                user_id
            )

            if result == "UPDATE 0":
                raise ValueError("Session not found or forbidden")

    @staticmethod
    async def stream_chat(
        query: str,
        user_id: str,
        session_id: str = None,
        retry_message_id: str = None
    ) -> AsyncGenerator[str, None]:
        is_new_session = False
        if not session_id:
            session_id = str(uuid.uuid4())
            is_new_session = True
            title = query[:Config.CHAT_MAX_TITLE_LENGTH] + "..." if len(query) > Config.CHAT_MAX_TITLE_LENGTH else query

        user_message_id = retry_message_id if retry_message_id else str(uuid.uuid4())

        async with PostgresDBConnection.get_db_connection() as conn:
            if is_new_session:
                await conn.execute(
                    Config.INSERT_CHAT_SESSION_QUERY,
                    session_id,
                    user_id,
                    title
                )
            else:
                await conn.execute(
                    Config.UPDATE_CHAT_SESSION_TIME_QUERY,
                    session_id
                )

            if retry_message_id:
                await conn.execute(
                    Config.DELETE_SUBSEQUENT_CHAT_MESSAGES_QUERY,
                    session_id,
                    retry_message_id
                )
            else:
                await conn.execute(
                    Config.INSERT_CHAT_MESSAGE_QUERY,
                    user_message_id,
                    session_id,
                    "user",
                    query
                )

        chat_retriever = ChatMemoryRetriever()
        if not retry_message_id:
            asyncio.create_task(
                chat_retriever.insert_memory(user_message_id, session_id, user_id, "user", query)
            )

        history_msgs = []
        logger.info(f"ChatService: Stream initialized. session_id={session_id}, is_new={is_new_session}")
        if not is_new_session:
            try:
                all_msgs = await ChatService.get_chat_messages(session_id, user_id)
                logger.info(f"ChatService: Fetched {len(all_msgs)} total DB messages for session {session_id}")
                if len(all_msgs) > 1:
                    history_msgs = all_msgs[:-1][-Config.CHAT_SHORT_TERM_HISTORY_LIMIT:]
                logger.info(f"ChatService: Sliced short-term history length = {len(history_msgs)}")
            except Exception as e:
                logger.error(f"Failed to fetch short-term history: {e}")

        yield f"data: {json.dumps({'session_id': session_id})}\n\n"

        try:
            pipeline = RAGPipeline()
            sync_gen = await pipeline.query(query, user_id, session_id=session_id, history=history_msgs)
        except ValueError as ve:
            if str(ve) == "RATE_LIMIT_EXCEEDED":
                error_msg = Config.CHAT_RATE_LIMIT_MSG_AR if is_arabic(query) else Config.CHAT_RATE_LIMIT_MSG_EN
                payload = json.dumps({"text": error_msg}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            else:
                logger.error(f"ChatService value error: {ve}")
                yield f"data: {Config.CHAT_ERROR_INVALID_PARAMS}\n\n"
            return
        except Exception as e:
            logger.error(f"ChatService failed to initialize pipeline query: {e}")
            yield f"data: {Config.CHAT_ERROR_PIPELINE_INIT}\n\n"
            return

        if not sync_gen:
            error_msg = Config.CHAT_NO_INFO_MSG_AR if is_arabic(query) else Config.CHAT_NO_INFO_MSG_EN
            payload = json.dumps({"text": error_msg}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            return

        loop = asyncio.get_running_loop()
        assistant_message_id = str(uuid.uuid4())

        q = asyncio.Queue()
        full_assistant_response = []

        async def _background_consumer():
            try:
                while True:
                    chunk = await loop.run_in_executor(None, next, sync_gen, None)
                    if chunk is None:
                        break

                    full_assistant_response.append(chunk)
                    await q.put(chunk)
            except Exception as e:
                logger.error(f"ChatService stream consumer error: {e}")
                await q.put(f"[ERROR] {str(e)}")
            finally:
                await q.put(None)

                final_text = "".join(full_assistant_response)
                if final_text:
                    try:
                        async with PostgresDBConnection.get_db_connection() as conn:
                            await conn.execute(Config.INSERT_CHAT_MESSAGE_QUERY, assistant_message_id, session_id, "assistant", final_text)

                        await chat_retriever.insert_memory(assistant_message_id, session_id, user_id, "assistant", final_text)
                        logger.info(f"ChatService: Background response saved for session {session_id}")
                    except Exception as db_err:
                        logger.error(f"Failed to save background response to DB: {db_err}")

        asyncio.create_task(_background_consumer())

        while True:
            chunk = await q.get()
            if chunk is None:
                break

            if isinstance(chunk, str) and chunk.startswith("[ERROR]"):
                yield f"data: {chunk}\n\n"
                break

            payload = json.dumps({"text": chunk}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
