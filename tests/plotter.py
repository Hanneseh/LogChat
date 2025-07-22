import json
import os
import sys
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from adjustText import adjust_text

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.database.logchat_db import LogChatDB

eval_data_path = "/tests/data/eval_dataset.json"
eval_data = json.load(open(os.getcwd() + eval_data_path))
logchat_db = LogChatDB()


def generate_plots():
    for user_id, _ in eval_data.items():
        USER_ID = int(user_id)
        user = logchat_db.get_user(USER_ID)
        user_name = user.name

        # Retrieve all logs for the user
        logs = logchat_db.get_activity_and_symptom_logs_by_user(USER_ID)
        # Build DataFrame
        data = []
        for log in logs:
            if log.occurred_at:
                date = (
                    log.occurred_at.date()
                    if hasattr(log.occurred_at, "date")
                    else datetime.strptime(str(log.occurred_at)[:10], "%Y-%m-%d").date()
                )
            else:
                date = (
                    log.timestamp.date()
                    if hasattr(log.timestamp, "date")
                    else datetime.strptime(str(log.timestamp)[:10], "%Y-%m-%d").date()
                )
            data.append(
                {
                    "date": date,
                    "log_type": log.log_type.value,
                    "intensity": log.intensity,
                    "duration": log.duration,
                    "name": log.name,
                    "description": log.description,
                }
            )
        df = pd.DataFrame(data)
        if df.empty:
            continue

        # Activity score: duration * intensity, summed per day
        activity_df = df[df["log_type"] == "activity"].copy()
        activity_df["action_score"] = activity_df["duration"] * activity_df["intensity"]
        daily_activity = activity_df.groupby("date")["action_score"].sum()
        if not daily_activity.empty:
            daily_activity = daily_activity / daily_activity.max()

        # Symptom score: duration * intensity, summed per day
        symptom_df = df[df["log_type"] == "symptom"].copy()
        symptom_df["symptom_score"] = symptom_df["duration"] * symptom_df["intensity"]
        daily_symptom = symptom_df.groupby("date")["symptom_score"].sum()
        if not daily_symptom.empty:
            daily_symptom = daily_symptom / daily_symptom.max()

        # Combined trend and scatter plot
        plt.figure(figsize=(12, 6), dpi=200)
        # Plot activity and symptom trends
        if not daily_activity.empty:
            plt.plot(
                daily_activity.index,
                daily_activity.values,
                "-o",
                label="Activity Score (normalized)",
                color="tab:blue",
            )
        if not daily_symptom.empty:
            plt.plot(
                daily_symptom.index,
                daily_symptom.values,
                "-o",
                label="Symptom Score (normalized)",
                color="tab:red",
            )
        # Overlay symptom scatter
        if not symptom_df.empty:
            max_symptom_score = symptom_df["symptom_score"].max()
            scatter = plt.scatter(
                symptom_df["date"],
                symptom_df["symptom_score"] / max_symptom_score
                if max_symptom_score
                else 0,
                s=symptom_df["duration"],
                c=symptom_df["intensity"],
                cmap="viridis",
                alpha=0.7,
                edgecolors="w",
                label="Symptom Events",
                zorder=3,
            )
            # Add symptom names as text labels with adjustText
            texts = []
            for i, row in symptom_df.iterrows():
                texts.append(
                    plt.text(
                        row["date"],
                        row["symptom_score"] / max_symptom_score
                        if max_symptom_score
                        else 0,
                        str(row["name"]),
                        fontsize=8,
                        ha="center",
                        va="bottom",
                        alpha=0.8,
                    )
                )
            adjust_text(
                texts, only_move={"points": "xy", "text": "xy", "objects": "xy"}
            )

            cbar = plt.colorbar(scatter, label="Symptom Intensity (1-10)")
        plt.xlabel("Date")
        plt.ylabel("Normalized Score")

        # Format x-axis dates for better readability
        plt.gcf().autofmt_xdate()

        plt.title(f"{user_name}: Activity & Symptom Trend with Symptom Events")
        # Adjust legend to reduce dot size further
        plt.legend(
            scatterpoints=1, markerscale=0.5, handletextpad=0.5
        )  # Smaller legend dot size
        plt.tight_layout()
        plot_path = os.path.join("logs", f"{user_name}_activity_symptom_combined.png")
        plt.savefig(plot_path, dpi=200)
        plt.close()


if __name__ == "__main__":
    generate_plots()
