import json
import os

from langchain_core.messages import trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from src.logger import logger
from tests.prompts import impersonator_system_prompt
from tests.simulator.utils import State, end_conversation

api_key = os.getenv("GOOGLE_API_KEY")
LOG_FULL_PROMPT = os.getenv("LOG_FULL_PROMPT", "false").lower() == "true"
IMPERSONATOR_LLM = os.getenv("IMPERSONATOR_LLM", "gemini-2.0-flash")
TEMPERATURE = 0.3
TOP_P = 0.9


class Impersonator:
    def __init__(
        self, persona: str, interaction_style: str, daily_report: list, sim_time: str
    ):
        self.model = ChatGoogleGenerativeAI(
            model=IMPERSONATOR_LLM,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            api_key=api_key,
        )

        self.persona = persona
        self.interaction_style = interaction_style
        self.daily_report = daily_report
        self.sim_time = sim_time

        self.trimmer = trim_messages(
            max_tokens=4096 * 4,
            strategy="last",
            token_counter=self.model,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )
        self.tools_by_name = {
            tool.name: tool
            for tool in [
                end_conversation,
            ]
        }

        self.model = self.model.bind_tools([end_conversation])

        self.prompt_template = ChatPromptTemplate(
            [
                (
                    "system",
                    impersonator_system_prompt,
                ),
                MessagesPlaceholder("messages"),
            ]
        )

    def call_model(self, state: State, config: dict = None):
        trimmed_messages = self.trimmer.invoke(state["messages"])
        configurable = config.get("configurable")
        thread_summaries = configurable.get("thread_summaries")

        prompt = self.prompt_template.invoke(
            {
                "sim_time": self.sim_time,
                "persona": self.persona,
                "interaction_style": self.interaction_style,
                "daily_report": json.dumps(self.daily_report, indent=2),
                "interaction_summaries": thread_summaries,
                "messages": trimmed_messages,
            }
        )
        if LOG_FULL_PROMPT:
            logger.debug(f"IMPERSONATOR PROMPT\n{prompt.to_string()}")

        model_output = self.model.invoke(prompt)

        for tool_call in model_output.tool_calls:
            if tool_call["name"] not in self.tools_by_name:
                continue
            tool_output = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )

            model_output.content = tool_output

        return {"messages": model_output}
