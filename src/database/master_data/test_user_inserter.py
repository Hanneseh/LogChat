import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root))

from src.database.logchat_db import LogChatDB  # noqa: E402
from src.database.models.user_data.logchat_user import LogChatUser  # noqa: E402

# Initialize DB
logchat_db = LogChatDB()

# User data to insert
users = [
    {"id": 1, "name": "Mark"},
    {"id": 2, "name": "Sarah"},
    {"id": 3, "name": "Elena"},
    {"id": 4, "name": "Charlie"},
]

with logchat_db.get_session() as session:
    # Delete users with IDs 1, 2, 3 if they exist
    session.query(LogChatUser).filter(LogChatUser.id.in_([1, 2, 3])).delete(
        synchronize_session=False
    )
    # Insert new users
    for user in users:
        session.add(LogChatUser(id=user["id"], name=user["name"]))
    session.commit()

print("Inserted test users: Mark, Sarah, Elena (IDs 1, 2, 3)")
