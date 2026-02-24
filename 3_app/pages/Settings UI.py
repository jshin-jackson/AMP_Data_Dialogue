"""
pages/Settings UI.py
--------------------
Streamlit settings page. Writes changes back to the .env file so that
values are persisted across sessions and picked up by models.py on restart.
"""

import os
import streamlit as st
from dotenv import set_key, dotenv_values

from src.config import SETTINGS

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "src", ".env")

AVAILABLE_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
    "custom-model",
]

st.set_page_config(
    page_title="Settings",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { display: none; }
    .css-h5rgaw.egzxvld2 { display: none !important; }
    .title-bar {
        background-color: #F7931E;
        position: fixed; top: 0; left: 0;
        width: 100%; z-index: 9999;
        padding: 1rem; text-align: center;
    }
    .title-bar h1 { color: white; margin: 0; font-size: 1.5rem; font-weight: 600; }
    [data-testid="stAppViewContainer"] {
        margin-top: 100px; max-width: 1350px;
        margin-left: auto; margin-right: auto;
        background-color: #FFFFFF; padding: 1rem; margin-bottom: 10px;
    }
    .floating-gear {
        position: fixed; bottom: 20px; left: 20px;
        width: 60px; height: 60px;
        background-color: #F7931E; border-radius: 50%;
        text-align: center; z-index: 9999; cursor: pointer;
    }
    .floating-gear img { width: 32px; height: 32px; margin-top: 14px; }
    .floating-gear:hover { background-color: #d97a17; }
    </style>

    <div class="title-bar"><h1>Cloudera Database Assistant</h1></div>

    <div class="floating-gear" onclick="toggleSidebar()">
        <img src="https://img.icons8.com/ios-filled/50/ffffff/settings.png" />
    </div>

    <script>
    function toggleSidebar() {
      let btn = document.querySelector('button[title="Main menu"]');
      if (!btn) btn = document.querySelector('div[data-testid="collapsedControl"] button');
      if (btn) btn.click();
    }
    </script>
    """,
    unsafe_allow_html=True,
)

st.title("Settings")
st.info("Changes are saved to `.env` and take effect after the app restarts.", icon="ℹ️")

# ---------------------------------------------------------------------------
# Database Settings
# ---------------------------------------------------------------------------
st.header("Database Settings")

IS_REMOTE_DB = SETTINGS["IS_REMOTE_DB"]
LOCAL_DB_URI = (
    SETTINGS["DATABASE_URI"]
    or "sqlite:///sample_sqlite.db"
)

db_connection_type = st.radio(
    "Select Database Connection Type:",
    ["Local", "Remote"],
    index=1 if IS_REMOTE_DB else 0,
)

if db_connection_type == "Local":
    st.write("Using local DB connection")
    new_db_uri = st.text_input("Database URI", value=LOCAL_DB_URI)
else:
    st.write("Using remote DB connection via SSH tunnel")
    col1, col2 = st.columns(2)
    with col1:
        new_ssh_host = st.text_input("SSH Host", value=os.getenv("SSH_HOST", ""))
        new_ssh_username = st.text_input("SSH Username", value=os.getenv("SSH_USERNAME", ""))
        new_ssh_password = st.text_input("SSH Password", value=os.getenv("SSH_PASSWORD", ""), type="password")
        new_ssh_port = st.number_input("SSH Port", value=int(os.getenv("SSH_PORT", 22)), min_value=1, max_value=65535)
    with col2:
        new_db_host = st.text_input("DB Host", value=os.getenv("DB_HOST", ""))
        new_db_port = st.number_input("DB Port", value=int(os.getenv("DB_PORT", 5432)), min_value=1, max_value=65535)
        new_db_name = st.text_input("DB Name", value=os.getenv("DB_NAME", ""))
        new_db_user = st.text_input("DB User", value=os.getenv("DB_USER", ""))
        new_db_password = st.text_input("DB Password", value=os.getenv("DB_PASSWORD", ""), type="password")

st.markdown("---")

# ---------------------------------------------------------------------------
# Model Settings
# ---------------------------------------------------------------------------
st.header("Model Settings")

current_model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
model_index = AVAILABLE_MODELS.index(current_model) if current_model in AVAILABLE_MODELS else 0

MODEL_NAME = st.selectbox("Select Model", options=AVAILABLE_MODELS, index=model_index)

col1, col2 = st.columns(2)
with col1:
    TEMPERATURE = st.number_input(
        "Temperature", min_value=0.0, max_value=2.0,
        value=SETTINGS["TEMPERATURE"], step=0.1,
    )
with col2:
    TOP_P = st.number_input(
        "Top P", min_value=0.0, max_value=1.0,
        value=SETTINGS["TOP_P"], step=0.1,
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
if st.button("Save Settings", type="primary"):
    try:
        is_remote = db_connection_type == "Remote"
        set_key(ENV_PATH, "IS_REMOTE_DB", str(is_remote).lower())

        if is_remote:
            set_key(ENV_PATH, "SSH_HOST", new_ssh_host)
            set_key(ENV_PATH, "SSH_PORT", str(int(new_ssh_port)))
            set_key(ENV_PATH, "SSH_USERNAME", new_ssh_username)
            set_key(ENV_PATH, "SSH_PASSWORD", new_ssh_password)
            set_key(ENV_PATH, "DB_HOST", new_db_host)
            set_key(ENV_PATH, "DB_PORT", str(int(new_db_port)))
            set_key(ENV_PATH, "DB_NAME", new_db_name)
            set_key(ENV_PATH, "DB_USER", new_db_user)
            set_key(ENV_PATH, "DB_PASSWORD", new_db_password)
        else:
            set_key(ENV_PATH, "DATABASE_URI", new_db_uri)

        set_key(ENV_PATH, "OPENAI_MODEL_NAME", MODEL_NAME)
        set_key(ENV_PATH, "TEMPERATURE", str(TEMPERATURE))
        set_key(ENV_PATH, "TOP_P", str(TOP_P))

        st.success("Settings saved to .env. Please restart the app for changes to take effect.")
    except Exception as e:
        st.error(f"Failed to save settings: {e}")
