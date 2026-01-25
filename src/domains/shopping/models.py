from sqlalchemy import Column, BigInteger, ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base

class Shopping(Base):
    __tablename__ = "shopping_list"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item = Column(String(45), nullable=False)
    status = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="shopping_list")
