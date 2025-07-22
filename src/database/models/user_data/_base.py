from src.database.models._base import _Base

__all__ = ["_UserDataBase"]


class _UserDataBase(_Base):
    __abstract__ = True
    __table_args__ = {"schema": "user_data"}
