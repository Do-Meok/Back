from sqlalchemy import Column, BigInteger, String, Date, ForeignKey, DateTime
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_name = Column(String(45), nullable=False)
    purchase_date = Column(Date, server_default=func.current_date(), nullable=False)
    expiration_date = Column(Date)
    storage_type = Column(String(10))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="ingredients")
