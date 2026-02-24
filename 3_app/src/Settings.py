"""
settings.py
-----------
Pure config file: No Streamlit UI calls here.
Loads defaults from .env and stores them in a SETTINGS dict.
"""

import os
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

# ✅ Prepare config defaults
IS_REMOTE_DB = os.getenv("IS_REMOTE_DB", "false").lower().strip() == "true"
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/financial_advisor"
)
SSH_HOST = os.getenv("SSH_HOST", "")
SSH_USERNAME = os.getenv("SSH_USERNAME", "")
SSH_PORT = int(os.getenv("SSH_PORT", 22))
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "")

DB_HOST = os.getenv("DB_HOST", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))
TOP_P = float(os.getenv("TOP_P", 0.9))

# ✅ Store everything in a dictionary
SETTINGS = {
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
    "MODEL_NAME": MODEL_NAME,
    "TEMPERATURE": TEMPERATURE,
    "TOP_P": TOP_P,
}

# Note: No Streamlit calls at the top level. Just config.
