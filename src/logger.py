import logging
import os
from datetime import datetime
from pathlib import Path


class LogChatLogger:
    """Central logger for the LogChat application."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogChatLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Skip re-initialization if already initialized
        if self._initialized:
            return

        # Initial setup with default values
        self._initialized = True

        # set up debug logger - this part doesn't depend on user-specific configuration
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_dir = Path(os.environ.get("LOGCHAT_LOG_DIR", "logs"), timestamp)
        os.makedirs(self.log_dir, exist_ok=True)

        self.debug_logger = logging.getLogger("DebugLogChat")
        self.debug_logger.setLevel(logging.DEBUG)
        debug_log_dir = Path(os.environ.get("LOGCHAT_LOG_DIR", "logs"))
        debug_log_file = debug_log_dir / f"{timestamp}_debug.log"
        debug_file_handler = logging.FileHandler(debug_log_file)
        debug_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        debug_file_handler.setFormatter(debug_formatter)
        self.debug_logger.addHandler(debug_file_handler)

        # The main logger will be configured later with configure()
        self.logger = None
        self.conversation_logger = None

    def configure(self, user_name: str, sim_time: str):
        """Configure the logger with user-specific information."""

        # Remove existing handlers if any
        if self.logger:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)

        if self.conversation_logger:
            for handler in self.conversation_logger.handlers[:]:
                self.conversation_logger.removeHandler(handler)

        # Set up main logger
        sim_time = sim_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger = logging.getLogger("LogChat")
        self.logger.setLevel(logging.INFO)
        log_file = (
            self.log_dir
            / f"{user_name}_{sim_time.replace(' ', '_').replace(':', '-')}_with_tools.log"
        )
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("%(simulated_time)s - %(message)s")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Set up conversation logger
        self.conversation_logger = logging.getLogger("ConversationLogChat")
        self.conversation_logger.setLevel(logging.INFO)
        conversation_log_file = (
            self.log_dir
            / f"{user_name}_{sim_time.replace(' ', '_').replace(':', '-')}_chat_only.log"
        )
        conversation_file_handler = logging.FileHandler(conversation_log_file)
        conversation_formatter = logging.Formatter("%(simulated_time)s - %(message)s")
        conversation_file_handler.setFormatter(conversation_formatter)
        self.conversation_logger.addHandler(conversation_file_handler)

        self.debug_logger.info(
            f"Logger configured for user: {user_name}, sim time: {sim_time}"
        )
        return self

    # Standard logging methods
    def write_conversation(self, message, sim_time):
        self.conversation_logger.info(
            message,
            extra={
                "simulated_time": sim_time
                if isinstance(sim_time, str)
                else sim_time.strftime("%Y-%m-%d %H:%M:%S")
            },
        )
        self.logger.info(
            message,
            extra={
                "simulated_time": sim_time
                if isinstance(sim_time, str)
                else sim_time.strftime("%Y-%m-%d %H:%M:%S")
            },
        )
        self.debug_logger.info(message)

    def write(self, message, sim_time):
        self.logger.info(
            message,
            extra={
                "simulated_time": sim_time
                if isinstance(sim_time, str)
                else sim_time.strftime("%Y-%m-%d %H:%M:%S")
            },
        )
        self.debug_logger.info(message)

    def info(self, message):
        self.debug_logger.info(message)

    def warning(self, message):
        self.debug_logger.warning(message)

    def error(self, message):
        self.debug_logger.error(message)

    def debug(self, message):
        self.debug_logger.debug(message)


# Create singleton instance
logger = LogChatLogger()
