from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Integer, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from domains.user.models import User
    from domains.ingredient.models import Ingredient


class Refrigerator(Base):
    __tablename__ = "refrigerator"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(10))
    pos_x: Mapped[int] = mapped_column(Integer)
    pos_y: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="refrigerator")

    compartments: Mapped[list[Compartment]] = relationship(
        back_populates="refrigerator",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Compartment(Base):
    __tablename__ = "compartment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    refrigerator_id: Mapped[int] = mapped_column(ForeignKey("refrigerator.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(10))
    order_index: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    refrigerator: Mapped[Refrigerator] = relationship(back_populates="compartments")

    ingredients: Mapped[list[Ingredient]] = relationship(
        "Ingredient", back_populates="compartment", cascade="all, delete-orphan", passive_deletes=True
    )
