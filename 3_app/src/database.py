"""
database.py
-----------
Handles database connection with SSH tunnel support.
Uses @st.cache_resource so the connection is created once per Streamlit
server process and reused across all reruns and sessions.
"""

import atexit
import logging

import streamlit as st
from sshtunnel import SSHTunnelForwarder
from langchain_community.utilities import SQLDatabase

from src.config import SETTINGS

logger = logging.getLogger(__name__)

_ssh_tunnel: SSHTunnelForwarder | None = None


def _close_ssh_tunnel() -> None:
    """Cleanly shut down the SSH tunnel on process exit."""
    global _ssh_tunnel
    if _ssh_tunnel and _ssh_tunnel.is_active:
        _ssh_tunnel.stop()
        logger.info("SSH tunnel closed.")


atexit.register(_close_ssh_tunnel)


def _get_database_uri() -> str:
    """Resolve the database URI, opening an SSH tunnel when required."""
    global _ssh_tunnel

    if SETTINGS["IS_REMOTE_DB"]:
        logger.info("Remote DB: TRUE — opening SSH tunnel")
        _ssh_tunnel = SSHTunnelForwarder(
            (SETTINGS["SSH_HOST"], int(SETTINGS["SSH_PORT"])),
            ssh_username=SETTINGS["SSH_USERNAME"],
            ssh_password=SETTINGS["SSH_PASSWORD"],
            remote_bind_address=(
                SETTINGS["DB_HOST"],
                int(SETTINGS["DB_PORT"]),
            ),
        )
        _ssh_tunnel.start()
        return (
            f"postgresql://{SETTINGS['DB_USER']}:{SETTINGS['DB_PASSWORD']}"
            f"@127.0.0.1:{_ssh_tunnel.local_bind_port}/{SETTINGS['DB_NAME']}"
        )

    return SETTINGS["DATABASE_URI"]


@st.cache_resource(show_spinner="Connecting to database...")
def get_db() -> SQLDatabase | None:
    """
    Return a cached SQLDatabase instance.
    Created once on first call; reused for all subsequent Streamlit reruns.
    """
    try:
        uri = _get_database_uri()
        db = SQLDatabase.from_uri(uri, engine_args={"echo": False})
        logger.info("Connected to database successfully.")
        return db
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None
