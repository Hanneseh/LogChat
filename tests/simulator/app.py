from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from tests.simulator.impersonator import Impersonator
from tests.simulator.utils import State


class Simulator:
    def __init__(self, persona: str, daily_report: str, sim_time: str):
        self.config = {"configurable": {"thread_id": "eval"}}

        checkpointer = MemorySaver()
        impersonator = Impersonator(persona, daily_report, sim_time)

        graph = StateGraph(State)
        graph.add_node("impersonator", impersonator.call_model)
        graph.add_edge(START, "impersonator")
        graph.add_edge("impersonator", END)

        self.app = graph.compile(checkpointer=checkpointer)

    def run(self, message: str) -> str:
        messages = [HumanMessage(message)]

        output = self.app.invoke({"messages": messages}, self.config)
        return output["messages"][-1].content
