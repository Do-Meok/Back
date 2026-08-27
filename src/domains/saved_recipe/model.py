from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import uuid6
from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from core.database import Base

if TYPE_CHECKING:
    from domains.user.model import User


class SavedRecipe(Base):
    __tablename__ = "saved_recipe"

    id: Mapped[uuid6.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    user_id: Mapped[uuid6.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(16))
    source_id: Mapped[str] = mapped_column(String(512))
    recipe_name: Mapped[str] = mapped_column(String(256))
    recipe_difficulty: Mapped[str | None] = mapped_column(String(64))
    time: Mapped[str | None] = mapped_column(String(64))
    snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="saved_recipes",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "source", "source_id", name="uq_saved_recipes_user_source"),
        Index("ix_saved_recipes_user_created", "user_id", created_at.desc()),
    )
