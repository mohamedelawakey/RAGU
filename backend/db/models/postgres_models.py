from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column, Integer,
    String, DateTime,
    func, JSON,
    ForeignKey, Text
)

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="processing")
    metadata_info = Column(JSON, nullable=True)
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(100), primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=True)
    text_content = Column(Text, nullable=False)
    document = relationship(
        "Document",
        back_populates="chunks"
    )
