import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src import LogChat
from src.database.logchat_db import LogChatDB
from tests.simulator import Simulator

eval_data_path = "/tests/data/eval_dataset.json"
eval_data = json.load(open(os.getcwd() + eval_data_path))
logchat_db = LogChatDB()

for user_id, user_dataset in eval_data.items():
    USER_ID = int(user_id)

    logchat_db.clear_data_for_user(USER_ID)

    persona_description = user_dataset["description"]
    interactions = user_dataset["interactions"]

    for sim_time, values in interactions.items():
        daily_report = values["daily_report"]

        logchat = LogChat(user_id=USER_ID, state_saver="memory", sim_time=sim_time)
        user_name = logchat.get_user_name()

        simulator = Simulator(
            persona=persona_description, daily_report=daily_report, sim_time=sim_time
        )
        simulator_output = simulator.run(f"Hi {user_name}! How are you")

        while simulator_output != "END_CONVERSATION":
            logchat_output = logchat.run(f"{simulator_output}")
            simulator_output = simulator.run(f"{logchat_output}")
