"""
chart.py
--------
Generates Vega-Lite chart HTML from query result log data using an LLM.
Uses json_repair to gracefully handle malformed JSON returned by the LLM.
"""

import json
import logging
import re

import altair as alt
from json_repair import repair_json
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def _generate_vega_lite_spec(log: dict, llm: ChatOpenAI) -> str:
    """Ask the LLM to produce a Vega-Lite JSON spec for the given query result."""
    prompt = (
        "You are an expert data visualization developer. "
        "Given the following log data which includes conversation context, a user query, "
        "the SQL query that was executed, the raw data (under the 'data' field), "
        "and the final answer, analyze the data and automatically determine the best "
        "chart type and encodings (axes, mark, color, etc.). "
        "Generate a complete and valid Vega-Lite JSON specification. "
        "Output ONLY the JSON — no commentary, no markdown fences.\n\n"
        f"Log data:\n{log}"
    )
    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


def _parse_vega_lite_json(raw: str) -> dict:
    """
    Extract and parse the JSON object from the LLM response.
    Falls back to json_repair when the LLM returns slightly malformed JSON.
    """
    json_match = re.search(r"(\{.*\})", raw, re.DOTALL)
    json_block = json_match.group(1) if json_match else raw

    try:
        return json.loads(json_block)
    except json.JSONDecodeError:
        logger.warning("LLM returned malformed JSON — attempting auto-repair.")
        repaired = repair_json(json_block)
        return json.loads(repaired)


def render_chart_from_log(log: dict, llm: ChatOpenAI) -> str | None:
    """
    Generate a Vega-Lite chart from query log data and return it as an HTML string.
    Returns None if chart generation fails so that callers can degrade gracefully.
    """
    raw_spec = _generate_vega_lite_spec(log, llm)
    spec_dict = _parse_vega_lite_json(raw_spec)
    chart = alt.Chart.from_dict(spec_dict)
    return chart.to_html()
