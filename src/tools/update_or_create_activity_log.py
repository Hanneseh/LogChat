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
def update_or_create_activity_log(
    config: RunnableConfig,
    name: str,
    id: int = -1,
    description: str = "",
    occurred_at: str = "",
    intensity: int = -1,
    duration: int = -1,
    amount: str = "",
    purpose: str = "",
):
    """Create or update an activity log entry. Activities can be anything from walking to talking on the phone, watching TV, talking to a friend, etc.

    Args:
        name (str): The name of the activity (e.g., Walking). Always required.
        id (int): The id of the activity log to update. Required to update an existing log.
        description (str): The description of the activity provided by the user.
        occurred_at (str): The time when the activity occurred. Expected format: YYYY-MM-DD HH:MM:SS.
        intensity (int): The intensity of the activity on a scale from 1 to 10 rated by the user.
        duration (int): The duration in minutes the activity was performed for.
        amount (str): The quantity and unit of the activity performed (e.g., 2000 steps).
        purpose (str): The purpose of the activity (e.g., increase circulation, entertainment, socialize).
    """
    # Cast all inputs to their expected types
    name = safe_cast(name, str)
    id = safe_cast(id, int)
    description = safe_cast(description, str)
    occurred_at = safe_cast_to_datetime(occurred_at)
    intensity = safe_cast(intensity, int)
    duration = safe_cast(duration, int)
    amount = safe_cast(amount, str)
    purpose = safe_cast(purpose, str)

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
        "amount": amount,
        "purpose": purpose,
    }
    action = "UPDATE" if id is not None else "CREATE"
    logger.write(
        f"{action}: ACTIVITY LOG - Args: {json.dumps(tool_args)}",
        sim_time=current_sim_time,
    )

    if id:
        activity = log_db.get_log_by_id(id)
        if activity is None:
            logger.error(f"Activity with ID {id} not found.")
            return None

        activity.name = name or activity.name
        activity.description = description or activity.description
        activity.occurred_at = occurred_at or activity.occurred_at
        activity.timestamp = current_sim_time
        activity.intensity = intensity or activity.intensity
        activity.duration = duration or activity.duration
        activity.amount = amount or activity.amount
        activity.purpose = purpose or activity.purpose
        activity.log_type = LogType.ACTIVITY

    else:
        if name is None:
            logger.error("No name for the activity provided")
            return None

        activity = Log(
            user_id=user_id,
            thread_id=thread_id,
            timestamp=current_sim_time,
            name=name,
            description=description,
            occurred_at=occurred_at,
            intensity=intensity,
            duration=duration,
            amount=amount,
            purpose=purpose,
            log_type=LogType.ACTIVITY,
        )

    activity = log_db.upsert_log(activity)
    return activity
