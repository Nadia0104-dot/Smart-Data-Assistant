import json
import os
from datetime import datetime

USERS_FILE = "backend/users.json"


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}

    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def update_last_login(username):
    users = load_users()
    if username in users:
        users[username]["last_login"] = datetime.utcnow().isoformat()
        save_users(users)


def create_user(username, password_hash, email):
    users = load_users()

    users[username] = {
        "password": password_hash,
        "email": email,
        "account_type": "basic",
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None
    }

    save_users(users)


def get_user(username):
    users = load_users()
    return users.get(username)