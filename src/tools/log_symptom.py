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
def log_symptom(
    config: RunnableConfig,
    name: str,
    description: str,
    occurred_at: str,
    intensity: float,
    duration: int,
):
    """Log a symptom. Common symptoms in ME/CFS include fatigue, pain, brain fog, unrefreshing sleep and racing heart.

    Args:
        name (str): The name of the symptom (e.g., "Headache").
        description (str): The description of the symptom.
        occurred_at (str): The time when the symptom started. Expected format: YYYY-MM-DD HH:MM:SS.
        intensity (float): The intensity of the symptom on a scale from 1 to 10 rated by the user.
        duration (int): The duration in minutes the symptom persisted put 1500 for all day.
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
        "intensity": intensity,
        "duration": duration,
    }
    logger.write(f"CREATE SYMPTOM LOG: {json.dumps(tool_args)}", current_sim_time)

    symptom = Log(
        user_id=user_id,
        thread_id=thread_id,
        timestamp=current_sim_time,
        name=name,
        description=description,
        occurred_at=datetime.strptime(occurred_at, "%Y-%m-%d %H:%M:%S"),
        intensity=intensity,
        duration=duration,
        log_type=LogType.SYMPTOM,
    )

    symptom = log_db.upsert_log(symptom)
    return symptom
