"""
app.py
------
Cloudera Database Assistant 의 메인 Streamlit 애플리케이션입니다.

화면 구성:
  - 상단 고정 오렌지색 배너 (앱 제목 표시)
  - 채팅 인터페이스 (사용자 질의 입력 및 대화 히스토리 표시)
  - 어시스턴트 응답: Response / SQL Query / Chart 3개 탭으로 구성
  - 좌하단 플로팅 기어 아이콘 (설정 페이지 사이드바 열기)

Streamlit rerun 최적화:
  사용자 입력 → 사용자 메시지 즉시 렌더링 → 에이전트 실행 → 응답 렌더링
  → 세션 상태 저장 → 최종 rerun (1회)
  (기존 2회 rerun 방식 대비 불필요한 화면 깜빡임 제거)
"""

import streamlit as st
from src.agent import execute_sql_query

# ── UI 스타일 및 배너 HTML ────────────────────────────────────────────────
# CSS 와 HTML 을 상수로 분리해 main() 함수 가독성을 높입니다.
# unsafe_allow_html=True 로 st.markdown() 에 직접 삽입됩니다.
_BANNER_CSS = """
<style>
/* Streamlit 기본 헤더 숨김 (커스텀 배너로 대체) */
header[data-testid="stHeader"] { display: none; }
/* 구버전 Streamlit 내부 클래스 숨김 */
.css-h5rgaw.egzxvld2 { display: none !important; }

/* ── 상단 고정 오렌지 배너 ───────────────────────────────────────── */
.title-bar {
    background-color: #F7931E;  /* Cloudera 브랜드 오렌지 */
    position: fixed; top: 0; left: 0;
    width: 100%; z-index: 9999;   /* 다른 모든 요소 위에 표시 */
    padding: 1rem; text-align: center;
}
.title-bar h1 {
    color: white; margin: 0;
    font-size: 1.5rem; font-weight: 600;
}

/* ── 메인 컨테이너: 배너 높이만큼 상단 여백 확보 ───────────────── */
[data-testid="stAppViewContainer"] {
    margin-top: 100px;         /* 배너 아래 콘텐츠가 가려지지 않도록 */
    max-width: 1350px;         /* 넓은 화면에서도 읽기 편한 최대 너비 */
    margin-left: auto; margin-right: auto;
    background-color: #FFFFFF;
    border: 2px solid #F7931E; /* 오렌지 테두리로 브랜드 일관성 유지 */
    border-radius: 8px;
    padding: 1rem; margin-bottom: 10px;
}

/* ── 좌하단 플로팅 기어 버튼 (설정 페이지 진입) ────────────────── */
.floating-gear {
    position: fixed; bottom: 80px; left: 20px;  /* 채팅 입력 위에 배치 */
    width: 60px; height: 60px;
    background-color: #F7931E; border-radius: 50%;
    text-align: center; z-index: 9999; cursor: pointer;
}
.floating-gear img { width: 32px; height: 32px; margin-top: 14px; }
.floating-gear:hover { background-color: #d97a17; }  /* 호버 시 어두운 오렌지 */

/* ── 채팅 메시지 아바타 숨김 (커스텀 스타일과 충돌 방지) ────────── */
[data-testid="stChatMessage-avatar"],
[data-testid="stChatMessage-avatar"] img { display: none !important; }

/* ── 사용자 메시지 버블: 우측 정렬, 파란 배경 ──────────────────── */
[data-testid="stChatMessage"]:has(> [data-testid="stChatMessageMeta"] > div:contains("user")) {
    background-color: #E1F0FF !important;
    border: 1px solid #ccc; border-radius: 10px;
    margin-left: auto !important; margin-right: 0 !important;
    width: fit-content; max-width: 65%;
    margin-bottom: 0.5rem !important; text-align: right;
}

/* ── 어시스턴트 메시지 버블: 좌측 정렬, 회색 배경 ──────────────── */
[data-testid="stChatMessage"]:has(> [data-testid="stChatMessageMeta"] > div:contains("assistant")) {
    background-color: #F5F5F5 !important;
    border: 1px solid #ccc; border-radius: 10px;
    margin-right: auto !important; margin-left: 0 !important;
    width: fit-content; max-width: 65%;
    margin-bottom: 0.5rem !important;
}
[data-testid="stChatMessage"] > div { padding: 0.75rem 1rem; }

/* ── 탭 스타일 ──────────────────────────────────────────────────── */
div.stTabs [role="tablist"] {
    background-color: #ECECEC;
    border-radius: 8px 8px 0 0; margin-top: 0.5rem;
}
div[role="tab"] { font-weight: 600 !important; }

/* ── 사용자 메시지 내부 레이아웃 우측 정렬 ─────────────────────── */
[class*="st-key-user-message"] .stChatMessage {
    flex-direction: row-reverse; text-align: right;
}
</style>

<!-- 상단 고정 배너 -->
<div class="title-bar"><h1>Cloudera Database Assistant</h1></div>

<!-- 설정 페이지를 여는 플로팅 기어 버튼 -->
<div class="floating-gear" onclick="toggleSidebar()">
    <img src="https://img.icons8.com/ios-filled/50/ffffff/settings.png" />
</div>

<script>
// Streamlit 사이드바 토글 버튼을 프로그래밍 방식으로 클릭합니다.
// Streamlit 버전에 따라 버튼 선택자가 다를 수 있어 두 가지를 시도합니다.
function toggleSidebar() {
  let btn = document.querySelector('button[title="Main menu"]');
  if (!btn) btn = document.querySelector('div[data-testid="collapsedControl"] button');
  if (btn) btn.click();
}
</script>
"""


