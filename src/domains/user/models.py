import uuid6

from sqlalchemy import Column, String, Date, DateTime, func
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship

from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    email = Column(String(128), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    nickname = Column(String(20), nullable=False, unique=True)
    name = Column(String(20))
    birth = Column(Date)
    phone = Column(String(128))
    phone_hash = Column(String(128), unique=True)
    social_auth = Column(String(10), nullable=False, default="local")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ingredients = relationship("Ingredient", back_populates="user")
    recipes = relationship("Recipe", back_populates="user")
    shopping_list = relationship("Shopping", back_populates="user")
    refrigerator = relationship("Refrigerator", back_populates="user")
    expiry_deviation_logs = relationship("ExpiryDeviationLog", back_populates="user")
    missing_ingredients_logs = relationship("MissingIngredientLog", back_populates="user")
