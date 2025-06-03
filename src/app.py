from datetime import datetime
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.database import LogChatDB, LogChatStateSaver
from src.database.models import Thread
from src.logger import logger
from src.node import (
    LogChatResponseGenerator,
    LogChatTaskManager,
    State,
    get_current_sime_time,
)


class LogChat:
    def __init__(
        self,
        user_id: int,
        state_saver: str = "postgres",
        sim_time: str | None = None,
    ):
        self.first_invocation = True

        self.db = LogChatDB()
        self.user = self.db.get_user(user_id)

        thread = Thread(id=uuid4(), user_id=user_id, timestamp=datetime.now())

        self.db.set_thread(thread)

        # Initialize the time
        current_time_dt = datetime.now()
        sim_time_dt = (
            datetime.strptime(sim_time, "%Y-%m-%d %H:%M:%S")
            if sim_time
            else current_time_dt
        )

        if sim_time:
            sim_time_dt = sim_time_dt.replace(
                minute=current_time_dt.minute,
                second=current_time_dt.second,
                microsecond=current_time_dt.microsecond,
            )

        # convert sim_time to string
        sim_time_value = sim_time_dt.strftime("%Y-%m-%d %H:%M:%S")

        self.config = {
            "configurable": {
                "thread_id": thread.id,
                "user_id": self.user.id,
                "user_name": self.user.name,
                "sim_time": sim_time_value,
                "sim_start_time": current_time_dt.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

        logger.configure(self.user.name, sim_time_value)

        if state_saver.lower() == "memory":
            checkpointer = MemorySaver()
        elif state_saver.lower() == "postgres":
            memory = LogChatStateSaver()
            checkpointer = memory.get_checkpointer()

        task_manager = LogChatTaskManager()
        response_generator = LogChatResponseGenerator()

        graph = StateGraph(State)
        graph.add_node("task_manager", task_manager.call_model)
        graph.add_node("response_generator", response_generator.call_model)

        graph.add_edge(START, "task_manager")
        graph.add_edge("task_manager", "response_generator")
        graph.add_edge("response_generator", END)

        self.app = graph.compile(checkpointer=checkpointer)

    def get_user_name(self) -> str:
        return self.user.name

    def run(self, message: str | list) -> str:
        """
        Run the LogChat application with the given message.

        Args:
            message (str | list): The message to process

        Returns:
            str: The response message
        """
        messages = []
        if self.first_invocation:
            self.first_invocation = False
            greeting_msg = f"Hi {self.user.name}! How are you?"
            messages.extend(
                [
                    HumanMessage("Hi"),
                    AIMessage(greeting_msg),
                ]
            )
            logger.write_conversation(
                f"LogChat: {greeting_msg}",
                sim_time=get_current_sime_time(self.config["configurable"]),
            )

        if isinstance(message, str):
            messages.append(HumanMessage(message))
            logger.write_conversation(
                f"{self.user.name}: {message}",
                sim_time=get_current_sime_time(self.config["configurable"]),
            )
        elif isinstance(message, list):
            messages.extend(message)

        output = self.app.invoke({"messages": messages}, self.config)
        logger.write_conversation(
            f"LogChat: {output['messages'][-1].content}",
            sim_time=get_current_sime_time(self.config["configurable"]),
        )

        return output["messages"][-1].content