def _render_assistant_content(content: dict) -> None:
    """
    어시스턴트 응답을 3개 탭으로 렌더링합니다.

    탭 구성:
      - Response  : LLM 이 생성한 자연어 요약 (마크다운 형식)
      - SQL Query : 실행된 SQL 쿼리 (코드 하이라이팅)
      - Chart     : Vega-Lite 기반 인터랙티브 차트 HTML
                   (차트 생성 실패 시 안내 메시지 표시)

    매개변수:
      content (dict): execute_sql_query() 의 반환값
                      성공: {"query": ..., "result": ..., "chart": ...}
                      실패: {"error": ...}
    """
    # 에이전트 실행 실패 시 에러 메시지를 빨간 박스로 표시합니다.
    if "error" in content:
        st.error(content["error"])
        return

    # 3개 탭을 생성합니다.
    tabs = st.tabs(["Response", "SQL Query", "Chart"])

    with tabs[0]:
        # 자연어 요약: 마크다운 렌더링 (볼드, 리스트, 표 등 지원)
        st.markdown(content["result"])

    with tabs[1]:
        # SQL 쿼리: 신택스 하이라이팅과 복사 버튼 제공
        st.code(content["query"], language="sql")

    with tabs[2]:
        if content.get("chart"):
            # Vega-Lite HTML 을 iframe 형태로 임베드합니다.
            # height=400: 차트 기본 높이, scrolling=True: 차트가 크면 스크롤 허용
            st.components.v1.html(content["chart"], height=400, scrolling=True)  # type: ignore
        else:
            # 차트 생성 실패 또는 시각화 불필요한 쿼리인 경우 안내 메시지 표시
            st.info("이 쿼리에 대한 차트를 생성할 수 없습니다.")


def _display_history() -> None:
    """
    세션 상태에 저장된 모든 이전 대화를 화면에 렌더링합니다.

    st.session_state["messages"] 리스트를 순회하며 각 메시지를 표시합니다.
    unique_key 를 설정해 Streamlit 의 DuplicateWidgetID 오류를 방지합니다.
    """
    for index, msg in enumerate(st.session_state["messages"]):
        role = msg["role"]
        content = msg["content"]
        # 각 메시지 컨테이너에 고유 키를 부여합니다.
        unique_key = f"{role}-message-{index}"

        if role == "user":
            with st.container(key=unique_key):
                with st.chat_message(
                    "user",
                    avatar="https://img.icons8.com/color/48/gender-neutral-user.png",
                ):
                    st.markdown(content, unsafe_allow_html=True)
        else:
            # 어시스턴트 메시지는 3탭 응답 렌더러로 표시합니다.
            with st.container(key=unique_key):
                with st.chat_message(
                    "assistant",
                    avatar="https://img.icons8.com/fluency/48/bot.png",
                ):
                    _render_assistant_content(content)


def main() -> None:
    """
    Streamlit 앱의 진입점(entry point) 함수입니다.

    실행 흐름 (사용자 메시지 입력 시):
      1. 사용자 메시지를 session_state 에 저장합니다.
      2. 사용자 메시지를 즉시 화면에 렌더링합니다.
      3. 스피너를 표시하며 에이전트로 쿼리를 실행합니다.
      4. 응답 결과를 3탭으로 렌더링합니다.
      5. 응답을 session_state 에 저장합니다.
      6. st.rerun() 으로 화면을 갱신합니다. (1회)

    기존의 2회 rerun 방식 대신 같은 실행 사이클 내에서
    사용자 메시지와 응답을 모두 처리해 불필요한 화면 깜빡임을 제거했습니다.
    """
    st.set_page_config(
        page_title="Cloudera Database Assistant",
        layout="wide",
        initial_sidebar_state="collapsed",  # 사이드바 기본 숨김
    )
    # 배너 CSS 및 플로팅 버튼 HTML 삽입
    st.markdown(_BANNER_CSS, unsafe_allow_html=True)

    # 세션 상태 초기화: 첫 방문 시 빈 메시지 리스트를 생성합니다.
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # 이전 대화 히스토리를 화면에 렌더링합니다.
    _display_history()

    # 채팅 입력창: 사용자가 엔터를 누르면 user_input 에 값이 할당됩니다.
    user_input = st.chat_input("데이터베이스에 대해 질문해 보세요...")
    if user_input:
        # 1. 사용자 메시지를 세션에 저장합니다.
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # 2. 사용자 메시지를 현재 화면에 즉시 표시합니다.
        with st.chat_message(
            "user",
            avatar="https://img.icons8.com/color/48/gender-neutral-user.png",
        ):
            st.markdown(user_input, unsafe_allow_html=True)

        # 3. 에이전트 실행 및 응답 렌더링
        with st.chat_message(
            "assistant",
            avatar="https://img.icons8.com/fluency/48/bot.png",
        ):
            # 에이전트 실행 중 로딩 스피너를 표시합니다.
            # (LLM 호출은 수초~수십 초 소요될 수 있음)
            with st.spinner("질문을 분석하는 중..."):
                response_dict = execute_sql_query(user_input)
            # 응답 결과를 3탭으로 렌더링합니다.
            _render_assistant_content(response_dict)

        # 4. 응답을 세션에 저장합니다.
        st.session_state["messages"].append(
            {"role": "assistant", "content": response_dict}
        )

        # 5. 화면을 갱신해 히스토리가 올바르게 표시되도록 합니다.
        #    이 rerun 이후에는 user_input 이 없으므로 에이전트가 재실행되지 않습니다.
        st.rerun()


if __name__ == "__main__":
    main()
