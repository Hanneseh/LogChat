import uuid
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as EnumColumn
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.user_data._base import _UserDataBase as Base

if TYPE_CHECKING:
    from .logchat_user import LogChatUser


class LogType(Enum):
    """Enum for differentiating log types"""

    SYMPTOM = "symptom"
    ACTIVITY = "activity"


class Log(Base):
    """SQLAlchemy log model for storing user logs"""

    __tablename__ = "log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user_data.logchat_user.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_data.thread.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    timestamp: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=False)
    occurred_at: Mapped[Optional[str]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    log_type: Mapped[LogType] = mapped_column(EnumColumn(LogType), nullable=False)

    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    intensity: Mapped[Optional[float]] = mapped_column(Float, nullable=False)

    # Relationships
    user: Mapped["LogChatUser"] = relationship("LogChatUser", back_populates="logs")
