import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src import LogChat
from src.database.logchat_db import LogChatDB
from tests.judge import judge
from tests.plotter import generate_plots
from tests.simulator import Simulator

eval_data_path = "/tests/data/eval_dataset.json"
eval_data = json.load(open(os.getcwd() + eval_data_path))
logchat_db = LogChatDB()

for user_id, user_dataset in eval_data.items():
    USER_ID = int(user_id)

    logchat_db.clear_data_for_user(USER_ID)

    persona_description = user_dataset["description"]
    interaction_style = user_dataset["interaction_style"]
    interactions = user_dataset["interactions"]

    for sim_time, values in interactions.items():
        print(f"Running simulation for user {USER_ID} at sim_time {sim_time}")
        daily_report = values["daily_report"]

        logchat = LogChat(user_id=USER_ID, sim_time=sim_time)
        thread_summaries = logchat.thread_summaries

        simulator = Simulator(
            persona=persona_description,
            interaction_style=interaction_style,
            daily_report=daily_report,
            sim_time=sim_time,
            thread_summaries=thread_summaries,
        )
        logchat_opener = logchat.get_opener()
        simulator_output = simulator.run(logchat_opener)

        while simulator_output != "END_CONVERSATION":
            logchat_output = logchat.run(f"{simulator_output}")
            simulator_output = simulator.run(f"{logchat_output}")

        logchat.post_interaction_routine()

judge()
generate_plots()
