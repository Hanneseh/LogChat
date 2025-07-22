import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.user_data._base import _UserDataBase as Base

if TYPE_CHECKING:
    from .logchat_user import LogChatUser

__all__ = ["Thread"]


class Thread(Base):
    __tablename__ = "thread"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_data.logchat_user.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    timestamp: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    user: Mapped["LogChatUser"] = relationship("LogChatUser", back_populates="threads")
