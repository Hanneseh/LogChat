import json
from datetime import datetime

from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool

from src.database import LogChatDB
from src.database.models.log import Log, LogType
from src.logger import logger
from src.node.utils import get_current_sime_time
from src.tools.utils import safe_cast, safe_cast_to_datetime

log_db = LogChatDB()


@tool(parse_docstring=True)
def update_or_create_symptom_log(
    config: RunnableConfig,
    name: str,
    id: int = -1,
    description: str = "",
    occurred_at: str = "",
    intensity: int = -1,
    duration: int = -1,
):
    """Create or update a symptom log entry. Common symptoms in ME/CFS include fatigue, pain, brain fog, unrefreshing sleep and racing heart.

    Args:
        name (str): The name of the symptom (e.g., "Headache"). Always required.
        id (int): The id of the log to update. Leave empty to create a new log.
        description (str): The description of the symptom provided by the user.
        occurred_at (str): The time when the symptom started. Expected format: YYYY-MM-DD HH:MM:SS.
        intensity (int): The intensity of the symptom on a scale from 1 to 10 rated by the user.
        duration (int): The duration in minutes the symptom persisted put 1500 for all day.
    """
    # Cast all inputs to their expected types
    name = safe_cast(name, str)
    id = safe_cast(id, int)
    description = safe_cast(description, str)
    occurred_at = safe_cast_to_datetime(occurred_at)
    intensity = safe_cast(intensity, int)
    duration = safe_cast(duration, int)

    # extract static info from config
    configurable = config.get("configurable", {})
    user_id = configurable.get("user_id")
    thread_id = configurable.get("thread_id")
    current_sim_time = get_current_sime_time(configurable)

    # Log the tool call
    tool_args = {
        "id": id,
        "name": name,
        "description": description,
        "occurred_at": occurred_at.isoformat()
        if isinstance(occurred_at, datetime)
        else occurred_at,
        "intensity": intensity,
        "duration": duration,
    }
    action = "UPDATE" if id is not None else "CREATE"
    logger.write(
        f"{action}: SYMPTOM LOG - Args: {json.dumps(tool_args)}",
        sim_time=current_sim_time,
    )

    if id:
        symptom = log_db.get_log_by_id(id)
        if symptom is None:
            logger.error(f"Symptom with ID {id} not found.")
            return None

        symptom.name = name or symptom.name
        symptom.description = description or symptom.description
        symptom.occurred_at = occurred_at or symptom.occurred_at
        symptom.timestamp = current_sim_time
        symptom.intensity = intensity or symptom.intensity
        symptom.duration = duration or symptom.duration
        symptom.log_type = LogType.SYMPTOM
    else:
        if name is None:
            logger.error("No name for the symptom log provided.")
            return None

        symptom = Log(
            user_id=user_id,
            thread_id=thread_id,
            timestamp=current_sim_time,
            name=name,
            description=description,
            occurred_at=occurred_at,
            intensity=intensity,
            duration=duration,
            log_type=LogType.SYMPTOM,
        )

    symptom = log_db.upsert_log(symptom)
    return symptom
