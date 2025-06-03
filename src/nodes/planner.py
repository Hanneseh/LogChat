import json
import os

from langchain_core.messages import HumanMessage, ToolMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.database import LogChatDB
from src.logger import logger
from src.prompts import (
    initial_thread_summaries,
    initial_user_description,
    planner_instructions,
    planner_instructions_with_tool_results,
    planner_system,
)
from src.tools import retrieve_activity_level, retrieve_information
from src.utils import State, get_current_sim_time

LOG_FULL_PROMPT = os.getenv("LOG_FULL_PROMPT", "false").lower() == "true"
MODEL_PROVIDER = os.getenv("LOG_CHAT_MODEL_PROVIDER", "ollama")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM = os.getenv("LOG_CHAT_LLM")
TEMPERATURE = 0.2
TOP_P = 0.9


class LogChatPlanner:
    def __init__(self):
        if MODEL_PROVIDER.lower() == "ollama":
            self.model_with_tools = ChatOllama(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                base_url=BASE_URL,
            )
            self.model_without_tools = ChatOllama(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                base_url=BASE_URL,
            )
        elif MODEL_PROVIDER.lower() == "google":
            self.model_with_tools = ChatGoogleGenerativeAI(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                api_key=GOOGLE_API_KEY,
            )
            self.model_without_tools = ChatGoogleGenerativeAI(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                api_key=GOOGLE_API_KEY,
            )
        elif MODEL_PROVIDER.lower() == "openai":
            self.model_with_tools = ChatOpenAI(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                api_key=OPENAI_API_KEY,
            )
            self.model_without_tools = ChatOpenAI(
                model=LLM,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                api_key=OPENAI_API_KEY,
            )
        else:
            logger.error(
                f"Invalid model provider: {MODEL_PROVIDER}. Defaulting to Ollama."
            )
            self.model_with_tools = ChatOllama(
                model="qwen2.5:14b",
                temperature=TEMPERATURE,
                base_url=BASE_URL,
                top_p=TOP_P,
            )
            self.model_without_tools = ChatOllama(
                model="qwen2.5:14b",
                temperature=TEMPERATURE,
                base_url=BASE_URL,
                top_p=TOP_P,
            )

        self.db = LogChatDB()

        self.trimmer = trim_messages(
            max_tokens=4096,
            strategy="last",
            token_counter=self.model_with_tools,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

        self.tools_by_name = {
            tool.name: tool
            for tool in [
                retrieve_activity_level,
                retrieve_information,
            ]
        }

        self.planner_tools = [
            retrieve_activity_level,
            retrieve_information,
        ]

        self.model_with_tools = self.model_with_tools.bind_tools(self.planner_tools)

        self.prompt_template = ChatPromptTemplate(
            [
                (
                    "system",
                    planner_system,
                ),
                MessagesPlaceholder("messages"),
            ]
        )

    def _prepare_base_input_string(self, state: State, config: dict):
        """Helper function to prepare the common input string for the planner."""
        trimmed_messages_for_context = self.trimmer.invoke(state["messages"])
        configurable = config.get("configurable", {})
        user_name = configurable.get("user_name", "User")
        user_description = configurable.get("user_description")
        current_sim_time_str = get_current_sim_time(configurable, format="str")
        thread_summaries = configurable.get("thread_summaries")

        if not user_description:
            user_description = initial_user_description
        if not thread_summaries:
            thread_summaries = initial_thread_summaries

        context_and_history = f"Aggregated user self-description:\n{user_description}\n\n{thread_summaries}\n\nCurrent time: {current_sim_time_str}\n\nCurrent Conversation:"
        for message in trimmed_messages_for_context:
            if message.type == "human":
                context_and_history += f"\n{user_name}: {message.content}"
            elif message.type == "ai":
                ai_content = f"\nLogChat: {message.content}"
                if hasattr(message, "tool_calls") and message.tool_calls:
                    ai_content += f" (called tools: {json.dumps(message.tool_calls)})"
                context_and_history += ai_content

        return context_and_history

    def call_model(self, state: State, config: dict = None):
        context_and_history_str = self._prepare_base_input_string(state, config)
        initial_prompt_str = (
            f"Instructions: {planner_instructions}\n\n{context_and_history_str}"
        )

        # Initial call with tools
        prompt_for_initial_call = self.prompt_template.invoke(
            {"messages": [HumanMessage(initial_prompt_str)]}
        )
        if LOG_FULL_PROMPT:
            logger.debug(
                f"PLANNER INITIAL PROMPT\n{prompt_for_initial_call.to_string()}"
            )
        model_output = self.model_with_tools.invoke(prompt_for_initial_call)

        # remove any <think> tags from the model output content
        if hasattr(model_output, "content") and "</think>" in model_output.content:
            model_output.content = model_output.content.split("</think>")[1].strip()

        retrieved_information_items = []
        executed_tool_calls_for_state = []

        # execute initial tool calls if they exist
        if model_output.tool_calls:
            for tool_call in model_output.tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["args"]
                tool_call_id = tool_call["id"]
                executed_tool_calls_for_state.append(tool_call)

                if tool_name not in self.tools_by_name:
                    logger.warning(
                        f"Invalid tool call: {tool_name}. Skipping tool invocation."
                    )
                    retrieved_information_items.append(
                        ToolMessage(
                            content=f"Error: Tool '{tool_name}' not found.",
                            tool_call_id=tool_call_id,
                        )
                    )
                    continue
                try:
                    retrieved_data = self.tools_by_name[tool_name].invoke(
                        tool_input, config=config
                    )
                    retrieved_data_str = (
                        str(retrieved_data)
                        if retrieved_data is not None
                        else "No data returned."
                    )
                    retrieved_information_items.append(
                        ToolMessage(
                            content=retrieved_data_str, tool_call_id=tool_call_id
                        )
                    )
                except Exception as e:
                    logger.error(
                        f"Error executing tool {tool_name} with args {tool_input}: {e}"
                    )
                    retrieved_information_items.append(
                        ToolMessage(
                            content=f"Error executing tool {tool_name}: {str(e)}",
                            tool_call_id=tool_call_id,
                        )
                    )

        # collect all retrieved information items
        retrieved_information_str_combined = ""
        if retrieved_information_items:
            retrieved_information_str_combined = "\nTool Results:\n" + "\n".join(
                [f"- {item.content}" for item in retrieved_information_items]
            )

        planner_suggestion_content = (
            model_output.content if hasattr(model_output, "content") else ""
        )

        # Re-prompt if no suggestion was made but tool calls were executed
        if (
            not planner_suggestion_content
            and model_output.tool_calls
            and retrieved_information_items
        ):
            logger.info(
                "PLANNER: Initial call returned only tool calls. Re-prompting for suggestion based on tool results."
            )

            reprompt_input_str = (
                f"Instructions: {planner_instructions_with_tool_results}\n\n"
                f"{context_and_history_str}\n"
                f"\nTool Call Results:\n"
            )
            for tool_msg in retrieved_information_items:
                original_call = next(
                    (
                        tc
                        for tc in executed_tool_calls_for_state
                        if tc["id"] == tool_msg.tool_call_id
                    ),
                    None,
                )
                if original_call:
                    reprompt_input_str += f"- Tool: {original_call['name']}({json.dumps(original_call['args'])}) -> Result: {tool_msg.content}\n"
                else:
                    reprompt_input_str += f"- Tool Result (ID: {tool_msg.tool_call_id}): {tool_msg.content}\n"

            prompt_for_reprompt = self.prompt_template.invoke(
                {"messages": [HumanMessage(content=reprompt_input_str)]}
            )
            if LOG_FULL_PROMPT:
                logger.debug(f"PLANNER RE-PROMPT\n{prompt_for_reprompt.to_string()}")

            # Call the model without tools for the re-prompt
            reprompt_output = self.model_without_tools.invoke(prompt_for_reprompt)

            if (
                hasattr(reprompt_output, "content")
                and "</think>" in reprompt_output.content
            ):
                reprompt_output.content = reprompt_output.content.split("</think>")[
                    1
                ].strip()

            planner_suggestion_content = (
                reprompt_output.content if hasattr(reprompt_output, "content") else ""
            )
            if planner_suggestion_content:
                logger.info(f"PLANNER (after re-prompt): {planner_suggestion_content}")
            else:
                logger.warning(
                    "PLANNER: No content returned from model even after re-prompting with tool results."
                )
        elif planner_suggestion_content:
            logger.info(f"PLANNER (initial with content): {planner_suggestion_content}")
        else:
            logger.warning(
                "PLANNER: No content from model and no tool calls made or no tool results."
            )

        output_state = {"messages": [], "planner_output": ""}
        final_planner_output = planner_suggestion_content

        # Append tool results to the planner's output if available
        if final_planner_output and retrieved_information_str_combined:
            final_planner_output += (
                f"\n\n--- Retrieved Information ---{retrieved_information_str_combined}"
            )
        elif not final_planner_output and retrieved_information_str_combined:
            final_planner_output = f"--- Retrieved Information ---{retrieved_information_str_combined}\n\nSuggestion: Based on the above, ask the user a relevant follow-up question or present the information."
            logger.info(
                "Planner providing only tool results as no specific suggestion was generated."
            )

        output_state["planner_output"] = final_planner_output
        return output_state
