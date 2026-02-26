"""
agent.py
--------
LLM 및 LangChain SQL 에이전트의 초기화와 쿼리 실행을 담당하는 모듈입니다.

주요 설계 원칙:
  1. @st.cache_resource 를 통해 LLM 과 에이전트를 프로세스 당 1회만 초기화합니다.
     Streamlit 재로드마다 모델을 다시 불러오는 오버헤드를 없앱니다.

  2. 대화 기록은 ChatMessageHistory (LangChain 최신 API) 로 관리합니다.
     기존의 ConversationBufferMemory (deprecated) 를 대체합니다.

  3. SQLQueryCallbackHandler 는 요청마다 새 인스턴스를 생성합니다.
     전역 싱글턴 방식은 동시 요청 시 데이터가 섞일 수 있어 스레드 안전하지 않습니다.

모듈 의존 관계:
  agent.py → database.py → config.py
  agent.py → chart.py
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
from langchain_core.caches import BaseCache  # noqa: F401 – pydantic 2.11.x forward-ref 해결용
from langchain_openai import ChatOpenAI

# pydantic 2.11.x 에서 ChatOpenAI 의 BaseCache forward reference 가 자동으로
# resolve 되지 않는 문제를 수동으로 해결합니다.
# _types_namespace 로 BaseCache 를 명시적으로 제공해야 합니다.
try:
    ChatOpenAI.model_rebuild(_types_namespace={"BaseCache": BaseCache})
except Exception:
    ChatOpenAI.model_rebuild()

from src.config import SETTINGS
from src.database import get_db
from src.chart import render_chart_from_log

# 이 모듈 전용 로거
logger = logging.getLogger(__name__)

# ── 세션별 대화 기록 저장소 ───────────────────────────────────────────────
# session_id(문자열) → ChatMessageHistory 객체 를 매핑하는 인메모리 딕셔너리입니다.
# 앱을 재시작하면 초기화됩니다 (영속성이 필요하면 Redis 등 외부 저장소를 사용하세요).
_session_store: dict[str, ChatMessageHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """
    주어진 session_id 에 해당하는 대화 기록 객체를 반환합니다.

    처음 요청된 session_id 면 새 ChatMessageHistory 인스턴스를 생성해
    저장소에 등록한 후 반환합니다.

    매개변수:
      session_id (str): 세션 식별자 (기본값 "default")

    반환값:
      해당 세션의 ChatMessageHistory 인스턴스
    """
    if session_id not in _session_store:
        # 새로운 세션이면 빈 대화 기록을 생성합니다.
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]


def reset_session_history(session_id: str = "default") -> None:
    """
    특정 세션의 대화 기록을 초기화합니다.

    새 대화를 시작하거나 "대화 초기화" 버튼 클릭 시 호출됩니다.

    매개변수:
      session_id (str): 초기화할 세션 식별자
    """
    _session_store.pop(session_id, None)  # 키가 없어도 예외 없이 처리
    logger.info(f"세션 '{session_id}' 의 대화 기록이 초기화되었습니다.")


class SQLQueryCallbackHandler(BaseCallbackHandler):
    """
    LangChain SQL 에이전트가 실행하는 SQL 쿼리와 결과를 캡처하는 콜백 핸들러입니다.

    LangChain 에이전트는 도구(Tool) 를 통해 SQL 을 실행하는데,
    이 핸들러는 on_tool_start / on_tool_end / on_agent_action 이벤트를 통해
    실행된 SQL 쿼리와 결과를 수집합니다.

    인스턴스는 execute_sql_query() 호출마다 새로 생성해 스레드 안전성을 보장합니다.
    """

    def __init__(self):
        # 실행된 SQL 쿼리 목록 (여러 번 실행될 수 있으므로 리스트로 관리)
        self.sql_queries: list[str] = []
        # SQL 도구의 실행 결과 목록
        self.tool_outputs: list = []

    def on_tool_start(self, tool_name: str, tool_input: dict, **kwargs) -> None:
        """
        LangChain 도구가 실행되기 직전에 호출됩니다.

        SQL 관련 도구("sql_db", "sql_db_query")가 실행될 때만
        쿼리 문자열을 추출해 sql_queries 리스트에 저장합니다.

        매개변수:
          tool_name: 실행될 도구의 이름 (문자열 또는 딕셔너리)
          tool_input: 도구에 전달될 입력값 (딕셔너리 또는 JSON 문자열)
        """
        try:
            # 일부 LangChain 버전에서 tool_name 이 딕셔너리로 전달되는 경우 처리
            if isinstance(tool_name, dict) and "name" in tool_name:
                tool_name = tool_name["name"]  # type: ignore

            logger.info(f"도구 실행 시작: {tool_name}")

            # SQL 관련 도구만 처리합니다.
            if tool_name in ["sql_db", "sql_db_query"]:
                # tool_input 이 JSON 문자열로 전달된 경우 딕셔너리로 변환합니다.
                if isinstance(tool_input, str):
                    try:
                        tool_input = ast.literal_eval(tool_input)
                    except Exception:
                        logger.warning("tool_input 문자열을 딕셔너리로 변환할 수 없습니다.")
                        return

                # "query" 키에서 실제 SQL 쿼리를 추출합니다.
                query = tool_input.get("query") if isinstance(tool_input, dict) else None
                if query:
                    self.sql_queries.append(query)
                    logger.info(f"SQL 쿼리 캡처 완료: {query}")

        except Exception as e:
            logger.error(f"on_tool_start 처리 중 오류 발생: {e}")

    def on_tool_end(self, output, **kwargs) -> None:
        """
        LangChain 도구 실행이 완료된 직후 호출됩니다.
        도구의 출력 결과(SQL 실행 결과 등)를 tool_outputs 리스트에 저장합니다.

        매개변수:
          output: 도구 실행 결과 (문자열 또는 데이터 구조)
        """
        self.tool_outputs.append(output)

    def on_agent_action(self, action, **kwargs) -> None:
        """
        에이전트가 다음 실행할 도구를 결정했을 때 호출됩니다.
        on_tool_start 가 SQL 을 캡처하지 못한 경우의 폴백(fallback)으로 동작합니다.

        매개변수:
          action: AgentAction 객체 (tool, tool_input 속성 포함)
        """
        try:
            if hasattr(action, "tool") and action.tool in ["sql_db", "sql_db_query"]:
                query = action.tool_input.get("query")
                if query:
                    self.sql_queries.append(query)
                    logger.info(f"에이전트 액션에서 SQL 쿼리 캡처: {query}")
        except Exception as e:
            logger.error(f"on_agent_action 처리 중 오류 발생: {e}")


def _build_llm() -> ChatOpenAI:
    """
    설정 값에 따라 ChatOpenAI 인스턴스를 생성합니다.

    OPENAI_BASE_URL 이 설정된 경우:
      - 사설 OpenAI 호환 엔드포인트(예: Cloudera AI Inference)를 사용합니다.
      - SSL 검증을 비활성화한 httpx 클라이언트를 사용합니다.
        (내부망 인증서 문제 대응)

    OPENAI_BASE_URL 이 비어있는 경우:
      - 공개 OpenAI API 를 사용합니다.

    반환값:
      초기화된 ChatOpenAI 인스턴스
    """
    base_url = SETTINGS["OPENAI_BASE_URL"]
    if base_url:
        # 사설 엔드포인트: SSL 검증 비활성화 (내부망 자체 서명 인증서 대응)
        return ChatOpenAI(
            model=SETTINGS["OPENAI_MODEL_NAME"],
            base_url=base_url,
            api_key=SETTINGS["OPENAI_API_KEY"],
            http_client=httpx.Client(verify=False),
            temperature=0,  # SQL 생성은 결정론적이어야 하므로 0으로 설정
        )
    # 공개 OpenAI API 사용
    return ChatOpenAI(
        model=SETTINGS["OPENAI_MODEL_NAME"],
        api_key=SETTINGS["OPENAI_API_KEY"],
        temperature=0,
    )


@st.cache_resource(show_spinner="AI 에이전트를 초기화하는 중...")
def _get_agent_and_llm():
    """
    LLM 과 SQL 에이전트를 초기화하고 캐싱합니다.

    @st.cache_resource 덕분에:
      - 앱 서버 프로세스당 최초 1회만 실행됩니다.
      - Streamlit 재로드, 사용자 입력, 페이지 전환 등 모든 rerun 에서
        동일한 LLM/에이전트 인스턴스를 재사용합니다.

    처리 순서:
      1. get_db() 로 캐싱된 DB 연결을 가져옵니다.
      2. _build_llm() 으로 LLM 인스턴스를 생성합니다.
      3. create_sql_agent() 로 LangChain SQL 에이전트를 구성합니다.

    반환값:
      (agent_executor, llm) 튜플 (성공 시)
      (None, None) 튜플 (DB 연결 실패 또는 초기화 오류 시)
    """
    # DB 연결 확인 (get_db() 도 cache_resource 로 캐싱됨)
    db = get_db()
    if db is None:
        logger.error("DB 연결 없이 에이전트를 초기화할 수 없습니다.")
        return None, None

    try:
        llm = _build_llm()

        # create_sql_agent: DB 스키마를 자동으로 읽고,
        # 자연어 질의를 SQL 로 변환·실행하는 에이전트를 구성합니다.
        # agent_type="openai-tools": OpenAI Function Calling 방식 사용
        agent_executor = create_sql_agent(
            llm,
            db=db,
            agent_type="openai-tools",
            verbose=True,  # 에이전트의 추론 과정을 서버 로그에 출력
        )

        # 사용 가능한 도구 목록을 로그에 기록합니다.
        for tool in agent_executor.tools:
            logger.info(f"에이전트 도구 등록됨: {tool.name}")

        logger.info("LangChain SQL 에이전트 초기화 완료.")
        return agent_executor, llm

    except Exception as e:
        logger.error(f"에이전트 초기화 실패: {e}")
        return None, None


def _clean_response(response) -> str:
    """
    에이전트의 원시 응답에서 최종 텍스트만 추출하고 정리합니다.

    LangChain 에이전트는 {"output": "..."} 딕셔너리 형태로 응답을 반환합니다.
    "output:" 같은 불필요한 접두사를 정규식으로 제거합니다.

    매개변수:
      response: 에이전트 응답 (딕셔너리 또는 문자열)

    반환값:
      정리된 응답 텍스트 문자열
    """
    if isinstance(response, dict) and "output" in response:
        text = response["output"].strip()
    else:
        text = str(response).strip()
    # "output:", "output :" 같은 접두사 제거 (대소문자 무시)
    return re.sub(r"^output:?\s*", "", text, flags=re.IGNORECASE)


def execute_sql_query(
    user_query: str,
    session_id: str = "default",
    column_names: list | None = None,
) -> dict:
    """
    사용자의 자연어 질의를 SQL 에이전트를 통해 실행하고 결과를 반환합니다.

    처리 흐름:
      1. 캐싱된 에이전트와 LLM 을 가져옵니다.
      2. 해당 세션의 대화 기록을 불러와 컨텍스트로 포함시킵니다.
      3. 에이전트에 질의를 전달하고 SQL 을 생성·실행합니다.
      4. 대화 기록에 이번 질의와 응답을 추가합니다.
      5. 쿼리 결과로 차트 HTML 을 생성합니다 (실패해도 텍스트 응답은 유지).

    매개변수:
      user_query (str): 사용자가 입력한 자연어 질의
      session_id (str): 대화 기록을 구분할 세션 ID (기본값 "default")
      column_names (list | None): SQL 결과 튜플을 딕셔너리로 변환할 컬럼명 목록

    반환값:
      성공 시: {"query": SQL문, "result": 텍스트 응답, "chart": HTML 또는 None}
      실패 시: {"error": 에러 메시지}
    """
    # 에이전트 초기화 확인 (DB 연결 실패 등으로 None 일 수 있음)
    agent_executor, llm = _get_agent_and_llm()
    if agent_executor is None:
        return {"error": "SQL 에이전트가 초기화되지 않았습니다. DB 연결과 API 키를 확인하세요."}

    # 쿼리마다 새 콜백 인스턴스를 생성해 스레드 안전성을 보장합니다.
    callback = SQLQueryCallbackHandler()

    try:
        logger.info(f"사용자 질의: {user_query}")

        # 현재 세션의 대화 기록을 텍스트 형식으로 구성합니다.
        # "Human: ..." / "Ai: ..." 형식으로 이어지는 대화를 에이전트에게 컨텍스트로 제공합니다.
        history = get_session_history(session_id)
        history_text = "\n".join(
            f"{m.type.capitalize()}: {m.content}" for m in history.messages
        )
        # 이전 대화가 있으면 컨텍스트로 포함, 없으면 현재 질의만 전달합니다.
        full_query = f"{history_text}\nHuman: {user_query}" if history_text else user_query

        # 에이전트 실행: 내부적으로 DB 스키마 조회 → SQL 생성 → SQL 실행 → 결과 해석
        raw_response = agent_executor.invoke(
            full_query,
            config={"callbacks": [callback]},  # SQL 캡처 콜백 연결
        )

        # 실행 결과를 대화 기록에 추가합니다 (다음 질의의 컨텍스트로 활용)
        history.add_user_message(user_query)
        history.add_ai_message(_clean_response(raw_response))

        # 콜백 핸들러에서 캡처된 마지막 SQL 쿼리를 사용합니다.
        # (에이전트가 여러 번 SQL 을 실행한 경우 최종 실행된 쿼리를 반환)
        sql_query = (
            callback.sql_queries[-1]
            if callback.sql_queries
            else "SQL 쿼리를 추출할 수 없습니다."
        )
        # 마지막 SQL 도구의 실행 결과 (원시 데이터)
        raw_sql_result = (
            callback.tool_outputs[-1]
            if callback.tool_outputs
            else "SQL 도구 출력을 캡처하지 못했습니다."
        )

        # column_names 가 제공된 경우 튜플 목록을 딕셔너리 목록으로 변환합니다.
        # 예: [("Alice", 30)] + ["name", "age"] → [{"name": "Alice", "age": 30}]
        if column_names and isinstance(raw_sql_result, list):
            data = [dict(zip(column_names, row)) for row in raw_sql_result]
        else:
            data = raw_sql_result

        # 차트 생성에 필요한 컨텍스트 데이터를 딕셔너리로 구성합니다.
        log_data = {
            "conversation": history_text,  # 이전 대화 컨텍스트
            "user_query": user_query,       # 현재 사용자 질의
            "sql_query": sql_query,         # 실행된 SQL 쿼리
            "data": data,                   # SQL 실행 결과 데이터
        }

        # 차트 생성은 독립적인 try/except 로 감쌉니다.
        # 차트 생성에 실패하더라도 텍스트와 SQL 응답은 정상 반환합니다.
        chart_html = None
        try:
            chart_html = render_chart_from_log(log_data, llm)
            logger.info("차트가 성공적으로 생성되었습니다.")
        except Exception as chart_err:
            # 차트 실패는 경고 수준으로 기록 (전체 응답을 실패시키지 않음)
            logger.warning(f"차트 생성 실패 (비치명적): {chart_err}")

        return {
            "query": sql_query,                    # 실행된 SQL 쿼리 문자열
            "result": _clean_response(raw_response),  # 정리된 텍스트 응답
            "chart": chart_html,                   # 차트 HTML (없으면 None)
        }

    except Exception as e:
        # 에이전트 실행 자체가 실패한 경우 에러 딕셔너리를 반환합니다.
        # app.py 에서 이 경우를 감지해 에러 메시지를 표시합니다.
        logger.error(f"쿼리 실행 오류: {e}")
        return {"error": f"오류: {str(e)}"}
