from sqlalchemy import Column, BigInteger, ForeignKey, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import Uuid
from sqlalchemy.sql import func

from core.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    food_name = Column(String(45), nullable=False)
    recipe = Column(JSONB, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="recipes")
