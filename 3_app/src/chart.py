"""
chart.py
--------
쿼리 결과 로그 데이터를 기반으로 Vega-Lite 차트를 생성하는 모듈입니다.

처리 흐름:
  1. LLM 에 쿼리 결과 데이터를 전달해 최적의 Vega-Lite JSON 스펙을 요청합니다.
  2. LLM 응답에서 JSON 블록을 정규식으로 추출합니다.
  3. JSON 파싱에 실패하면 json_repair 라이브러리로 자동 복구를 시도합니다.
  4. Altair 라이브러리로 차트 객체를 생성하고 HTML 문자열로 변환합니다.

json_repair 를 사용하면 LLM 이 마크다운 펜스(```json```)나 불완전한 JSON 을
반환하더라도 차트 탭이 크래시 없이 렌더링됩니다.
"""

import json
import logging
import re

import altair as alt
from json_repair import repair_json  # LLM 이 반환한 깨진 JSON 을 자동 복구
from langchain_openai import ChatOpenAI

# 이 모듈 전용 로거
logger = logging.getLogger(__name__)


def _generate_vega_lite_spec(log: dict, llm: ChatOpenAI) -> str:
    """
    LLM 에게 Vega-Lite JSON 스펙 생성을 요청합니다.

    매개변수:
      log (dict): 대화 컨텍스트, 사용자 질의, SQL 쿼리, 쿼리 결과 데이터를
                  포함하는 로그 딕셔너리
      llm (ChatOpenAI): 스펙 생성에 사용할 LLM 인스턴스

    반환값:
      LLM 이 생성한 Vega-Lite JSON 스펙 문자열
      (마크다운 펜스나 설명 텍스트가 포함될 수 있음)
    """
    # LLM 에게 역할과 출력 형식을 명확히 지시하는 프롬프트입니다.
    # "JSON 만 출력" 을 강조해 불필요한 설명 텍스트를 최소화합니다.
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
    # ChatOpenAI 응답은 AIMessage 객체이므로 .content 속성으로 문자열을 추출합니다.
    return response.content if hasattr(response, "content") else str(response)


def _parse_vega_lite_json(raw: str) -> dict:
    """
    LLM 응답 문자열에서 Vega-Lite JSON 객체를 추출하고 파싱합니다.

    처리 순서:
      1. 정규식으로 첫 번째 { } 블록을 추출합니다.
      2. 표준 json.loads() 로 파싱을 시도합니다.
      3. 실패하면 json_repair() 로 JSON 을 자동 복구한 후 다시 파싱합니다.

    매개변수:
      raw (str): LLM 이 반환한 원시 응답 문자열

    반환값:
      파싱된 Vega-Lite 스펙 딕셔너리

    예외:
      json.JSONDecodeError: json_repair 로도 복구 불가능한 경우
    """
    # re.DOTALL 플래그로 중괄호 사이의 줄바꿈도 매칭합니다.
    json_match = re.search(r"(\{.*\})", raw, re.DOTALL)
    # 중괄호 블록이 발견되면 해당 부분만 사용, 없으면 전체 문자열을 시도합니다.
    json_block = json_match.group(1) if json_match else raw

    try:
        # 정상적인 JSON 인 경우 바로 파싱합니다.
        return json.loads(json_block)
    except json.JSONDecodeError:
        # LLM 이 불완전한 JSON 을 반환한 경우 자동 복구를 시도합니다.
        # json_repair 는 누락된 따옴표, 쉼표, 괄호 등을 자동으로 보완합니다.
        logger.warning("LLM 이 유효하지 않은 JSON 을 반환했습니다 — 자동 복구를 시도합니다.")
        repaired = repair_json(json_block)
        return json.loads(repaired)


def render_chart_from_log(log: dict, llm: ChatOpenAI) -> str | None:
    """
    쿼리 결과 로그 데이터로부터 차트를 생성하고 HTML 문자열로 반환합니다.

    이 함수가 반환한 HTML 문자열은 app.py 의 st.components.v1.html() 에
    직접 삽입되어 브라우저에서 인터랙티브 차트로 렌더링됩니다.

    매개변수:
      log (dict): 대화 컨텍스트, 사용자 질의, SQL 쿼리, 데이터를 포함한 딕셔너리
      llm (ChatOpenAI): 스펙 생성에 사용할 LLM 인스턴스

    반환값:
      Altair 차트의 HTML 문자열 (성공 시)
      None (실패 시 — 호출자가 graceful degradation 처리)
    """
    # 1단계: LLM 으로 Vega-Lite JSON 스펙 생성
    raw_spec = _generate_vega_lite_spec(log, llm)

    # 2단계: 응답에서 JSON 추출 및 파싱 (자동 복구 포함)
    spec_dict = _parse_vega_lite_json(raw_spec)

    # 3단계: Altair 차트 객체 생성 후 HTML 로 변환
    # from_dict() 는 Vega-Lite 스펙 딕셔너리를 Altair Chart 로 변환합니다.
    chart = alt.Chart.from_dict(spec_dict)
    return chart.to_html()
