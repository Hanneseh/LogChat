from typing import TYPE_CHECKING, List

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models._base import _Base as Base

if TYPE_CHECKING:
    from .log import Log
    from .thread import Thread

__all__ = ["LogChatUser"]


class LogChatUser(Base):
    __tablename__ = "logchat_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    threads: Mapped[List["Thread"]] = relationship("Thread", back_populates="user")
    logs: Mapped[List["Log"]] = relationship("Log", back_populates="user")
