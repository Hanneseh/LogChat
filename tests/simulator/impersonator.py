import os

from langchain_core.messages import trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from tests.prompts import impersonator_system_prompt
from tests.simulator.utils import State, end_conversation

api_key = os.getenv("GOOGLE_API_KEY")


class Impersonator:
    def __init__(self, persona: str, daily_report: str, sim_time: str):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.5,
            api_key=api_key,
        )

        self.persona = persona
        self.daily_report = daily_report
        self.sim_time = sim_time

        self.trimmer = trim_messages(
            max_tokens=16384 * 4,
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

    def call_model(self, state: State):
        trimmed_messages = self.trimmer.invoke(state["messages"])

        prompt = self.prompt_template.invoke(
            {
                "sim_time": self.sim_time,
                "persona": self.persona,
                "daily_report": self.daily_report,
                "messages": trimmed_messages,
            }
        )
        # print(f"Impersonator prompt: {prompt.to_string()}")
        model_output = self.model.invoke(prompt)

        for tool_call in model_output.tool_calls:
            if tool_call["name"] not in self.tools_by_name:
                continue
            tool_output = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )

            model_output.content = tool_output

        return {"messages": model_output}
