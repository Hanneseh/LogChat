import os

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.database import LogChatDB
from src.logger import logger
from src.prompts import first_opener, opener_instructions, opener_system
from src.utils import get_current_sim_time

LOG_FULL_PROMPT = os.getenv("LOG_FULL_PROMPT", "false").lower() == "true"
MODEL_PROVIDER = os.getenv("LOG_CHAT_MODEL_PROVIDER", "ollama")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM = os.getenv("LOG_CHAT_LLM")
TEMPERATURE = 0.2
TOP_P = 0.9


class LogChatOpener:
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

        self.prompt_template = ChatPromptTemplate(
            [
                (
                    "system",
                    opener_system,
                ),
                MessagesPlaceholder("messages"),
            ]
        )

    def call_model(self, config: dict = None):
        configurable = config.get("configurable")
        user_id = configurable.get("user_id")
        user_name = configurable.get("user_name")
        user_description = configurable.get("user_description")
        current_sim_time_str = get_current_sim_time(configurable, format="str")
        current_sim_time_dt = get_current_sim_time(configurable, format="datetime")
        current_sim_date_obj = current_sim_time_dt.date()

        threads = self.db.get_threads(user_id)
        thread_summaries = self.db.thread_summary_to_string(
            threads, current_sim_date_obj
        )
        opener = first_opener

        if user_description:
            input_message = (
                f"Instructions: {opener_instructions}\n\n"
                f"User Name: {user_name}\n\n"
                f"Aggregated user self-description (Long-Term Memory Profile):\n{user_description}\n\n"
                f"Interaction Summary:\n{thread_summaries}\n\n"
                f"Current time: {current_sim_time_str}"
            )

            prompt = self.prompt_template.invoke(
                {
                    "messages": [HumanMessage(input_message)],
                }
            )

            if LOG_FULL_PROMPT:
                logger.debug(f"OPENER PROMPT\n{prompt.to_string()}")

            model_output = self.model.invoke(prompt)
            if "</think>" in model_output.content:
                model_output.content = model_output.content.split("</think>")[1].strip()

            if model_output.content and len(str(model_output.content)) > 0:
                opener = str(model_output.content).strip()

        return opener
