from datetime import datetime
from typing import Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    task_manager_output: str | None


def get_current_sime_time(config: dict | None, format="datetime") -> str:
    if not config:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # extract sim_time and sim_start_time from config
    sim_time = config.get("sim_time")
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


def preprocess_tool_args(tool_name, tool_args):
    """Preprocess tool arguments to ensure they are in the correct format."""
    str_keys = ["name", "description", "occurred_at", "amount", "purpose"]
    int_keys = ["id", "intensity", "duration"]
    all_possible_keys = int_keys + str_keys
    for key in all_possible_keys:
        if key not in tool_args or tool_args[key] is None:
            if key in int_keys:
                tool_args[key] = -1
            if key in str_keys:
                tool_args[key] = ""
        if key in int_keys:
            try:
                tool_args[key] = int(tool_args[key])
            except ValueError:
                tool_args[key] = -1
        if key in str_keys:
            try:
                tool_args[key] = str(tool_args[key])
            except ValueError:
                tool_args[key] = ""

    # remove keys which are unnecessary for the specific tool call
    if tool_name == "update_or_create_consumption_log":
        tool_args.pop("intensity", None)
        tool_args.pop("duration", None)
    if tool_name == "update_or_create_symptom_log":
        tool_args.pop("amount", None)
        tool_args.pop("purpose", None)
    if tool_name == "update_or_create_experience_log":
        tool_args.pop("amount", None)
        tool_args.pop("purpose", None)

    return tool_args
