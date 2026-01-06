from sqlalchemy import Column, TIMESTAMP, BigInteger, String, Date, text, ForeignKey
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
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    owner = relationship("User", back_populates="ingredients")
