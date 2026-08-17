from __future__ import annotations

import uuid 
from typing import Any, Dict, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
 
if TYPE_CHECKING: 
    from app.models.user import User
    from app.models.document import Document

class Space(Base):
    __tablename__ = "space"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    thread_id: Mapped[UUID] = mapped_column(
        UUID, nullable=False, default=uuid.uuid4
    )
    tool_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default={}, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user: Mapped[User] = relationship(
        "User", back_populates="spaces"
    )
    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="space", cascade="all, delete-orphan"
    )
