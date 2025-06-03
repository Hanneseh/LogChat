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
def update_or_create_consumption_log(
    config: RunnableConfig,
    name: str,
    id: int = -1,
    description: str = "",
    occurred_at: str = "",
    amount: str = "",
    purpose: str = "",
):
    """Create or update a consumption log entry. Consumption can be anything that is ingested, such as food, drink, or medication or supplements.

    Args:
        name (str): The name of the consumption item (e.g., Orange Juice, Magnesium, Porridge). Always required.
        id (int): The id of the consumption log to update. Required to update an existing log.
        description (str): The description of the consumption provided by the user.
        occurred_at (str): The time when the consumption occurred. Expected format: YYYY-MM-DD HH:MM:SS.
        amount (str): The quantity and unit consumed (e.g., 200ml, 2 tablets, 1 bowl).
        purpose (str): The purpose for the consumption (e.g., hydration, muscle relaxation, breakfast).
    """
    # Cast all inputs to their expected types
    name = safe_cast(name, str)
    id = safe_cast(id, int)
    description = safe_cast(description, str)
    occurred_at = safe_cast_to_datetime(occurred_at)
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
        "amount": amount,
        "purpose": purpose,
    }
    action = "UPDATE" if id is not None else "CREATE"
    logger.write(
        f"{action}: CONSUMPTION LOG - Args: {json.dumps(tool_args)}",
        sim_time=current_sim_time,
    )

    if id:
        consumption = log_db.get_log_by_id(id)
        if consumption is None:
            logger.error(f"Consumption with ID {id} not found.")
            return None

        consumption.name = name or consumption.name
        consumption.description = description or consumption.description
        consumption.occurred_at = occurred_at or consumption.occurred_at
        consumption.timestamp = current_sim_time
        consumption.amount = amount or consumption.amount
        consumption.purpose = purpose or consumption.purpose
        consumption.log_type = LogType.CONSUMPTION
    else:
        if name is None:
            logger.error("No name for the activity log provided.")
            return None
        consumption = Log(
            user_id=user_id,
            thread_id=thread_id,
            timestamp=current_sim_time,
            name=name,
            description=description,
            occurred_at=occurred_at,
            amount=amount,
            purpose=purpose,
            log_type=LogType.CONSUMPTION,
        )

    consumption = log_db.upsert_log(consumption)
    return consumption
