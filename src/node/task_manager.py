import json
import os

from langchain_core.messages import HumanMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from src.database import LogChatDB
from src.logger import logger
from src.node.prompts import task_manager_instructions, task_manager_system
from src.node.utils import State, get_current_sime_time, preprocess_tool_args
from src.tools import (
    update_or_create_activity_log,
    update_or_create_consumption_log,
    update_or_create_experience_log,
    update_or_create_symptom_log,
)

api_key = os.getenv("GOOGLE_API_KEY")
# api_key = os.getenv("OPENAI_API_KEY")


class LogChatTaskManager:
    def __init__(self):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,
            api_key=api_key,
        )

        # self.model = ChatOpenAI(
        #     model="gpt-4o-mini",  # otherwise trimmer does not work
        #     base_url="http://localhost:1234/v1",  # route to lm studio
        #     temperature=0.1,
        # )

        self.db = LogChatDB()

        self.trimmer = trim_messages(
            max_tokens=4096 * 1,
            strategy="last",
            token_counter=self.model,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

        self.tools_by_name = {
            tool.name: tool
            for tool in [
                update_or_create_symptom_log,
                update_or_create_activity_log,
                update_or_create_experience_log,
                update_or_create_consumption_log,
            ]
        }
        self.task_manager_tools = [
            update_or_create_symptom_log,
            update_or_create_activity_log,
            update_or_create_experience_log,
            update_or_create_consumption_log,
        ]
        self.model = self.model.bind_tools(self.task_manager_tools)

        self.processed_tool_calls = []

        self.prompt_template = ChatPromptTemplate(
            [
                (
                    "system",
                    task_manager_system,
                ),
                MessagesPlaceholder("messages"),
            ]
        )

    def call_model(self, state: State, config: dict = None):
        trimmed_messages = self.trimmer.invoke(state["messages"])
        configurable = config.get("configurable")
        user_id = configurable.get("user_id")
        user_name = configurable.get("user_name")
        thread_id = configurable.get("thread_id")
        current_sim_time = get_current_sime_time(configurable, format="str")

        logs = self.db.get_logs(user_id, thread_id)
        log_string = self.db.logs_to_string(logs)

        # Construct the user message
        user_message = f"""Instructions: {task_manager_instructions}\n\nCurrent time: {current_sim_time}\n\nLogged logs: \n{log_string}\n\nConversation:"""
        for message in trimmed_messages:
            if message.type == "human":
                user_message += f"\n{user_name}: {message.content}"
            elif message.type == "ai":
                user_message += f"\nLogChat: {message.content}"

        prompt = self.prompt_template.invoke(
            {
                "messages": [HumanMessage(user_message)],
            }
        )

        logger.debug("TASKMANAGER")
        logger.debug(prompt.to_string())

        model_output = self.model.invoke(prompt)

        for tool_call in model_output.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            tool_args = preprocess_tool_args(tool_name, tool_args)

            if tool_name not in self.tools_by_name:
                logger.warning(
                    f"Invalid tool call: {tool_call['name']}. Skipping tool invocation."
                )
                continue

            tool_args_without_id = tool_args.copy()
            tool_args_without_id.pop("id", None)

            if tool_args_without_id in self.processed_tool_calls:
                logger.warning(
                    f"Repeated tool call detected with Args: {json.dumps(tool_args)}."
                )
                continue

            _ = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"], config=config
            )

            self.processed_tool_calls.append(tool_args_without_id)

        output_state = {"messages": [], "task_manager_output": ""}
        if len(model_output.content) > 0:
            output_state["task_manager_output"] = model_output.content

        return output_state
