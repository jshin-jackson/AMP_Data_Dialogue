"""
config.py
---------
Pure config module: loads environment variables and exposes a SETTINGS dict.
No Streamlit calls here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

IS_REMOTE_DB = os.getenv("IS_REMOTE_DB", "false").lower().strip() == "true"
DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///sample_sqlite.db")
SSH_HOST = os.getenv("SSH_HOST", "")
SSH_USERNAME = os.getenv("SSH_USERNAME", "")
SSH_PORT = int(os.getenv("SSH_PORT", "22"))
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "")

DB_HOST = os.getenv("DB_HOST", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
TOP_P = float(os.getenv("TOP_P", "0.9"))

SETTINGS: dict = {
    "IS_REMOTE_DB": IS_REMOTE_DB,
    "DATABASE_URI": DATABASE_URI if not IS_REMOTE_DB else None,
    "SSH_HOST": SSH_HOST if IS_REMOTE_DB else None,
    "SSH_USERNAME": SSH_USERNAME if IS_REMOTE_DB else None,
    "SSH_PORT": SSH_PORT if IS_REMOTE_DB else None,
    "SSH_PASSWORD": SSH_PASSWORD if IS_REMOTE_DB else None,
    "DB_HOST": DB_HOST if IS_REMOTE_DB else None,
    "DB_NAME": DB_NAME if IS_REMOTE_DB else None,
    "DB_PORT": DB_PORT if IS_REMOTE_DB else None,
    "DB_USER": DB_USER if IS_REMOTE_DB else None,
    "DB_PASSWORD": DB_PASSWORD if IS_REMOTE_DB else None,
    "OPENAI_BASE_URL": OPENAI_BASE_URL,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "OPENAI_MODEL_NAME": OPENAI_MODEL_NAME,
    "MODEL_NAME": MODEL_NAME,
    "TEMPERATURE": TEMPERATURE,
    "TOP_P": TOP_P,
}
