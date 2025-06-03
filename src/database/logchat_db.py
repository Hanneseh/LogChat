import atexit
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import scoped_session, sessionmaker

from src.database.models import LogChatUser, Thread
from src.database.models.log import (
    Log,
    LogType,
)

load_dotenv()


class LogChatDB:
    _instance = None

    def __new__(cls):
        """Ensure only one instance of LogChatDB exists (Singleton Pattern)."""
        if cls._instance is None:
            cls._instance = super(LogChatDB, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        """Initialize the database connection and session factory."""
        db_uri = os.environ["LOG_CHAT_DB"]
        engine = create_engine(
            db_uri,
            pool_size=10,
            max_overflow=5,
            pool_timeout=30,
            pool_recycle=1800,
        )
        session_factory = sessionmaker(bind=engine)
        self.session = scoped_session(session_factory)
        atexit.register(self._close)

    def _close(self):
        """Ensure the session is properly closed on exit."""
        if hasattr(self, "session"):
            self.session.remove()

    @contextmanager
    def get_session(self):
        """Provide a session context, ensuring cleanup after use."""
        session = self.session()
        try:
            yield session
            session.commit()  # Commit changes automatically
        except Exception:
            session.rollback()  # Rollback on error
            raise
        finally:
            session.close()

    def get_user(self, user_id: int) -> LogChatUser:
        """Get a user from the database."""
        with self.get_session() as session:
            user = session.get(LogChatUser, user_id)
            session.expunge(user)
        if user is None:
            raise ValueError(f"User with ID {user_id} not found.")
        return user

    def get_logs(self, user_id: int, thread_id: str, limit: int = 100) -> list[Log]:
        """ "Get the most recent logs for a user."""
        with self.get_session() as session:
            logs = (
                session.query(Log)
                .filter_by(user_id=user_id)
                .filter_by(thread_id=thread_id)
                .order_by(desc(Log.timestamp))
                .limit(limit)
                .all()
            )
            session.expunge_all()
            return logs

    def upsert_log(self, log: Log):
        """Save or update a log entry."""
        with self.get_session() as session:
            merged_log = session.merge(log)
            session.flush()
            session.refresh(merged_log)
            session.expunge(merged_log)
            return merged_log

    def get_log_by_id(
        self,
        log_id: int,
    ) -> Log | None:
        """Get the log entry with the given ID."""
        with self.get_session() as session:
            log = session.get(Log, log_id)
            if log:
                session.expunge(log)
            return log

    def set_thread(self, thread: Thread) -> Thread:
        """Save a thread for a user only if the user exists."""
        with self.get_session() as session:
            session.add(thread)
            session.flush()
            session.refresh(thread)
            session.expunge(thread)
            return thread

    def clear_data_for_user(self, user_id: int):
        """Delete all logs and threads for a user."""
        with self.get_session() as session:
            session.query(Log).filter_by(user_id=user_id).delete()
            session.query(Thread).filter_by(user_id=user_id).delete()
            session.commit()

    def logs_to_string(self, logs: list[Log]) -> str:
        """Convert a list of log ORM objects into a string representation.

        Each log is formatted as:
        <Log Type> - ID: <ID> - timestamp: <Timestamp> - name: <Name> - description: <Description> - occurred_at: <Occurred At> - <Optional Fields based on Log Type>

        Possible optional fields:
        - For Symptom: intensity, duration, severity
        - For Activity: intensity, duration, amount, purpose
        - For Consumption: amount, purpose
        - For Experience: intensity, duration

        Example:
        Symptom - ID: 123 - timestamp: 2024-01-01 10:00:00 - name: Headache - description: Throbbing pain in temples - occurred_at: 2024-01-01 09:30:00 - intensity: 7 - duration: 60 - severity: 6

        Args:
            logs (list): A list of Log objects.

        Returns:
            str: A string representation of all logs, one log per line. Returns "Nothing logged yet." if the list is empty.
        """
        output_lines = []

        for log in logs:
            log_type = log.log_type.value.capitalize()

            # Format common fields; assume timestamp and occurred_at are datetime objects
            ts = log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else None
            occ = (
                log.occurred_at.strftime("%Y-%m-%d %H:%M:%S")
                if log.occurred_at
                else None
            )

            # Start with the common structure
            line = f"{log_type} ID: {log.id} - timestamp: {ts} - name: {log.name} - description: {log.description} - occurred_at: {occ}"

            # Append log type specific fields based on log_type enum
            if log.log_type == LogType.SYMPTOM:
                extras = []
                if log.intensity is not None:
                    extras.append(f"intensity: {log.intensity}")
                if log.duration is not None:
                    extras.append(f"duration: {log.duration}")
                if log.intensity is not None:
                    extras.append(f"intensity: {log.intensity}")
                if extras:
                    line += " - " + " - ".join(extras)
            elif log.log_type == LogType.ACTIVITY:
                extras = []
                if log.intensity is not None:
                    extras.append(f"intensity: {log.intensity}")
                if log.duration is not None:
                    extras.append(f"duration: {log.duration}")
                if log.amount is not None:
                    extras.append(f"amount: {log.amount}")
                if log.purpose is not None:
                    extras.append(f"purpose: {log.purpose}")
                if extras:
                    line += " - " + " - ".join(extras)
            elif log.log_type == LogType.CONSUMPTION:
                extras = []
                if log.amount is not None:
                    extras.append(f"amount: {log.amount}")
                if log.purpose is not None:
                    extras.append(f"purpose: {log.purpose}")
                if log.purpose is not None:
                    extras.append(f"purpose: {log.purpose}")
                if extras:
                    line += " - " + " - ".join(extras)
            elif log.log_type == LogType.EXPERIENCE:
                extras = []
                if log.intensity is not None:
                    extras.append(f"intensity: {log.intensity}")
                if log.duration is not None:
                    extras.append(f"duration: {log.duration}")
                if extras:
                    line += " - " + " - ".join(extras)

            output_lines.append(line)

        if not output_lines:
            return "Nothing was logged yet from the current conversation."
        return "\n".join(output_lines)
