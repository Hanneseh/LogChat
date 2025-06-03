from typing import Sequence

from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@tool(parse_docstring=True)
def end_conversation(command: str):
    """End the conversation.

    Args:
        command (str): The command to end the conversation. Can be any string like "end", "stop", "finish", etc.
    """
    return "END_CONVERSATION"
