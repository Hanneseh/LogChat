import os

from langchain_core.messages import AIMessage, HumanMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from src.database import LogChatDB
from src.logger import logger
from src.node.prompts import response_generator_instructions, response_generator_system
from src.node.utils import State

api_key = os.getenv("GOOGLE_API_KEY")
# api_key = os.getenv("OPENAI_API_KEY")


class LogChatResponseGenerator:
    def __init__(self):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.8,
            api_key=api_key,
        )

        # self.model = ChatOpenAI(
        #     model="gpt-4o-mini",  # otherwise trimmer does not work
        #     base_url="http://localhost:1234/v1",  # route to lm studio
        #     temperature=0.8,
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

        self.prompt_template = ChatPromptTemplate(
            [
                (
                    "system",
                    response_generator_system,
                ),
                MessagesPlaceholder("messages"),
            ]
        )

    def call_model(self, state: State, config: dict = None):
        trimmed_messages = self.trimmer.invoke(state["messages"])
        configurable = config.get("configurable")
        user_id = configurable.get("user_id")
        thread_id = configurable.get("thread_id")
        user_name = configurable.get("user_name")
        logs = self.db.get_logs(user_id, thread_id)
        log_string = self.db.logs_to_string(logs)
        task_manager_output = state["task_manager_output"]

        # Construct the user message
        user_message = f"""Instructions: {response_generator_instructions}\n\nLogged logs:\n{log_string}\n\nConversation:"""
        for message in trimmed_messages:
            if message.type == "human":
                user_message += f"\n{user_name}: {message.content}"
            elif message.type == "ai":
                user_message += f"\nLogChat: {message.content}"
        user_message += (
            f"\n\nSuggestion from the log-extractor-llm:\n{task_manager_output}"
        )

        prompt = self.prompt_template.invoke(
            {
                "messages": [HumanMessage(user_message)],
            }
        )
        logger.debug("RESPONSEGENERATOR")
        logger.debug(prompt.to_string())

        model_output = self.model.invoke(prompt)
        output_state = {"messages": []}
        if len(model_output.content) > 0:
            output_state["messages"] = AIMessage(model_output.content)
        else:
            raise ValueError("Model output is empty")

        return output_state
