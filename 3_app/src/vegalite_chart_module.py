# vegalite_chart_module.py

import json
import re
import altair as alt
from langchain_openai import ChatOpenAI


def generate_dynamic_vega_lite_script(log: dict, llm: ChatOpenAI) -> str:
    """
    Uses the provided log data to dynamically generate a Vega-Lite specification using an LLM.
    The LLM analyzes the log (which includes conversation context, user query, SQL query, raw data, and final answer)
    and automatically determines the best chart type and encodings.

    Parameters:
      - log (dict): A dictionary containing keys like 'conversation', 'user_query', 'sql_query', 'data', and 'final_answer'.
      - llm (ChatOpenAI): An instance of the LLM (e.g., GPT-4o).

    Returns:
      A string containing the raw Vega-Lite specification (which might be wrapped with additional text).
    """
    prompt = (
        "You are an expert data visualization developer. "
        "Given the following log data which includes conversation context, a user query, the SQL query that was executed, "
        "the raw data (in a JSON-like format under the 'data' field), and the final answer, please analyze the data and "
        "automatically determine the best type of chart along with its encodings (axes, mark, color, etc.). "
        "Generate a complete and valid Vega-Lite JSON specification that visualizes the data appropriately based on the context. "
        "Do not include any commentary or explanation—only output the JSON specification.\n\n"
        "Log data:\n"
        f"{log}"
    )

    # Invoke the LLM and return the response.
    response = llm.invoke(prompt)
    return response


def extract_vega_lite_json(spec_response) -> dict:
    """
    Extracts the JSON block from the LLM's response.
    The response may be a string or an object with a `.content` attribute.

    Parameters:
      - spec_response: Either a string or an object with a .content attribute containing the spec.

    Returns:
      A dictionary parsed from the JSON block.

    Raises:
      ValueError if no JSON object can be found or if parsing fails.
    """
    # Get the string content from the response.
    spec_str = (
        spec_response.content if hasattr(spec_response, "content") else spec_response
    )

    # Extract the JSON object from the text using a regular expression.
    json_match = re.search(r"(\{.*\})", spec_str, re.DOTALL)
    if not json_match:
        raise ValueError("No JSON object found in the LLM response.")

    json_block = json_match.group(1)
    try:
        spec_dict = json.loads(json_block)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing JSON: {e}")

    return spec_dict


def render_chart_from_log(log: dict, llm: ChatOpenAI) -> str:
    """
    Generates a Vega-Lite specification from the provided log data using an LLM,
    creates an Altair chart from that specification, and returns the chart as an HTML string.

    This HTML string can then be embedded in your UI within a collapsible window (e.g., below the SQL query window).
    The chart is rendered dynamically and is not saved to disk.

    Parameters:
      - log (dict): The log data containing conversation, user_query, sql_query, data, final_answer.
      - llm (ChatOpenAI): An instance of the LLM (e.g., GPT-4o).

    Returns:
      A string containing the HTML representation of the chart.
    """
    # Generate the raw Vega-Lite spec using the LLM.
    spec_response = generate_dynamic_vega_lite_script(log, llm)

    # Extract the actual JSON spec from the LLM's response.
    spec_dict = extract_vega_lite_json(spec_response)

    # Create an Altair chart using the extracted spec.
    chart = alt.Chart.from_dict(spec_dict)

    # Return the chart as an HTML string for UI rendering.
    return chart.to_html()


# Example usage:
if __name__ == "__main__":
    # Instantiate your LLM (make sure your API keys/configurations are set)
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # Sample log data (replace with actual log data)
    sample_log = {
        "conversation": "[HumanMessage(content='[]\\nHuman: how many products?', ...), AIMessage(content='There are 5,000 products in the database.', ...)]",
        "user_query": "give me top 5 products",
        "sql_query": "SELECT product_id, product_type, interest_rate, minimum_balance, risk_level FROM financialproducts ORDER BY interest_rate DESC LIMIT 5;",
        "data": "[('4a6ff892-75cb-4dea-8278-f2d0391f95ce', 'Savings Account', 10.0, 2249, 'Medium'), "
        "('b4a9a0b9-6142-4162-a674-d3400bfdec48', 'Mutual Fund', 9.99, 112, 'Low'), "
        "('f1770e75-4b11-4958-a6bb-c08f589ef619', 'Bond', 9.99, 2125, 'High'), "
        "('c75c4966-5c03-40cb-809d-b8fa918f7e85', 'Mutual Fund', 9.99, 4994, 'High'), "
        "('fa0d6b96-e139-457f-bfaa-79d92854c156', 'Mutual Fund', 9.99, 1016, 'High')]",
        "final_answer": "Here are the top 5 products based on interest rate: ...",
    }

    # Render the chart HTML (to be inserted in the UI's collapsible window)
    chart_html = render_chart_from_log(sample_log, llm)
    print(chart_html)
