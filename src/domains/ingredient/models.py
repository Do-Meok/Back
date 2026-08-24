from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from domains.refrigerator.models import Compartment

    from domains.user.models import User


class Ingredient(Base):
    __tablename__ = "ingredients"

    # 고유정보(식재료 ID, 유저ID, 분류칸ID)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    compartment_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("compartment.id"))

    # 식재료 관련 정보(식재료 이름, 저장 방식, 유통기한, 구매날짜)
    ingredient_name: Mapped[str] = mapped_column(String(45))
    storage_type: Mapped[str | None] = mapped_column(String(10))
    expiration_date: Mapped[date | None] = mapped_column(Date)
    purchase_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())

    # 삭제시기 및 생성시기
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 릴레이션
    user: Mapped[User] = relationship(back_populates="ingredients")
    compartment: Mapped[Compartment | None] = relationship("Compartment", back_populates="ingredients")

    __table_args__ = (
        # user_id와 compartment_id를 묶어서 인덱스 생성
        Index("ix_ingredient_user_compartment", "user_id", "compartment_id"),
    )


class IngredientExpiry(Base):
    __tablename__ = "ingredients_expiry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    ingredient_name: Mapped[str] = mapped_column(String(45), nullable=False)
    expiry_day: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_type: Mapped[str] = mapped_column(String(10), nullable=False)


class ExpiryDeviationLog(Base):
    __tablename__ = "expiry_deviation_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ingredient_name: Mapped[str] = mapped_column(String(45), nullable=False)
    deviation_day: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_type: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="expiry_deviation_logs")


class MissingIngredientLog(Base):
    __tablename__ = "missing_ingredients_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ingredient_name: Mapped[str] = mapped_column(String(45), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="missing_ingredients_logs")


class NonIngredient(Base):
    __tablename__ = "non_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_name: Mapped[str] = mapped_column(String(45), nullable=False)
