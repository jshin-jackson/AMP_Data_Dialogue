"""
agent.py
--------
Initialises the LLM and LangChain SQL agent, both cached with
@st.cache_resource so they are created once per Streamlit server
process and reused across all reruns and user sessions.

Conversation history is managed with InMemoryChatMessageHistory
(the modern LangChain replacement for the deprecated ConversationBufferMemory).
"""

import ast
import logging
import re

import httpx
import streamlit as st
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.callbacks.base import BaseCallbackHandler
from langchain_openai import ChatOpenAI

from src.config import SETTINGS
from src.database import get_db
from src.chart import render_chart_from_log

logger = logging.getLogger(__name__)

# In-process session store: session_id → ChatMessageHistory
_session_store: dict[str, ChatMessageHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in _session_store:
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]


def reset_session_history(session_id: str = "default") -> None:
    _session_store.pop(session_id, None)
    logger.info(f"Conversation history reset for session '{session_id}'.")


class SQLQueryCallbackHandler(BaseCallbackHandler):
    """Captures the SQL query and raw result produced by the SQL agent tools."""

    def __init__(self):
        self.sql_queries: list[str] = []
        self.tool_outputs: list = []

    def on_tool_start(self, tool_name: str, tool_input: dict, **kwargs) -> None:
        try:
            if isinstance(tool_name, dict) and "name" in tool_name:
                tool_name = tool_name["name"]  # type: ignore

            logger.info(f"Tool triggered: {tool_name}")

            if tool_name in ["sql_db", "sql_db_query"]:
                if isinstance(tool_input, str):
                    try:
                        tool_input = ast.literal_eval(tool_input)
                    except Exception:
                        logger.warning("Could not parse tool_input string as dict.")
                        return

                query = tool_input.get("query") if isinstance(tool_input, dict) else None
                if query:
                    self.sql_queries.append(query)
                    logger.info(f"Captured SQL: {query}")

        except Exception as e:
            logger.error(f"on_tool_start error: {e}")

    def on_tool_end(self, output, **kwargs) -> None:
        self.tool_outputs.append(output)

    def on_agent_action(self, action, **kwargs) -> None:
        try:
            if hasattr(action, "tool") and action.tool in ["sql_db", "sql_db_query"]:
                query = action.tool_input.get("query")
                if query:
                    self.sql_queries.append(query)
                    logger.info(f"Captured SQL (agent action): {query}")
        except Exception as e:
            logger.error(f"on_agent_action error: {e}")


def _build_llm() -> ChatOpenAI:
    base_url = SETTINGS["OPENAI_BASE_URL"]
    if base_url:
        return ChatOpenAI(
            model=SETTINGS["OPENAI_MODEL_NAME"],
            base_url=base_url,
            api_key=SETTINGS["OPENAI_API_KEY"],
            http_client=httpx.Client(verify=False),
            temperature=0,
        )
    return ChatOpenAI(
        model=SETTINGS["OPENAI_MODEL_NAME"],
        api_key=SETTINGS["OPENAI_API_KEY"],
        temperature=0,
    )


@st.cache_resource(show_spinner="Initializing AI agent...")
def _get_agent_and_llm():
    """
    Build and cache the LLM and SQL agent executor.
    Returns (agent_executor, llm) or (None, None) on failure.
    """
    db = get_db()
    if db is None:
        return None, None

    try:
        llm = _build_llm()
        agent_executor = create_sql_agent(
            llm,
            db=db,
            agent_type="openai-tools",
            verbose=True,
        )
        for tool in agent_executor.tools:
            logger.info(f"Agent tool available: {tool.name}")
        logger.info("LangChain SQL Agent initialized successfully.")
        return agent_executor, llm
    except Exception as e:
        logger.error(f"Agent initialization failed: {e}")
        return None, None


def _clean_response(response) -> str:
    if isinstance(response, dict) and "output" in response:
        text = response["output"].strip()
    else:
        text = str(response).strip()
    return re.sub(r"^output:?\s*", "", text, flags=re.IGNORECASE)


def execute_sql_query(
    user_query: str,
    session_id: str = "default",
    column_names: list | None = None,
) -> dict:
    """
    Run the user query through the SQL agent and return a result dict with
    keys: 'query' (SQL), 'result' (text), 'chart' (HTML or None).
    Returns {'error': ...} on failure.
    """
    agent_executor, llm = _get_agent_and_llm()

    if agent_executor is None:
        return {"error": "SQL Agent is not initialized. Check database connection and API key."}

    callback = SQLQueryCallbackHandler()

    try:
        logger.info(f"User query: {user_query}")

        history = get_session_history(session_id)
        history_text = "\n".join(
            f"{m.type.capitalize()}: {m.content}" for m in history.messages
        )
        full_query = f"{history_text}\nHuman: {user_query}" if history_text else user_query

        raw_response = agent_executor.invoke(
            full_query,
            config={"callbacks": [callback]},
        )

        history.add_user_message(user_query)
        history.add_ai_message(_clean_response(raw_response))

        sql_query = (
            callback.sql_queries[-1]
            if callback.sql_queries
            else "SQL query could not be extracted."
        )
        raw_sql_result = (
            callback.tool_outputs[-1]
            if callback.tool_outputs
            else "No SQL tool output captured."
        )

        if column_names and isinstance(raw_sql_result, list):
            data = [dict(zip(column_names, row)) for row in raw_sql_result]
        else:
            data = raw_sql_result

        log_data = {
            "conversation": history_text,
            "user_query": user_query,
            "sql_query": sql_query,
            "data": data,
        }

        chart_html = None
        try:
            chart_html = render_chart_from_log(log_data, llm)
            logger.info("Chart generated successfully.")
        except Exception as chart_err:
            logger.warning(f"Chart generation failed (non-fatal): {chart_err}")

        return {
            "query": sql_query,
            "result": _clean_response(raw_response),
            "chart": chart_html,
        }

    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return {"error": f"Error: {str(e)}"}
