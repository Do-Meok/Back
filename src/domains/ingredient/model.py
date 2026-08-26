from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import uuid6
from sqlalchemy import BigInteger, Date, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from domains.user.model import User


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[uuid6.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ingredient_name: Mapped[str] = mapped_column(String(45))
    created_at: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    # 릴레이션
    user: Mapped[User] = relationship(back_populates="ingredients")
