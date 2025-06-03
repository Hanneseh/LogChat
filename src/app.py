from datetime import datetime
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.database import LogChatDB
from src.database.models.user_data import LogType, Thread
from src.logger import logger
from src.nodes import (
    LogChatExtractor,
    LogChatOpener,
    LogChatPlanner,
    LogChatResponder,
    LogChatSummarizer,
    State,
    get_current_sim_time,
)


class LogChat:
    def __init__(
        self,
        user_id: int,
        sim_time: str | None = None,
    ):
        self.opener = []

        self.db = LogChatDB()
        self.user = self.db.get_user(user_id)

        # Initialize the time
        current_time_dt = datetime.now()
        sim_time_dt = (
            datetime.strptime(sim_time, "%Y-%m-%d %H:%M:%S")
            if sim_time
            else current_time_dt
        )

        # get thread summaries
        current_sim_date_obj = sim_time_dt.date()
        threads = self.db.get_threads(user_id)
        self.thread_summaries = self.db.thread_summary_to_string(
            threads, current_sim_date_obj
        )

        if sim_time:
            sim_time_dt = sim_time_dt.replace(
                minute=current_time_dt.minute,
                second=current_time_dt.second,
                microsecond=current_time_dt.microsecond,
            )

        thread = Thread(id=uuid4(), user_id=user_id, timestamp=sim_time_dt)
        self.db.set_thread(thread)

        # convert sim_time to string
        sim_time_value = sim_time_dt.strftime("%Y-%m-%d %H:%M:%S")

        self.config = {
            "configurable": {
                "thread_id": thread.id,
                "user_id": self.user.id,
                "user_description": self.user.description,
                "thread_summaries": self.thread_summaries,
                "user_name": self.user.name,
                "sim_time": sim_time_value,
                "sim_start_time": current_time_dt.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

        logger.configure(self.user.name, sim_time_value)

        checkpointer = MemorySaver()

        planner = LogChatPlanner()
        responder = LogChatResponder()

        graph = StateGraph(State)
        graph.add_node("planner", planner.call_model)
        graph.add_node("responder", responder.call_model)

        graph.add_edge(START, "planner")
        graph.add_edge("planner", "responder")
        graph.add_edge("responder", END)

        self.app = graph.compile(checkpointer=checkpointer)

    def get_user_name(self) -> str:
        return self.user.name

    def get_opener(self) -> str:
        """
        Get the opener message for the user.

        Returns:
            str: The opener message
        """
        opener = LogChatOpener()
        opener_message = opener.call_model(self.config)
        self.opener.extend(
            [
                HumanMessage("Hi"),
                AIMessage(opener_message),
            ]
        )
        logger.write_conversation(
            f"LogChat: {opener_message}",
            sim_time=get_current_sim_time(self.config["configurable"]),
        )

        return opener_message

    def post_interaction_routine(self) -> None:
        """
        Post interaction routine to save the state of the conversation.
        """
        extractor = LogChatExtractor()
        summarizer = LogChatSummarizer()
        state = self.app.get_state(self.config).values
        summarizer.call_model(
            state,
            self.config,
            summarizer_type="summarize_interaction",
        )
        summarizer.call_model(
            state,
            self.config,
            summarizer_type="summarize_interactions",
        )
        extractor.call_model(
            state,
            self.config,
            log_type=LogType.ACTIVITY,
        )
        extractor.call_model(
            state,
            self.config,
            log_type=LogType.SYMPTOM,
        )

    def run(self, message: str) -> str:
        """
        Run the LogChat application with the given message.

        Args:
            message (str): The message to process

        Returns:
            str: The response message
        """
        logger.write_conversation(
            f"{self.user.name}: {message}",
            sim_time=get_current_sim_time(self.config["configurable"]),
        )
        if len(self.opener) > 0:
            messages = self.opener.copy()
            messages.append(HumanMessage(message))
            self.opener = []

        else:
            messages = [HumanMessage(message)]

        output = self.app.invoke({"messages": messages}, self.config)
        logger.write_conversation(
            f"LogChat: {output['messages'][-1].content}",
            sim_time=get_current_sim_time(self.config["configurable"]),
        )

        return output["messages"][-1].content
