import atexit
import os
from contextlib import contextmanager
from datetime import date, timedelta

from dotenv import load_dotenv
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import scoped_session, sessionmaker

from src.database.models.knowledge import Knowledge
from src.database.models.user_data import LogChatUser, Thread
from src.database.models.user_data.log import (
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

    def get_logs(self, user_id: int, thread_id: str, limit: int = 15) -> list[Log]:
        """Get the most recent logs for a user and thread."""  # Updated docstring
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

    def get_activity_logs_in_period(
        self, user_id: int, start_date: date, end_date: date
    ) -> list[Log]:
        """Get activity logs for a user within a specific date range."""
        with self.get_session() as session:
            # Ensure end_date is inclusive by adding one day for the upper bound
            end_date_inclusive = end_date + timedelta(days=1)
            logs = (
                session.query(Log)
                .filter(Log.user_id == user_id)
                .filter(Log.log_type == LogType.ACTIVITY)
                .filter(Log.occurred_at.isnot(None))
                .filter(Log.occurred_at >= start_date)
                .filter(Log.occurred_at < end_date_inclusive)
                .order_by(Log.occurred_at)
                .all()
            )
            session.expunge_all()
            return logs

    def get_threads(self, user_id: int):
        """Get all interaction summaries for a user, ordered by timestamp descending."""
        with self.get_session() as session:
            threads = (
                session.query(Thread)
                .filter_by(user_id=user_id)
                .filter(Thread.summary.isnot(None))
                .order_by(desc(Thread.timestamp))
                .all()
            )
            session.expunge_all()
            return threads

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

    def update_thread(self, thread_id, summary):
        """Update the summary of a thread."""
        with self.get_session() as session:
            thread = session.query(Thread).filter_by(id=thread_id).first()
            if thread:
                thread.summary = summary
                session.commit()
            else:
                raise ValueError(f"Thread with ID {thread_id} not found.")

    def update_user(self, user_id: int, description: str):
        """Update the description of a user."""
        with self.get_session() as session:
            user = session.query(LogChatUser).filter_by(id=user_id).first()
            if user:
                user.description = description
                session.commit()
            else:
                raise ValueError(f"User with ID {user_id} not found.")

    def perform_vector_search_with_scores(
        self, query_embedding: list[float], limit: int
    ) -> list[tuple[Knowledge, float]]:
        """Performs the vector similarity search and returns results with scores."""
        with self.get_session() as session:
            results = (
                session.query(
                    Knowledge,
                    Knowledge.embedding.cosine_distance(query_embedding).label("score"),
                )
                .order_by(Knowledge.embedding.cosine_distance(query_embedding))
                .limit(limit)
                .all()
            )
            # Expunge results before returning to detach them from the session
            for knowledge, score in results:
                session.expunge(knowledge)
            return results

    def format_results(self, results: list[Knowledge]) -> str:
        """Formats the retrieved knowledge chunks into a string."""
        if not results:
            return "No relevant information found in the knowledge base."

        formatted_chunks = []
        for i, chunk in enumerate(results):
            formatted_chunks.append(
                f"{chunk.headline}: {chunk.content} \\n(Source: {chunk.source})"
            )
        return "\n".join(formatted_chunks)

    def thread_summary_to_string(
        self, threads: list["Thread"], current_sim_date: date, limit: int = 5
    ) -> str | None:
        """Convert a list of thread ORM objects into a string representation,
        placing summaries first in chronological order (oldest shown first, most recent shown last),
        followed by placeholders for missing days up to the day before the current simulated date.

        Limits the output to the most recent 'limit' summaries.
        Formats each thread as: 'Interaction on YYYY-MM-DD HH:MM:SS:\n<Summary>\n'
        Adds placeholders like: "No interaction logged for YYYY-MM-DD." for days missing
        between the most recent non-current-date interaction and the current_sim_date.

        Args:
            threads (list): A list of Thread objects, ordered descending by timestamp (most recent first).
            current_sim_date (date): The current simulated date for context.
            limit (int): The maximum number of summaries to include. Defaults to 5.

        Returns:
            str: A string representation of recent threads and placeholders in chronological order,
                or None if no threads exist.
        """
        if not threads:
            return None

        total_interactions = len(threads)

        # sort threads in ascending order by timestamp
        threads.sort(key=lambda x: x.timestamp)
        recent_threads_for_display = threads.copy()

        # Group threads and placeholders chronologically
        output_items = {}

        # Process threads chronologically
        for thread in recent_threads_for_display:
            thread_date = thread.timestamp.date()
            ts = thread.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            summary = f"Interaction on {ts}:\n{thread.summary}"
            output_items[thread_date] = summary

        # remove thread from the same day as current_sim_date
        recent_threads_for_display = [
            thread
            for thread in recent_threads_for_display
            if thread.timestamp.date() != current_sim_date
        ]
        latest_thread_date = (
            recent_threads_for_display[-1].timestamp.date()
            if recent_threads_for_display
            else None
        )
        yesterday = current_sim_date - timedelta(days=1)
        if latest_thread_date != yesterday and latest_thread_date:
            # we need to add a placeholder for all days starting yesterday up to the day before latest_thread_date
            placeholder_date = yesterday
            while placeholder_date > latest_thread_date:
                placeholder = f"No interaction logged for {placeholder_date.strftime('%Y-%m-%d')}."
                output_items[placeholder_date] = placeholder
                placeholder_date -= timedelta(days=1)

        # order the output_times by date ascending
        output_items = dict(sorted(output_items.items()))
        output_items = [summary for _, summary in output_items.items()]

        # Limit the output to the most recent 'limit' summaries
        if len(output_items) > limit:
            output_items = output_items[-limit:]
        header = (
            f"Interaction Summary (Total Interactions: {total_interactions}, "
            f"showing last {len(output_items)} interactions chronologically, "
            f"with placeholders for missed days before {current_sim_date.strftime('%Y-%m-%d')}):"
        )

        return header + "\n\n" + "\n\n".join(output_items)

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
        Symptom - timestamp: 2024-01-01 10:00:00 - name: Headache - description: Throbbing pain in temples - occurred_at: 2024-01-01 09:30:00 - intensity: 7 - duration: 60

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
            line = f"{log_type} - timestamp: {ts} - name: {log.name} - description: {log.description} - occurred_at: {occ} - intensity: {log.intensity} - duration: {log.duration}"

            output_lines.append(line)

        if not output_lines:
            return "Nothing was logged yet from the current conversation."
        return "\n".join(output_lines)

    def add_knowledge_chunk(
        self,
        source: str,
        headline: str | None,
        content: str,
        embedding: list[float],
    ):
        """Adds a new knowledge chunk to the database."""
        knowledge_entry = Knowledge(
            source=source,
            headline=headline,
            content=content,
            embedding=embedding,
        )
        with self.get_session() as session:
            session.add(knowledge_entry)

    def clear_data_for_user(self, user_id: int):
        """Delete all logs and threads for a user."""
        with self.get_session() as session:
            session.query(Log).filter_by(user_id=user_id).delete()
            session.query(Thread).filter_by(user_id=user_id).delete()
            user = session.query(LogChatUser).filter_by(id=user_id).first()
            if user:
                user.description = None
            session.commit()

    def get_activity_and_symptom_logs_by_user(self, user_id: int):
        """Retrieve all activity and symptom logs for a user, grouped by date."""
        with self.get_session() as session:
            logs = (
                session.query(Log)
                .filter(Log.user_id == user_id)
                .filter(Log.log_type.in_([LogType.ACTIVITY, LogType.SYMPTOM]))
                .order_by(Log.occurred_at)
                .all()
            )
            session.expunge_all()
            return logs
