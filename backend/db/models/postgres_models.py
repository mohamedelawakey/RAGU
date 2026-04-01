from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column, Integer,
    String, DateTime,
    func, JSON,
    ForeignKey, Text
)

Base = declarative_base()


# User model
class User(Base):
    __tablename__ = "users"

    id = Column(String(255), primary_key=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Document model
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="processing")
    error_message = Column(Text, nullable=True)
    metadata_info = Column(JSON, nullable=True)
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )


# Document chunk model
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(100), primary_key=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    page_number = Column(Integer, nullable=True)
    text_content = Column(Text, nullable=False)
    document = relationship(
        "Document",
        back_populates="chunks"
    )


# Chat Session model
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(100), primary_key=True)
    user_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )


# Chat Message model
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(100), primary_key=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    session = relationship("ChatSession", back_populates="messages")
