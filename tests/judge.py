import json
import os
import re
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from numpy import average

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from tests.prompts import judge_instructions, judge_system_prompt

load_dotenv()


def calculate_score(evaluation_checklist: list, model_output: str) -> tuple[str, float]:
    """
    Generate a performance score section based on the LLM's evaluation output,
    using separate regex for input and output items.

    Args:
        evaluation_checklist: The original list of dicts defining expected inputs/outputs.
        model_output: The string output from the LLM containing the evaluated checklist (with ✅/❌).

    Returns:
        A tuple containing:
        - The formatted score string.
        - The calculated score (float).
    """
    total_input_items = 0
    achieved_input_items = 0
    total_output_items = 0
    achievable_output_items = 0
    achieved_output_items = 0
    evaluated_statuses = {}

    # Input item: Optional space, digits, dot, space, anything, ends with ✅ or ❌
    input_item_regex = re.compile(r"^\s*(\d+)\.\s+.*?\s+(✅|❌)\s*$", re.MULTILINE)
    # Output item: Optional space, digits, dot, digits, space, anything, ends with ✅ or ❌
    output_item_regex = re.compile(r"^\s*(\d+\.\d+)\s+.*?\s+(✅|❌)\s*$", re.MULTILINE)

    # Find all input matches
    for match in input_item_regex.finditer(model_output):
        item_id = match.group(1)
        status_symbol = match.group(2)
        evaluated_statuses[item_id] = status_symbol == "✅"

    # Find all output matches
    for match in output_item_regex.finditer(model_output):
        item_id = match.group(1)
        status_symbol = match.group(2)
        evaluated_statuses[item_id] = status_symbol == "✅"

    # Iterate through the original checklist to calculate scores
    for i, item in enumerate(evaluation_checklist):
        input_item_id = str(i + 1)
        total_input_items += 1
        num_outputs_for_this_input = len(item["output"])
        total_output_items += num_outputs_for_this_input

        # Check status of the input item
        input_achieved = evaluated_statuses.get(input_item_id, False)
        if input_achieved:
            achieved_input_items += 1
            achievable_output_items += num_outputs_for_this_input

            # Check status of corresponding output items ONLY if input was achieved
            for j, _ in enumerate(item["output"]):
                output_item_id = f"{input_item_id}.{j + 1}"
                output_achieved = evaluated_statuses.get(output_item_id, False)
                if output_achieved:
                    achieved_output_items += 1

    # Handle division by zero
    if achievable_output_items > 0:
        score_val = achieved_output_items / achievable_output_items
    else:
        score_val = 0.0

    score_fraction_str = f"{achieved_output_items}/{achievable_output_items}"

    score_string = f"""Performance Score:
Nr. Of total input items: {total_input_items}
Nr. of achieved input items: {achieved_input_items}
Nr. of total output items: {total_output_items}
Nr. of achievable output items: {achievable_output_items}
Nr. of achieved output items: {achieved_output_items}
Score: {score_fraction_str} = {score_val:.4f}
"""
    return score_string, score_val


def judge(eval_data: dict, log_base_path: str, file_mapping: dict):
    prompt_template = ChatPromptTemplate(
        [
            (
                "system",
                judge_system_prompt,
            ),
            MessagesPlaceholder("messages"),
        ]
    )
    scores = []
    judgment_str = ""
    for user_id, user_dataset in eval_data.items():
        user_name = user_dataset["name"]
        interactions = user_dataset["interactions"]

        for sim_time, values in interactions.items():
            sim_time_str = sim_time.replace(" ", "_").replace(":", "-")
            evaluation_checklist = values["evaluation_checklist"]

            #  format the evaluation checklist
            evaluation_checklist_string = ""
            item_number = 1
            for item in evaluation_checklist:
                evaluation_checklist_string += f"{item_number}. {item['input']}\n"
                for j, output in enumerate(item["output"]):
                    evaluation_checklist_string += f"  {item_number}.{j + 1} {output}\n"
                item_number += 1

            # identify the log file
            log_file_sim_time = [
                file
                for file in log_files_sim_time
                if user_name in file and sim_time_str in file
            ][0]
            log_file = file_mapping[log_file_sim_time]

            log_file = log_base_path + "/" + log_file
            logs = open(log_file, "r").readlines()

            user_message = f"""{judge_instructions}\n\nEvaluation Checklist:\n{evaluation_checklist_string}\n\nConversation Log:\n{"".join(logs)}"""

            prompt = prompt_template.invoke(
                {
                    "messages": [HumanMessage(user_message)],
                }
            )
            # print(prompt.to_string())

            model_response = model.invoke(prompt)

            score_str, score_val = calculate_score(
                evaluation_checklist, model_response.content
            )

            final_output_content = score_str + "\n\n" + model_response.content.strip()
            scores.append(score_val)

            evaluation_log_file = log_file.replace("_with_tools.log", "_evaluation.log")
            with open(evaluation_log_file, "w") as f:
                f.write(final_output_content)

            judgment = f"User: {user_name}, Simulated Time: {sim_time_str}, Score: {score_val:.4f} ({score_str.split('Score: ')[1].strip()})"
            print(judgment)
            judgment_str += judgment + "\n"

    if scores:
        average_score = average(scores)
        final_verdict = f"\nAverage Score across all interactions: {average_score:.4f}"
    else:
        final_verdict = "\nNo scores were calculated."

    print(final_verdict)
    judgment_str += final_verdict
    judgment_log_file = os.path.join(log_base_path, "vertict.log")

    with open(judgment_log_file, "w") as f:
        f.write(judgment_str)
    print(f"Judgment summary saved to {judgment_log_file}")


# define the model
api_key = os.getenv("GOOGLE_API_KEY")
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-thinking-exp-01-21",
    temperature=0.0,
    api_key=api_key,
)

# Load the evaluation data
eval_data_path = "/tests/data/eval_dataset.json"
eval_data = json.load(open(os.getcwd() + eval_data_path))

# list all the log directories
log_dirs = os.listdir(os.getcwd() + "/logs")

# iterate through the log directories
for log_dir in log_dirs:
    LOG_PATH = os.path.join("/logs", log_dir)
    log_base_path = os.getcwd() + LOG_PATH
    if not os.path.isdir(log_base_path):
        continue

    # generate log file mapping
    log_files = os.listdir(log_base_path)
    log_files = [file for file in log_files if file.endswith("_with_tools.log")]
    log_files_sim_time = [
        file.replace(file[-len("00-00_with_tools.log") :], "00-00_with_tools.log")
        for file in log_files
    ]
    file_mapping = {log_files_sim_time[i]: file for i, file in enumerate(log_files)}

    judge(eval_data, log_base_path, file_mapping)
