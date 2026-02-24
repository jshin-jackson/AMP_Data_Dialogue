import os
import logging
import re
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.callbacks.base import BaseCallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
import json
import ast
from langchain.memory import ConversationBufferMemory
from src.vegalite_chart_module import render_chart_from_log
from src.Settings import SETTINGS
import httpx

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename="server.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


import os
from sshtunnel import SSHTunnelForwarder

import os
from sshtunnel import SSHTunnelForwarder


def get_database_uri():
    """
    Returns the DATABASE_URI.
    - If the database is remote (`IS_REMOTE_DB=true` in .env), it sets up an SSH tunnel and constructs the URI dynamically.
    - If the database is local, it simply fetches the `DATABASE_URI` from the environment.
    """
    # Check if the database is remote
    if os.getenv("IS_REMOTE_DB", "false").lower().strip() == "true":
        print("Remote DB :TRUE")
        # Load remote DB & SSH credentials
        SSH_HOST = os.getenv("SSH_HOST")
        SSH_PORT = int(os.getenv("SSH_PORT", 22))
        SSH_USERNAME = os.getenv("SSH_USERNAME")
        SSH_PASSWORD = os.getenv("SSH_PASSWORD")

        DB_HOST = os.getenv("DB_HOST")
        DB_PORT = int(os.getenv("DB_PORT", 5432))
        DB_NAME = os.getenv("DB_NAME")
        DB_USER = os.getenv("DB_USER")
        DB_PASSWORD = os.getenv("DB_PASSWORD")

        # Set up SSH tunnel
        tunnel = SSHTunnelForwarder(
            (SSH_HOST, SSH_PORT),
            ssh_username=SSH_USERNAME,
            ssh_password=SSH_PASSWORD,
            remote_bind_address=(DB_HOST, DB_PORT),
        )
        tunnel.start()

        # Construct DATABASE_URI dynamically
        return f"postgresql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{tunnel.local_bind_port}/{DB_NAME}"

    # If local, fetch directly from env or use default
    return os.getenv(
        "DATABASE_URI",
        "postgresql://postgres:postgres@localhost:5432/financial_advisor",
    )


def get_database_uri_settings():
    if SETTINGS["IS_REMOTE_DB"]:
        print("Remote DB: TRUE")
        tunnel = SSHTunnelForwarder(
            (SETTINGS["SSH_HOST"], int(SETTINGS["SSH_PORT"])),
            ssh_username=SETTINGS["SSH_USERNAME"],
            ssh_password=SETTINGS["SSH_PASSWORD"],
            remote_bind_address=(
                SETTINGS["DB_HOST"],
                int(SETTINGS["DB_PORT"]),
            ),
        )
        tunnel.start()

        return f"postgresql://{SETTINGS['DB_USER']}:{SETTINGS['DB_PASSWORD']}@127.0.0.1:{tunnel.local_bind_port}/{SETTINGS['DB_NAME']}"

    return SETTINGS["DATABASE_URI"]


# Assign DATABASE_URI based on environment
DATABASE_URI = get_database_uri_settings()


try:
    db = SQLDatabase.from_uri(DATABASE_URI, engine_args={"echo": True})
    logger.info("✅ Connected to database successfully!")
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")
    db = None  # Prevent agent from initializing

# Initialize OpenAI LLM and Agent
llm = None
agent_executor = None
openai_base_url = os.getenv("OPENAI_BASE_URL")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_model_name = os.getenv("OPENAI_MODEL_NAME")

import ast
import logging
from langchain.callbacks.base import BaseCallbackHandler

# Set up logging
logger = logging.getLogger(__name__)


class SQLQueryCallbackHandler(BaseCallbackHandler):
    """Captures SQL queries executed by LangChain SQL Agent."""

    def __init__(self):
        self.sql_queries = []
        self.tool_outputs = []  # List to store raw SQL outputs

    def on_tool_start(self, tool_name: str, tool_input: dict, **kwargs) -> None:
        """Intercept SQL queries before execution."""
        try:
            # Ensure tool_name is a dictionary with a "name" field
            if isinstance(tool_name, dict) and "name" in tool_name:
                tool_name = tool_name["name"]  # type: ignore

            logger.info(
                f"🔎 Tool Triggered: {tool_name}, Input Type: {type(tool_input)}"
            )

            # Only capture SQL-related tools
            if tool_name in ["sql_db", "sql_db_query"]:
                # Ensure tool_input is a dictionary
                if isinstance(tool_input, str):
                    try:
                        tool_input = ast.literal_eval(
                            tool_input
                        )  # Convert string to dictionary
                    except Exception as e:
                        logger.error(f"⚠️ Failed to convert tool_input to dict: {e}")
                        return  # Skip this capture if conversion fails

                # Extract query safely
                query = tool_input.get("query")
                if query:
                    self.sql_queries.append(query)
                    logger.info(f"✅ Captured SQL Query: {query}")

        except Exception as e:
            logger.error(f"🚨 Exception in `on_tool_start`: {e}")

    def on_tool_end(self, output, **kwargs) -> None:
        """Capture the output after the tool finishes execution."""
        self.tool_outputs.append(output)
        logger.info(f"🔚 Tool finished with output: {output}")

    def on_agent_action(self, action, **kwargs):
        """Fallback: Capture SQL queries if they appear at the agent level."""
        try:
            logger.info(f"📡 Agent Action Triggered: {action}")

            # Ensure action has a tool name and tool_input
            if hasattr(action, "tool") and action.tool in ["sql_db", "sql_db_query"]:
                query = action.tool_input.get("query", None)
                if query:
                    self.sql_queries.append(query)
                    logger.info(f"✅ Captured SQL Query in `on_agent_action`: {query}")

        except Exception as e:
            logger.error(f"🚨 Exception in `on_agent_action`: {e}")


