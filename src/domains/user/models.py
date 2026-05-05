from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Date, DateTime, func, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

if TYPE_CHECKING:
    from domains.ingredient.models import Ingredient
    from domains.recipe.models import Recipe
    from domains.shopping.models import Shopping
    from domains.refrigerator.models import Refrigerator


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)
    email: Mapped[str | None] = mapped_column(String(128), unique=True)
    password: Mapped[str | None] = mapped_column(String(128))
    nickname: Mapped[str] = mapped_column(String(20))

    # 개인정보 영역
    name: Mapped[str | None] = mapped_column(String(20))
    birth: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str | None] = mapped_column("phone_encrypt", String(128))
    phone_hash: Mapped[str | None] = mapped_column(String(128), unique=True)

    # 소셜 로그인 영역
    provider: Mapped[str] = mapped_column(String(10), default="local")
    social_id: Mapped[str | None] = mapped_column(String(128), unique=True)

    # 삭제시기 및 생성시기
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 릴레이션
    ingredients: Mapped[list[Ingredient]] = relationship(back_populates="user")
    recipes: Mapped[list[Recipe]] = relationship(back_populates="user")
    shopping_list: Mapped[list[Shopping]] = relationship(back_populates="user")
    refrigerator: Mapped[list[Refrigerator]] = relationship(back_populates="user")

    expiry_deviation_logs = relationship("ExpiryDeviationLog", back_populates="user")
    missing_ingredients_logs = relationship("MissingIngredientLog", back_populates="user")

    __table_args__ = (
        # 닉네임 대소문자 중복 닉네임 방지
        Index("ix_user_nickname_lower", func.lower(nickname), unique=True),
        # 생성일 기준 정렬을 위한 일반 인덱스 설정
        Index("ix_user_created_at", created_at.desc()),
        # 회원 정보 찾기 관련 인덱싱
        Index("ix_active_user_recovery", "name", "birth", "phone_hash", postgresql_where=text("deleted_at IS NULL")),
    )
