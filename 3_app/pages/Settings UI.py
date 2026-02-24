"""
pages/settings_ui.py
--------------------
Streamlit UI page that reads/writes your config settings.
"""

import streamlit as st
import os
from src.Settings import SETTINGS  # Import the pure config

# Must be the FIRST Streamlit call if you want a separate page config here:
st.set_page_config(
    page_title="Settings",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Optional: If you want to keep the original styling and banner
st.markdown(
    """
    <style>
    /* Hide default header and sidebar toggler */
    header[data-testid="stHeader"] {
        display: none;
    }
    .css-h5rgaw.egzxvld2 {
        display: none !important;
    }
    /* Fixed Orange Banner at Top */
    .title-bar {
        background-color: #F7931E;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        z-index: 9999;
        padding: 1rem;
        text-align: center;
    }
    .title-bar h1 {
        color: white;
        margin: 0;
        font-size: 1.5rem;
        font-weight: 600;
    }
    [data-testid="stAppViewContainer"] {
        margin-top: 100px;
        max-width: 1350px;
        margin-left: auto;
        margin-right: auto;
        background-color: #FFFFFF;
        padding: 1rem;
        margin-bottom: 10px;
    }
    /* Floating Gear Icon */
    .floating-gear {
        position: fixed;
        bottom: 20px;
        left: 20px;
        width: 60px;
        height: 60px;
        background-color: #F7931E;
        border-radius: 50%;
        text-align: center;
        z-index: 9999;
        cursor: pointer;
    }
    .floating-gear img {
        width: 32px;
        height: 32px;
        margin-top: 14px;
    }
    .floating-gear:hover {
        background-color: #d97a17;
    }
    </style>

    <!-- Fixed Orange Banner -->
    <div class="title-bar">
        <h1>Cloudera Database Assistant</h1>
    </div>

    <!-- Floating Gear Icon -->
    <div class="floating-gear" onclick="toggleSidebar()">
        <img src="https://img.icons8.com/ios-filled/50/ffffff/settings.png" />
    </div>

    <script>
    function toggleSidebar() {
      let arrowButton = document.querySelector('button[title="Main menu"]');
      if (!arrowButton) {
          arrowButton = document.querySelector('div[data-testid="collapsedControl"] button');
      }
      if (arrowButton) {
          arrowButton.click();
      } else {
          console.log("Sidebar toggle button not found.");
      }
    }
    </script>
    """,
    unsafe_allow_html=True,
)

st.title("Settings")

# -----------------------------
# Database Settings Section
# -----------------------------
st.header("💾 Database Settings")

# The values from settings.py
IS_REMOTE_DB = SETTINGS["IS_REMOTE_DB"]
LOCAL_DB_URI = (
    SETTINGS["DATABASE_URI"]
    or "postgresql://postgres:postgres@localhost:5432/financial_advisor"
)

# For example, if you want to *start* the radio with the current choice
db_connection_type = st.radio(
    "Select Database Connection Type:",
    ["Local", "Remote"],
    index=1 if IS_REMOTE_DB else 0,
)

# Then let the user modify them in real-time:
if db_connection_type == "Local":
    st.write("Using local DB connection")
    new_db_uri = st.text_input("Database URI", value=LOCAL_DB_URI)
else:
    st.write("Using remote DB connection")
    new_ssh_host = st.text_input("SSH Host", value=SETTINGS["SSH_HOST"] or "")
    # etc. for other remote fields

st.markdown("---")  # Horizontal line separator

# -----------------------------
# Model Settings Section
# -----------------------------
st.header("🤖 Model Settings")
MODEL_NAME = st.selectbox(
    "Select Model",
    options=["gpt-3.5", "gpt-4", "custom-model"],
    index=(
        ["gpt-3.5", "gpt-4", "custom-model"].index(SETTINGS["MODEL_NAME"])
        if SETTINGS["MODEL_NAME"] in ["gpt-3.5", "gpt-4", "custom-model"]
        else 1
    ),
)

col1, col2 = st.columns(2)
with col1:
    TEMPERATURE = st.number_input(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=SETTINGS["TEMPERATURE"],
        step=0.1,
    )
with col2:
    TOP_P = st.number_input(
        "Top P", min_value=0.0, max_value=1.0, value=SETTINGS["TOP_P"], step=0.1
    )

st.markdown("---")

if st.button("Save Settings"):
    st.success("Settings updated!")
    # Optionally, update st.session_state or write back to .env, etc.
    # For example:
    st.session_state["IS_REMOTE_DB"] = db_connection_type == "Remote"
    st.session_state["MODEL_NAME"] = MODEL_NAME
    st.session_state["TEMPERATURE"] = TEMPERATURE
    st.session_state["TOP_P"] = TOP_P
