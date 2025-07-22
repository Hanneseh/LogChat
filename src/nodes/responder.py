import os

from langchain_core.messages import AIMessage, HumanMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.database import LogChatDB
from src.logger import logger
from src.prompts import responder_instructions, responder_system
from src.utils import State

LOG_FULL_PROMPT = os.getenv("LOG_FULL_PROMPT", "false").lower() == "true"
MODEL_PROVIDER = os.getenv("LOG_CHAT_MODEL_PROVIDER", "ollama")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM = os.getenv("LOG_CHAT_LLM")
TEMPERATURE = 0.2
TOP_P = 0.9


class LogChatResponder:
    def __init__(self):
        if MODEL_PROVIDER.lower() == "ollama":
            self.model = ChatOllama(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                base_url=BASE_URL,
            )
        elif MODEL_PROVIDER.lower() == "google":
            self.model = ChatGoogleGenerativeAI(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                api_key=GOOGLE_API_KEY,
            )
        elif MODEL_PROVIDER.lower() == "openai":
            self.model = ChatOpenAI(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                api_key=OPENAI_API_KEY,
            )
        else:
            logger.error(
                f"Invalid model provider: {MODEL_PROVIDER}. Defaulting to Ollama."
            )
            self.model = ChatOllama(
                model="qwen2.5:14b",
                temperature=TEMPERATURE,
                top_p=TOP_P,
                base_url=BASE_URL,
            )

        self.db = LogChatDB()

        self.trimmer = trim_messages(
            max_tokens=4096,
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
                    responder_system,
                ),
                MessagesPlaceholder("messages"),
            ]
        )

    def call_model(self, state: State, config: dict = None):
        trimmed_messages = self.trimmer.invoke(state["messages"])
        configurable = config.get("configurable")
        user_name = configurable.get("user_name")
        planner_output = state["planner_output"]

        # Construct the user message
        user_message = f"""Instructions: {responder_instructions}\n\nConversation:"""
        for message in trimmed_messages:
            if message.type == "human":
                user_message += f"\n{user_name}: {message.content}"
            elif message.type == "ai":
                user_message += f"\nLogChat: {message.content}"
        user_message += f"\n\nPlanner's Suggestions:\n{planner_output}"

        prompt = self.prompt_template.invoke(
            {
                "messages": [HumanMessage(user_message)],
            }
        )

        if LOG_FULL_PROMPT:
            logger.debug(f"RESPONDER PROMPT\n{prompt.to_string()}")

        model_output = self.model.invoke(prompt)
        if "</think>" in model_output.content:
            model_output.content = model_output.content.split("</think>")[1].strip()
        output_state = {"messages": []}
        if len(model_output.content) > 0:
            output_state["messages"] = AIMessage(model_output.content)
        else:
            raise ValueError("Model output is empty")

        return output_state
