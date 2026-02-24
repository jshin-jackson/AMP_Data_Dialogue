import os
import logging
import re
import ast
import atexit

import httpx
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder

from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.callbacks.base import BaseCallbackHandler
from langchain.memory import ConversationBufferMemory

from src.vegalite_chart_module import render_chart_from_log
from src.Settings import SETTINGS

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    filename="server.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

openai_base_url = os.getenv("OPENAI_BASE_URL")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_model_name = os.getenv("OPENAI_MODEL_NAME")

_ssh_tunnel: SSHTunnelForwarder | None = None


def _close_ssh_tunnel():
    """Cleanly shut down the SSH tunnel on process exit."""
    global _ssh_tunnel
    if _ssh_tunnel and _ssh_tunnel.is_active:
        _ssh_tunnel.stop()
        logger.info("SSH tunnel closed.")


atexit.register(_close_ssh_tunnel)


def get_database_uri() -> str:
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


try:
    db = SQLDatabase.from_uri(get_database_uri(), engine_args={"echo": True})
    logger.info("Connected to database successfully.")
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    db = None


def _build_llm() -> ChatOpenAI:
    if openai_base_url:
        return ChatOpenAI(
            model=openai_model_name,
            base_url=openai_base_url,
            api_key=openai_api_key,
            http_client=httpx.Client(verify=False),
            temperature=0,
        )
    return ChatOpenAI(
        model=openai_model_name,
        api_key=openai_api_key,
        temperature=0,
    )


class SQLQueryCallbackHandler(BaseCallbackHandler):
    """Captures SQL queries executed by LangChain SQL Agent."""

    def __init__(self):
        self.sql_queries = []
        self.tool_outputs = []

    def on_tool_start(self, tool_name: str, tool_input: dict, **kwargs) -> None:
        try:
            if isinstance(tool_name, dict) and "name" in tool_name:
                tool_name = tool_name["name"]  # type: ignore

            logger.info(f"Tool Triggered: {tool_name}, Input Type: {type(tool_input)}")

            if tool_name in ["sql_db", "sql_db_query"]:
                if isinstance(tool_input, str):
                    try:
                        tool_input = ast.literal_eval(tool_input)
                    except Exception as e:
                        logger.error(f"Failed to convert tool_input to dict: {e}")
                        return

                query = tool_input.get("query")
                if query:
                    self.sql_queries.append(query)
                    logger.info(f"Captured SQL Query: {query}")

        except Exception as e:
            logger.error(f"Exception in on_tool_start: {e}")

    def on_tool_end(self, output, **kwargs) -> None:
        self.tool_outputs.append(output)
        logger.info(f"Tool finished with output: {output}")

    def on_agent_action(self, action, **kwargs):
        try:
            logger.info(f"Agent Action Triggered: {action}")
            if hasattr(action, "tool") and action.tool in ["sql_db", "sql_db_query"]:
                query = action.tool_input.get("query", None)
                if query:
                    self.sql_queries.append(query)
                    logger.info(f"Captured SQL Query in on_agent_action: {query}")
        except Exception as e:
            logger.error(f"Exception in on_agent_action: {e}")


def _attach_callbacks_to_tools(agent_exec, callback_handler):
    for tool in agent_exec.tools:
        tool.callbacks = [callback_handler]
        logger.info(f"Callback attached to tool: {tool.name}")


sql_callback_handler = SQLQueryCallbackHandler()
llm = None
agent_executor = None
memory = None

if db:
    try:
        llm = _build_llm()
        memory = ConversationBufferMemory(memory_key="history", return_messages=True)

        suffix = """Begin!

            Relevant pieces of previous conversation:
            {history}
            (You do not need to use these pieces of information if not relevant)"""

        agent_executor = create_sql_agent(
            llm,
            db=db,
            memory=memory,
            agent_type="openai-tools",
            verbose=True,
            suffix=suffix,
            agent_executor_kwargs={"memory": memory},
            callbacks=[sql_callback_handler],
        )
        _attach_callbacks_to_tools(agent_executor, sql_callback_handler)
        logger.info("LangChain SQL Agent initialized successfully.")
    except Exception as e:
        logger.error(f"LangChain agent initialization failed: {e}")


def reset_conversation_memory():
    global memory
    if memory is not None:
        memory = ConversationBufferMemory(memory_key="history", return_messages=True)
        logger.info("Conversation memory has been reset.")


def clean_response(response) -> str:
    if isinstance(response, dict) and "output" in response:
        output_text = response["output"].strip()
    else:
        output_text = str(response).strip()
    return re.sub(r"^output:?\s*", "", output_text, flags=re.IGNORECASE)


def execute_sql_query(user_query: str, column_names: list = None) -> dict:  # type: ignore
    if agent_executor is None:
        return {"error": "SQL Agent is not initialized."}

    try:
        logger.info(f"User Query: {user_query}")
        conversation = memory.load_memory_variables({})["history"]
        full_query = f"{conversation}\nHuman: {user_query}"
        logger.info(f"Full Query: {full_query}")

        sql_callback_handler.sql_queries = []
        sql_callback_handler.tool_outputs = []

        raw_response = agent_executor.invoke(full_query)  # type: ignore

        sql_query = (
            sql_callback_handler.sql_queries[-1]
            if sql_callback_handler.sql_queries
            else "SQL Query extraction failed."
        )
        raw_sql_result = (
            sql_callback_handler.tool_outputs[-1]
            if sql_callback_handler.tool_outputs
            else "No SQL tool output captured."
        )

        logger.info(f"Extracted SQL Query: {sql_query}")
        logger.info(f"Raw SQL result: {raw_sql_result}")

        if column_names and isinstance(raw_sql_result, list):
            data = [dict(zip(column_names, row)) for row in raw_sql_result]
        else:
            data = raw_sql_result

        log_data = {
            "conversation": conversation,
            "user_query": user_query,
            "sql_query": sql_query,
            "data": data,
        }
        logger.info(f"Collected Data: {log_data}")

        # Chart failure is isolated — text response is still returned on error
        chart_html = None
        try:
            chart_html = render_chart_from_log(log_data, llm)
            logger.info("Chart HTML generated successfully.")
        except Exception as chart_err:
            logger.warning(f"Chart generation failed (non-fatal): {chart_err}")

        return {
            "query": sql_query,
            "result": clean_response(raw_response),
            "chart": chart_html,
        }

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return {"error": f"Error: {str(e)}"}
