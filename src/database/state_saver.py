import atexit
import os

from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

load_dotenv()


class LogChatStateSaver:
    def __init__(self):
        """Initialize a postgres memory checkpointer to persist threads in a database"""
        self.connection_kwargs = {
            "autocommit": True,
            "prepare_threshold": 0,
        }
        self.db_uri = os.environ["LOG_CHAT_DB_CHECKPOINT"]
        self.checkpointer = None
        self.pool = None

    def create_checkpoint(self):
        self.pool = ConnectionPool(
            conninfo=self.db_uri,
            max_size=10,
            kwargs=self.connection_kwargs,
        )
        self.checkpointer = PostgresSaver(self.pool)
        self.checkpointer.setup()
        atexit.register(self._close)

    def _close(self):
        if self.pool:
            self.pool.close()
            self.pool = None

    def get_checkpointer(self):
        if self.checkpointer is None:
            self.create_checkpoint()
        return self.checkpointer
