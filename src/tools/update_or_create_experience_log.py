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
def update_or_create_experience_log(
    config: RunnableConfig,
    name: str,
    id: int = -1,
    description: str = "",
    occurred_at: str = "",
    intensity: int = -1,
    duration: int = -1,
):
    """Create or update an experience log entry. Experiences can be anything environmentally induced, such as bright lights, loud noises, or emotional experiences.

    Args:
        name (str): The name of the experience (e.g., Felt anxious). Always required.
        id (int): The id of the log to update. Required to update an existing log.
        description (str): the description of the experience provided by the user.
        occurred_at (str): The time when the experience occurred. Expected format: YYYY-MM-DD HH:MM:SS.
        intensity (int): The intensity of the experience on a scale from 1 to 10 rated by the user.
        duration (int): The duration in minutes the experience was observed.
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
        f"{action}: EXPERIENCE LOG - Args: {json.dumps(tool_args)}",
        sim_time=current_sim_time,
    )

    if id:
        experience = log_db.get_log_by_id(id)
        if experience is None:
            logger.error(f"Experience with ID {id} not found.")
            return None

        experience.name = name or experience.name
        experience.description = description or experience.description
        experience.occurred_at = occurred_at or experience.occurred_at
        experience.timestamp = current_sim_time
        experience.intensity = intensity or experience.intensity
        experience.duration = duration or experience.duration
        experience.log_type = LogType.EXPERIENCE
    else:
        if name is None:
            logger.error("No name provided for the experience log.")
            return None

        experience = Log(
            user_id=user_id,
            thread_id=thread_id,
            timestamp=current_sim_time,
            name=name,
            description=description,
            occurred_at=occurred_at,
            intensity=intensity,
            duration=duration,
            log_type=LogType.EXPERIENCE,
        )

    experience = log_db.upsert_log(experience)
    return experience
