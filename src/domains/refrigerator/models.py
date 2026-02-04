from sqlalchemy import Column, BigInteger, ForeignKey, String, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class Refrigerator(Base):
    __tablename__ = "refrigerator"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(10), nullable=False)
    pos_x = Column(Integer, nullable=False)
    pos_y = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="refrigerator")
    compartments = relationship("Compartment", back_populates="refrigerator")


class Compartment(Base):
    __tablename__ = "compartment"

    id = Column(BigInteger, primary_key=True, index=True)
    refrigerator_id = Column(ForeignKey("refrigerator.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(10), nullable=False)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    refrigerator = relationship("Refrigerator", back_populates="compartments")
    ingredients = relationship("Ingredient", back_populates="compartment")
