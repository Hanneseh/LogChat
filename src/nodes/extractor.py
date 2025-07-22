import os

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.database import LogChatDB
from src.database.models.user_data import LogType
from src.logger import logger
from src.prompts import (
    extractor_extract_activities_instructions,
    extractor_extract_symptoms_instructions,
    extractor_system,
)
from src.tools import log_activity, log_symptom
from src.utils import State, get_current_sim_time, preprocess_tool_args

MODEL_PROVIDER = os.getenv("LOG_CHAT_MODEL_PROVIDER", "ollama")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LOG_FULL_PROMPT = os.getenv("LOG_FULL_PROMPT", "false").lower() == "true"
LLM = os.getenv("LOG_CHAT_LLM")
TEMPERATURE = 0.2
TOP_P = 0.9


class LogChatExtractor:
    def __init__(self):
        self.db = LogChatDB()

        self.prompt_template = ChatPromptTemplate(
            [
                (
                    "system",
                    extractor_system,
                ),
                MessagesPlaceholder("messages"),
            ]
        )

    def call_model(self, state: State, config: dict, log_type: LogType):
        if MODEL_PROVIDER.lower() == "ollama":
            model = ChatOllama(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                base_url=BASE_URL,
            )
        elif MODEL_PROVIDER.lower() == "google":
            model = ChatGoogleGenerativeAI(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                api_key=GOOGLE_API_KEY,
            )
        elif MODEL_PROVIDER.lower() == "openai":
            model = ChatOpenAI(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                api_key=OPENAI_API_KEY,
            )
        else:
            logger.error(f"Invalid model provider: {MODEL_PROVIDER}.")
            self.model = ChatOllama(
                model="qwen2.5:14b",
                temperature=TEMPERATURE,
                base_url=BASE_URL,
                top_p=TOP_P,
            )

        configurable = config.get("configurable")
        user_id = configurable.get("user_id")
        user_name = configurable.get("user_name")
        user_description = configurable.get("user_description")
        current_sim_time = get_current_sim_time(configurable, format="str")
        current_sim_time_dt = get_current_sim_time(configurable, format="datetime")
        current_sim_date_obj = current_sim_time_dt.date()

        threads = self.db.get_threads(user_id)
        thread_summaries = self.db.thread_summary_to_string(
            threads, current_sim_date_obj
        )
        is_first_interaction = not user_description and not thread_summaries

        # Conditionally bind tools and select instructions
        if log_type == LogType.SYMPTOM:
            base_instructions = extractor_extract_symptoms_instructions
            tools_by_name = {tool.name: tool for tool in [log_symptom]}
            extractor_tools = [log_symptom]
            if is_first_interaction:
                base_instructions += "\n\n**First Interaction Note:** Focus on extracting any initial symptoms mentioned by the user as they describe their situation for the first time."

        elif log_type == LogType.ACTIVITY:
            base_instructions = extractor_extract_activities_instructions
            tools_by_name = {tool.name: tool for tool in [log_activity]}
            extractor_tools = [log_activity]
            # Add specific guidance for first interaction if needed
            if is_first_interaction:
                base_instructions += "\n\n**First Interaction Note:** Pay close attention to any activities the user mentions while introducing themselves or describing their typical day/limitations for the first time."
        else:
            logger.error(f"Invalid log type: {log_type}.")
            return

        model = model.bind_tools(extractor_tools)

        # Construct the user message with potentially modified instructions
        user_desc_str = (
            user_description
            if user_description
            else "None. (This is the first interaction)."
        )
        thread_sum_str = (
            thread_summaries
            if thread_summaries
            else "No interaction summaries yet. This is the first interaction."
        )

        user_message = f"""Instructions: {base_instructions}\n\nAggregated user self-description:\n{user_desc_str}\n\n{thread_sum_str}\n\nCurrent time: {current_sim_time}\n\nCurrent Conversation:"""

        for message in state["messages"]:
            # Ensure message content is treated as string
            content = str(message.content) if message.content else ""
            if message.type == "human":
                user_message += f"\n{user_name}: {content}"
            elif message.type == "ai":
                if isinstance(message.content, str):  # Standard AI response
                    user_message += f"\nLogChat: {content}"
            elif message.type == "tool":
                pass

        prompt = self.prompt_template.invoke(
            {
                "messages": [HumanMessage(user_message)],
            }
        )

        if LOG_FULL_PROMPT:
            logger.debug(f"EXTRACTOR {log_type}, PROMPT: {prompt.to_string()}")

        model_output = model.invoke(prompt)

        for tool_call in model_output.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name not in tools_by_name:
                logger.warning(
                    f"Invalid tool call: {tool_call['name']}. Skipping tool invocation."
                )
                continue

            tool_args = preprocess_tool_args(tool_args, tool_name)
            if not tool_args:
                logger.warning(
                    f"Invalid tool arguments for {tool_name}: {tool_call['args']}. Skipping tool invocation."
                )
                continue
            _ = tools_by_name[tool_call["name"]].invoke(
                tool_call["args"], config=config
            )

        return
