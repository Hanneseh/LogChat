import json
from datetime import datetime

from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool

from src.database import LogChatDB
from src.database.models.user_data.log import Log, LogType
from src.logger import logger
from src.utils import get_current_sim_time

log_db = LogChatDB()


@tool(parse_docstring=True)
def log_activity(
    config: RunnableConfig,
    name: str,
    description: str,
    occurred_at: str,
    effort: float,
    duration: int,
):
    """Log an acitvity. Activities can be anything from walking to preparing food, watching TV, talking to a friend, etc.

    Args:
        name (str): The name of the activity (e.g., Walking).
        description (str): The description of the activity provided by the user.
        occurred_at (str): The time when the activity occurred. Expected format: YYYY-MM-DD HH:MM:SS.
        effort (float): The effort invested for the activity on a scale from 1 to 10 rated by the user.
        duration (int): The duration in minutes the activity was performed for.
    """
    # extract static info from config
    configurable = config.get("configurable")
    user_id = configurable.get("user_id")
    thread_id = configurable.get("thread_id")
    current_sim_time = get_current_sim_time(configurable)

    # Log the tool call
    tool_args = {
        "name": name,
        "description": description,
        "occurred_at": occurred_at,
        "effort": effort,
        "duration": duration,
    }
    logger.write(f"CREATE ACTIVITY LOG: {json.dumps(tool_args)}", current_sim_time)

    activity = Log(
        user_id=user_id,
        thread_id=thread_id,
        timestamp=current_sim_time,
        name=name,
        description=description,
        occurred_at=datetime.strptime(occurred_at, "%Y-%m-%d %H:%M:%S"),
        intensity=effort,
        duration=duration,
        log_type=LogType.ACTIVITY,
    )

    activity = log_db.upsert_log(activity)
    return activity
