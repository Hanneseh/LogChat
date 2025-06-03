from src.database.models._base import _Base

__all__ = ["_KnowledgeBase"]


class _KnowledgeBase(_Base):
    __abstract__ = True
    __table_args__ = {"schema": "knowledge"}