# Attach the callback handler to all tools explicitly
def attach_callbacks_to_tools(agent_executor, callback_handler):
    """Manually attach callback handlers to all tools in the agent."""
    for tool in agent_executor.tools:
        tool.callbacks = [callback_handler]
        logger.info(f"✅ Callback attached to tool: {tool.name}")


# Initialize SQL query capture handler
sql_callback_handler = SQLQueryCallbackHandler()

if db:
    try:
        llm = ChatOpenAI(
                model=openai_model_name,
                base_url=openai_base_url,
                api_key=openai_api_key,
                http_client=httpx.Client(verify=False),
                temperature=0
              )

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
            callbacks=[
                sql_callback_handler
            ],  # Attach callback handler to capture SQL queries
        )
        # ✅ Force attach callbacks to all tools
        attach_callbacks_to_tools(agent_executor, sql_callback_handler)

        logger.info("✅ LangChain SQL Agent initialized successfully!")
    except Exception as e:
        logger.error(f"❌ LangChain agent initialization failed: {e}")


def reset_conversation_memory():
    """Resets the conversation memory."""
    global memory
    memory = ConversationBufferMemory(memory_key="history", return_messages=True)
    logger.info("🔄 Conversation memory has been reset.")


def clean_response(response):
    """Formats and extracts only the necessary output from the agent's response."""
    if isinstance(response, dict) and "output" in response:
        output_text = response["output"].strip()
    else:
        output_text = str(response).strip()

    # Remove unwanted patterns (like SQL Agent prefixes)
    output_text = re.sub(r"^output:?\s*", "", output_text, flags=re.IGNORECASE)

    return output_text


def execute_sql_query(user_query: str, column_names: list = None) -> dict:  # type: ignore
    """
    Executes the SQL query via the agent and returns the same response structure as before.
    In addition, logs additional details: conversation, user query, SQL query, and the raw data (converted to JSON-like structure if column_names is provided).
    """
    if agent_executor is None:
        return {"error": "⚠️ Error: SQL Agent is not initialized."}

    try:
        # Retrieve conversation history
        logger.info(f"🔍 User Query: {user_query}")
        conversation = memory.load_memory_variables({})["history"]
        full_query = f"{conversation}\nHuman: {user_query}"
        logger.info(f"📝 Full Query: {full_query}")

        # Reset captured SQL queries and tool outputs
        sql_callback_handler.sql_queries = []
        sql_callback_handler.tool_outputs = []

        # Invoke the agent with the full query
        raw_response = agent_executor.invoke(full_query)  # type: ignore

        # Extract the SQL query that was executed
        if sql_callback_handler.sql_queries:
            sql_query = sql_callback_handler.sql_queries[-1]
        else:
            sql_query = "⚠️ SQL Query extraction failed."

        # Retrieve the raw SQL output captured by on_tool_end
        if sql_callback_handler.tool_outputs:
            raw_sql_result = sql_callback_handler.tool_outputs[-1]
        else:
            raw_sql_result = "⚠️ No SQL tool output captured."

        logger.info(f"📌 Extracted SQL Query: {sql_query}")
        logger.info(f"📌 Raw SQL result: {raw_sql_result}")

        # Optionally convert raw_sql_result (list of tuples) into a JSON-like structure.
        if column_names and isinstance(raw_sql_result, list):
            data = [dict(zip(column_names, row)) for row in raw_sql_result]
        else:
            data = raw_sql_result

        # Log the additional data components without altering the returned response
        log_data = {
            "conversation": conversation,
            "user_query": user_query,
            "sql_query": sql_query,
            "data": data,
        }
        logger.info(f"Collected Data: {log_data}")

        if openai_base_url:
            llm = ChatOpenAI(
                    model=openai_model_name,
                    base_url=openai_base_url,
                    api_key=openai_api_key,
                    http_client=httpx.Client(verify=False),
                    temperature=0
                  )
        else:
            llm = ChatOpenAI(model=openai_model_name, temperature=0)

        chart_html = render_chart_from_log(log_data, llm)

        logger.info(f"📊 Chart HTML: \n \n  {chart_html}")
        if chart_html:
            print("Chart html received ")

        # Return the original response structure
        return {
            "query": sql_query,
            "result": clean_response(raw_response),
            "chart": chart_html,
        }
    except Exception as e:
        logger.error(f"🚨 Error executing query: {e}")
        return {"error": f"⚠️ Error: {str(e)}"}
