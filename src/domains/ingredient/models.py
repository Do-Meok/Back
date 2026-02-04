from sqlalchemy import Column, BigInteger, String, Date, ForeignKey, DateTime, Integer
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    compartment_id = Column(BigInteger, ForeignKey("compartment.id"))
    ingredient_name = Column(String(45), nullable=False)
    purchase_date = Column(Date, server_default=func.current_date(), nullable=False)
    expiration_date = Column(Date)
    storage_type = Column(String(10))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="ingredients")
    compartment = relationship("Compartment", back_populates="ingredients")


class IngredientExpiry(Base):
    __tablename__ = "ingredients_expiry"
    id = Column(BigInteger, primary_key=True, index=True)
    ingredient_name = Column(String(45), nullable=False)
    expiry_day = Column(Integer, nullable=False)
    storage_type = Column(String(10), nullable=False)


class ExpiryDeviationLog(Base):
    __tablename__ = "expiry_deviation_logs"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ingredient_name = Column(String(45), nullable=False)
    deviation_day = Column(Integer, nullable=False)
    storage_type = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="expiry_deviation_logs")


class MissingIngredientLog(Base):
    __tablename__ = "missing_ingredients_logs"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ingredient_name = Column(String(45), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="missing_ingredients_logs")


class NonIngredient(Base):
    __tablename__ = "non_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    ingredient_name = Column(String(45), nullable=False)
