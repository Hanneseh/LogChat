import os

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.database import LogChatDB
from src.logger import logger
from src.prompts import (
    summarizer_summarize_interaction_instructions,
    summarizer_summarize_interactions_instructions,
    summarizer_system,
)
from src.utils import State, get_current_sim_time

LOG_FULL_PROMPT = os.getenv("LOG_FULL_PROMPT", "false").lower() == "true"
MODEL_PROVIDER = os.getenv("LOG_CHAT_MODEL_PROVIDER", "ollama")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM = os.getenv("LOG_CHAT_LLM")
TEMPERATURE = 0.2
TOP_P = 0.9


class LogChatSummarizer:
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
                    summarizer_system,
                ),
                MessagesPlaceholder("messages"),
            ]
        )

    def call_model(self, state: State, config: dict, summarizer_type: str):
        configurable = config.get("configurable")
        user_name = configurable.get("user_name")
        user_id = configurable.get("user_id")
        user_description = configurable.get("user_description")
        thread_id = configurable.get("thread_id")
        current_sim_time_str = get_current_sim_time(configurable, format="str")
        current_sim_time_dt = get_current_sim_time(configurable, format="datetime")
        current_sim_date_obj = current_sim_time_dt.date()

        if summarizer_type == "summarize_interaction":
            summerizer_instructions = summarizer_summarize_interaction_instructions
            content = "Conversation:"
            for message in state["messages"]:
                if message.type == "human":
                    content += f"\n{user_name}: {message.content}"
                elif message.type == "ai":
                    content += f"\nLogChat: {message.content}"
        elif summarizer_type == "summarize_interactions":
            summerizer_instructions = summarizer_summarize_interactions_instructions
            threads = self.db.get_threads(user_id)
            content = self.db.thread_summary_to_string(threads, current_sim_date_obj)
            if content is None:
                content = "No previous interaction summaries available."
        else:
            raise ValueError(f"Unknown summarizer type: {summarizer_type}")

        user_desc_str = user_description if user_description else "None."

        user_message = f"""Instructions: {summerizer_instructions}\n\nAggregated user self-description:\n{user_desc_str}\n\n{content}\n\nCurrent time: {current_sim_time_str}"""

        prompt = self.prompt_template.invoke(
            {
                "messages": [HumanMessage(user_message)],
            }
        )

        if LOG_FULL_PROMPT:
            logger.debug(f"SUMMARIZER {summarizer_type}, PROMPT: {prompt.to_string()}")

        model_output = self.model.invoke(prompt)
        if "</think>" in model_output.content:
            model_output.content = model_output.content.split("</think>")[1].strip()

        output_content = str(model_output.content) if model_output.content else ""

        if len(output_content) > 0:
            if summarizer_type == "summarize_interaction":
                logger.write(
                    f"SUMMARIZED INTERACTION: {output_content}", current_sim_time_str
                )
                self.db.update_thread(thread_id, output_content)

            if summarizer_type == "summarize_interactions":
                logger.write(
                    f"UPDATED USER DESCRIPTION: {output_content}", current_sim_time_str
                )
                self.db.update_user(user_id, output_content)
        else:
            logger.error(
                f"Model output is empty for summarizer type: {summarizer_type}"
            )

        return
