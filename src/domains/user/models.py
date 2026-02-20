import uuid6

from sqlalchemy import Column, String, Date, DateTime, func, Index
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship

from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    email = Column(String(128), unique=True)
    password = Column(String(128))
    nickname = Column(String(20), nullable=False, unique=True)
    name = Column(String(20))
    birth = Column(Date)
    phone = Column(String(128))
    phone_hash = Column(String(128), unique=True)
    provider = Column(String(10), nullable=False, default="local")
    social_id = Column(String(128), unique=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ingredients = relationship("Ingredient", back_populates="user")
    recipes = relationship("Recipe", back_populates="user")
    shopping_list = relationship("Shopping", back_populates="user")
    refrigerator = relationship("Refrigerator", back_populates="user")
    expiry_deviation_logs = relationship("ExpiryDeviationLog", back_populates="user")
    missing_ingredients_logs = relationship("MissingIngredientLog", back_populates="user")

    __table_args__ = (
        # 닉네임 대소문자 무시 (Unique)
        Index("ix_user_nickname_lower", func.lower(nickname), unique=True),
        # 활성 유저에 대해서만 소셜 로그인/리커버리 정보 인덱싱 (Partial Index)
        Index("ix_active_user_social", "provider", "social_id", postgresql_where=(deleted_at.is_(None))),
        Index("ix_active_user_recovery", "name", "birth", "phone_hash", postgresql_where=(deleted_at.is_(None))),
        # 생성일 기준 정렬을 위한 일반 인덱스
        Index("ix_user_created_at", created_at.desc()),
    )
