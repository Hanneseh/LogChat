import json
from collections import defaultdict
from datetime import date, datetime, timedelta

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.database.logchat_db import LogChatDB
from src.logger import logger
from src.utils import get_current_sim_time

db = LogChatDB()


@tool(parse_docstring=True)
def retrieve_activity_level(
    config: RunnableConfig,
    time_period_start: str = "",
    time_period_end: str = "",
):
    """
    Retrieves the user's daily activity level scores for a specific time period and the average.

    Args:
        time_period_start (str): The start date of the time period (e.g., "2022-04-01").
        time_period_end (str): The end date of the time period (e.g., "2022-04-07").
    """
    configurable = config.get("configurable", {})
    current_sim_time = get_current_sim_time(configurable)

    # Log the tool call
    tool_args = {
        "time_period_start": time_period_start,
        "time_period_end": time_period_end,
    }
    logger.write(
        f"RETRIEVE ACTIVITY LEVEL - Args: {json.dumps(tool_args)}",
        sim_time=current_sim_time,
    )

    user_id = config["configurable"]["user_id"]

    try:
        start_date = datetime.strptime(time_period_start, "%Y-%m-%d").date()
        end_date = datetime.strptime(time_period_end, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(
            "Invalid date format provided. Please use YYYY-MM-DD. Defaulting to last 7 days."
        )
        end_date = date.today()
        start_date = end_date - timedelta(days=6)

    if start_date > end_date:
        return "Error: Start date cannot be after end date."

    try:
        logs = db.get_activity_logs_in_period(user_id, start_date, end_date)
    except Exception as e:
        logger.error(f"Database error retrieving activity logs: {e}")
        return "Error: Could not retrieve activity logs from the database."

    if not logs:
        return f"No activity logs found for the period {start_date.isoformat()} to {end_date.isoformat()}."

    daily_scores = defaultdict(float)
    total_score = 0.0
    active_days_count = 0

    # Calculate scores per day
    for log in logs:
        if log.occurred_at and log.duration is not None and log.intensity is not None:
            log_date = log.occurred_at.date()
            # Ensure the log date is within the requested range (db query should handle this, but double-check)
            if start_date <= log_date <= end_date:
                score = float(log.duration) * float(log.intensity)
                daily_scores[log_date] += score

    # Generate full list of scores for the period, including days with 0 activity
    all_period_scores = []
    current_date = start_date
    while current_date <= end_date:
        score = daily_scores[current_date]
        all_period_scores.append(score)
        if score > 0:
            total_score += score
            active_days_count += 1
        current_date += timedelta(days=1)

    average_score = total_score / active_days_count if active_days_count > 0 else 0.0

    # Format scores as 'date: score' pairs for better readability
    formatted_scores_with_dates = [
        f"{current_date.isoformat()}: {daily_scores[current_date]:.1f}"
        for current_date in daily_scores
    ]

    result_string = (
        f"Activity scores from {start_date.isoformat()} to {end_date.isoformat()}:\n"
        f"{'; '.join(formatted_scores_with_dates)}.\n"
        f"Average Daily Score (on active days): {average_score:.1f}."
    )
    logger.info(
        f"Activity level result for user {user_id}: {result_string}",
        # sim_time=current_sim_time,
    )
    return result_string
