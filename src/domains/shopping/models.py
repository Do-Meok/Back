from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from domains.user.models import User

class Shopping(Base):
    __tablename__ = "shopping_list"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item: Mapped[str] = mapped_column(String(45))
    status: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="shopping_list")
