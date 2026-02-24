import streamlit as st
from src.agent import execute_sql_query

_BANNER_CSS = """
<style>
header[data-testid="stHeader"] { display: none; }
.css-h5rgaw.egzxvld2 { display: none !important; }

.title-bar {
    background-color: #F7931E;
    position: fixed; top: 0; left: 0;
    width: 100%; z-index: 9999;
    padding: 1rem; text-align: center;
}
.title-bar h1 {
    color: white; margin: 0;
    font-size: 1.5rem; font-weight: 600;
}
[data-testid="stAppViewContainer"] {
    margin-top: 100px;
    max-width: 1350px;
    margin-left: auto; margin-right: auto;
    background-color: #FFFFFF;
    border: 2px solid #F7931E;
    border-radius: 8px;
    padding: 1rem; margin-bottom: 10px;
}
.floating-gear {
    position: fixed; bottom: 80px; left: 20px;
    width: 60px; height: 60px;
    background-color: #F7931E; border-radius: 50%;
    text-align: center; z-index: 9999; cursor: pointer;
}
.floating-gear img { width: 32px; height: 32px; margin-top: 14px; }
.floating-gear:hover { background-color: #d97a17; }

[data-testid="stChatMessage-avatar"],
[data-testid="stChatMessage-avatar"] img { display: none !important; }

[data-testid="stChatMessage"]:has(> [data-testid="stChatMessageMeta"] > div:contains("user")) {
    background-color: #E1F0FF !important;
    border: 1px solid #ccc; border-radius: 10px;
    margin-left: auto !important; margin-right: 0 !important;
    width: fit-content; max-width: 65%;
    margin-bottom: 0.5rem !important; text-align: right;
}
[data-testid="stChatMessage"]:has(> [data-testid="stChatMessageMeta"] > div:contains("assistant")) {
    background-color: #F5F5F5 !important;
    border: 1px solid #ccc; border-radius: 10px;
    margin-right: auto !important; margin-left: 0 !important;
    width: fit-content; max-width: 65%;
    margin-bottom: 0.5rem !important;
}
[data-testid="stChatMessage"] > div { padding: 0.75rem 1rem; }
div.stTabs [role="tablist"] {
    background-color: #ECECEC;
    border-radius: 8px 8px 0 0; margin-top: 0.5rem;
}
div[role="tab"] { font-weight: 600 !important; }
[class*="st-key-user-message"] .stChatMessage {
    flex-direction: row-reverse; text-align: right;
}
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
"""


def _render_assistant_content(content: dict) -> None:
    """Render the three-tab assistant response (Response / SQL Query / Chart)."""
    if "error" in content:
        st.error(content["error"])
        return

    tabs = st.tabs(["Response", "SQL Query", "Chart"])
    with tabs[0]:
        st.markdown(content["result"])
    with tabs[1]:
        st.code(content["query"], language="sql")
    with tabs[2]:
        if content.get("chart"):
            st.components.v1.html(content["chart"], height=400, scrolling=True)  # type: ignore
        else:
            st.info("No chart available for this query.")


def _display_history() -> None:
    """Render all previous messages from session state."""
    for index, msg in enumerate(st.session_state["messages"]):
        role = msg["role"]
        content = msg["content"]
        unique_key = f"{role}-message-{index}"

        if role == "user":
            with st.container(key=unique_key):
                with st.chat_message(
                    "user",
                    avatar="https://img.icons8.com/color/48/gender-neutral-user.png",
                ):
                    st.markdown(content, unsafe_allow_html=True)
        else:
            with st.container(key=unique_key):
                with st.chat_message(
                    "assistant",
                    avatar="https://img.icons8.com/fluency/48/bot.png",
                ):
                    _render_assistant_content(content)


def main() -> None:
    st.set_page_config(
        page_title="Cloudera Database Assistant",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_BANNER_CSS, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    _display_history()

    user_input = st.chat_input("Ask a database question...")
    if user_input:
        # Append user message and immediately show it
        st.session_state["messages"].append({"role": "user", "content": user_input})

        with st.chat_message(
            "user",
            avatar="https://img.icons8.com/color/48/gender-neutral-user.png",
        ):
            st.markdown(user_input, unsafe_allow_html=True)

        # Stream the assistant response in the same run — no second rerun needed
        with st.chat_message(
            "assistant",
            avatar="https://img.icons8.com/fluency/48/bot.png",
        ):
            with st.spinner("Analyzing your question..."):
                response_dict = execute_sql_query(user_input)
            _render_assistant_content(response_dict)

        st.session_state["messages"].append(
            {"role": "assistant", "content": response_dict}
        )
        st.rerun()


if __name__ == "__main__":
    main()
