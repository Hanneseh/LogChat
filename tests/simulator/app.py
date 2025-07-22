from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from tests.simulator.impersonator import Impersonator
from tests.simulator.utils import State


class Simulator:
    def __init__(
        self,
        persona: str,
        interaction_style: str,
        daily_report: list,
        sim_time: str,
        thread_summaries: str,
    ):
        self.config = {
            "configurable": {
                "thread_id": "eval",
                "thread_summaries": thread_summaries,
            }
        }

        checkpointer = MemorySaver()
        impersonator = Impersonator(persona, interaction_style, daily_report, sim_time)

        graph = StateGraph(State)
        graph.add_node("impersonator", impersonator.call_model)
        graph.add_edge(START, "impersonator")
        graph.add_edge("impersonator", END)

        self.app = graph.compile(checkpointer=checkpointer)

    def run(self, message: str) -> str:
        messages = [HumanMessage(message)]

        output = self.app.invoke({"messages": messages}, self.config)
        return output["messages"][-1].content
