from datetime import datetime
from typing import Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from src.logger import logger


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    planner_output: str | None


def get_current_sim_time(config: dict | None, format="datetime") -> str:
    sim_time = config.get("sim_time", None)

    if not config or not sim_time:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # extract sim_time and sim_start_time from config
    sim_start_time = config.get("sim_start_time")

    # convert sim_time and sim_start_time to datetime objects
    sim_time = datetime.strptime(sim_time, "%Y-%m-%d %H:%M:%S")
    sim_start_time = datetime.strptime(sim_start_time, "%Y-%m-%d %H:%M:%S")

    # calculate the current simulated time
    current_sim_time = sim_time + (datetime.now() - sim_start_time)

    # format the current simulated time as a string
    if format == "datetime":
        return current_sim_time
    else:
        return current_sim_time.strftime("%Y-%m-%d %H:%M:%S")


def preprocess_tool_args(tool_args, tool_name: str):
    """Preprocess tool arguments to ensure each have a value of the correct type."""
    str_keys = ["name", "description", "occurred_at"]
    int_keys = ["duration"]
    if tool_name == "log_activity":
        float_keys = [
            "effort",
        ]
    elif tool_name == "log_symptom":
        float_keys = [
            "intensity",
        ]
    all_possible_keys = str_keys + int_keys + float_keys
    for key in all_possible_keys:
        if key not in tool_args or tool_args[key] is None:
            if key in ["name", "duration", "intensity"]:
                return False
            logger.warning(f"Key {key} not found in tool_args, setting default value.")
            if key == "description":
                tool_args[key] = tool_args.get("name", "No description provided")
            if key == "occurred_at":
                tool_args[key] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if key in int_keys:
            try:
                tool_args[key] = int(tool_args[key])
            except ValueError:
                return False
        if key in float_keys:
            try:
                tool_args[key] = float(tool_args[key])
            except ValueError:
                return False
        if key in str_keys:
            if key == "occurred_at":
                try:
                    _ = datetime.strptime(tool_args[key], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    tool_args[key] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                try:
                    tool_args[key] = str(tool_args[key])
                except ValueError:
                    return False

    return tool_args
