"""
pages/Settings UI.py
--------------------
Cloudera Database Assistant 설정 페이지입니다.

사용자가 UI 에서 변경한 설정값을 3_app/src/.env 파일에 직접 저장합니다.
저장된 값은 앱 재시작 시 config.py 를 통해 자동으로 로드됩니다.

설정 항목:
  1. 데이터베이스 연결 방식 (로컬 / 원격 SSH 터널)
  2. OpenAI 모델 선택 및 LLM 동작 파라미터 (Temperature, Top P)

주의: 설정 변경 후 "Save Settings" 버튼을 누르면 .env 파일이 업데이트되지만,
      변경 사항이 실제로 적용되려면 앱을 재시작해야 합니다.
      (@st.cache_resource 로 캐싱된 DB/에이전트가 재초기화되기 때문)
"""

import os
import streamlit as st
from dotenv import set_key, dotenv_values  # .env 파일 읽기/쓰기 유틸리티

from src.config import SETTINGS  # 현재 로드된 설정값

# .env 파일의 절대 경로를 동적으로 계산합니다.
# 이 파일(pages/Settings UI.py) 기준 ../src/.env 위치입니다.
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "src", ".env")

# 설정 UI 에서 제공하는 OpenAI 모델 목록입니다.
# 신규 모델 추가 시 이 리스트에만 추가하면 됩니다.
AVAILABLE_MODELS = [
    "gpt-4o",        # GPT-4o (가장 최신, 고성능)
    "gpt-4o-mini",   # GPT-4o Mini (빠르고 저렴, 기본 권장)
    "gpt-4-turbo",   # GPT-4 Turbo (128k 컨텍스트)
    "gpt-4",         # GPT-4 (구버전)
    "gpt-3.5-turbo", # GPT-3.5 Turbo (가장 빠르고 저렴)
    "custom-model",  # 사설 엔드포인트 커스텀 모델
]

# ── 페이지 기본 설정 ──────────────────────────────────────────────────────
# st.set_page_config() 은 페이지에서 가장 먼저 호출해야 합니다.
st.set_page_config(
    page_title="Settings",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 공통 배너 및 스타일 ───────────────────────────────────────────────────
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { display: none; }
    .css-h5rgaw.egzxvld2 { display: none !important; }
    .title-bar {
        background-color: #F7931E;
        position: fixed; top: 0; left: 0;
        width: 100%; z-index: 9999;
        padding: 1rem; text-align: center;
    }
    .title-bar h1 { color: white; margin: 0; font-size: 1.5rem; font-weight: 600; }
    [data-testid="stAppViewContainer"] {
        margin-top: 100px; max-width: 1350px;
        margin-left: auto; margin-right: auto;
        background-color: #FFFFFF; padding: 1rem; margin-bottom: 10px;
    }
    .floating-gear {
        position: fixed; bottom: 20px; left: 20px;
        width: 60px; height: 60px;
        background-color: #F7931E; border-radius: 50%;
        text-align: center; z-index: 9999; cursor: pointer;
    }
    .floating-gear img { width: 32px; height: 32px; margin-top: 14px; }
    .floating-gear:hover { background-color: #d97a17; }
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
    """,
    unsafe_allow_html=True,
)

st.title("Settings")
# 변경 사항이 앱 재시작 후 적용된다는 점을 사용자에게 안내합니다.
st.info("변경된 설정은 `.env` 파일에 저장되며, 앱을 재시작한 후 적용됩니다.", icon="ℹ️")

# ────────────────────────────────────────────────────────────────────────────
# 섹션 1: 데이터베이스 설정
# ────────────────────────────────────────────────────────────────────────────
st.header("데이터베이스 설정")

# 현재 설정에서 DB 연결 방식을 읽어 초기값으로 사용합니다.
IS_REMOTE_DB = SETTINGS["IS_REMOTE_DB"]
LOCAL_DB_URI = (
    SETTINGS["DATABASE_URI"]
    or "sqlite:///sample_sqlite.db"  # DATABASE_URI 가 None 이면 기본값 사용
)

# 로컬 / 원격 DB 연결 방식 선택
db_connection_type = st.radio(
    "데이터베이스 연결 방식을 선택하세요:",
    ["Local", "Remote"],
    index=1 if IS_REMOTE_DB else 0,  # 현재 설정에 따라 초기 선택값 결정
)

if db_connection_type == "Local":
    # ── 로컬 DB 설정 ────────────────────────────────────────────────────
    st.write("로컬 DB 에 직접 연결합니다.")
    # SQLAlchemy 형식의 접속 URI 를 직접 입력받습니다.
    # 예: sqlite:///sample_sqlite.db, postgresql://user:pw@localhost:5432/db
    new_db_uri = st.text_input("데이터베이스 URI", value=LOCAL_DB_URI)
else:
    # ── 원격 DB (SSH 터널) 설정 ──────────────────────────────────────────
    st.write("SSH 터널을 통해 원격 DB 에 연결합니다.")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("SSH 터널 설정")
        # SSH 서버 접속 정보: 원격 DB 가 위치한 서버의 SSH 정보입니다.
        new_ssh_host = st.text_input("SSH 호스트", value=os.getenv("SSH_HOST", ""))
        new_ssh_username = st.text_input("SSH 사용자명", value=os.getenv("SSH_USERNAME", ""))
        new_ssh_password = st.text_input(
            "SSH 비밀번호", value=os.getenv("SSH_PASSWORD", ""), type="password"
        )
        new_ssh_port = st.number_input(
            "SSH 포트", value=int(os.getenv("SSH_PORT", 22)),
            min_value=1, max_value=65535
        )

    with col2:
        st.subheader("원격 데이터베이스 설정")
        # DB 접속 정보: SSH 터널 내부에서 접근할 DB 의 정보입니다.
        new_db_host = st.text_input("DB 호스트", value=os.getenv("DB_HOST", ""))
        new_db_port = st.number_input(
            "DB 포트", value=int(os.getenv("DB_PORT", 5432)),
            min_value=1, max_value=65535
        )
        new_db_name = st.text_input("데이터베이스 이름", value=os.getenv("DB_NAME", ""))
        new_db_user = st.text_input("DB 사용자명", value=os.getenv("DB_USER", ""))
        new_db_password = st.text_input(
            "DB 비밀번호", value=os.getenv("DB_PASSWORD", ""), type="password"
        )

st.markdown("---")

# ────────────────────────────────────────────────────────────────────────────
# 섹션 2: 모델 설정
# ────────────────────────────────────────────────────────────────────────────
st.header("모델 설정")

# 현재 설정된 모델을 드롭다운 초기값으로 사용합니다.
current_model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
# 현재 모델이 목록에 없으면 첫 번째 항목(gpt-4o)을 기본값으로 선택합니다.
model_index = AVAILABLE_MODELS.index(current_model) if current_model in AVAILABLE_MODELS else 0

MODEL_NAME = st.selectbox("사용할 모델을 선택하세요", options=AVAILABLE_MODELS, index=model_index)

col1, col2 = st.columns(2)
with col1:
    TEMPERATURE = st.number_input(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=SETTINGS["TEMPERATURE"],
        step=0.1,
        help="높을수록 창의적이고 다양한 응답, 낮을수록 일관된 응답. SQL 생성에는 0.0 권장.",
    )
with col2:
    TOP_P = st.number_input(
        "Top P",
        min_value=0.0,
        max_value=1.0,
        value=SETTINGS["TOP_P"],
        step=0.1,
        help="핵 샘플링 확률. Temperature 와 함께 응답 다양성을 제어합니다.",
    )

st.markdown("---")

# ────────────────────────────────────────────────────────────────────────────
# 저장 버튼
# ────────────────────────────────────────────────────────────────────────────
if st.button("설정 저장", type="primary"):
    try:
        is_remote = db_connection_type == "Remote"

        # IS_REMOTE_DB 플래그를 먼저 저장합니다 (true / false 문자열).
        set_key(ENV_PATH, "IS_REMOTE_DB", str(is_remote).lower())

        if is_remote:
            # 원격 DB 모드: SSH 및 DB 접속 정보를 .env 에 저장합니다.
            set_key(ENV_PATH, "SSH_HOST", new_ssh_host)
            set_key(ENV_PATH, "SSH_PORT", str(int(new_ssh_port)))
            set_key(ENV_PATH, "SSH_USERNAME", new_ssh_username)
            set_key(ENV_PATH, "SSH_PASSWORD", new_ssh_password)
            set_key(ENV_PATH, "DB_HOST", new_db_host)
            set_key(ENV_PATH, "DB_PORT", str(int(new_db_port)))
            set_key(ENV_PATH, "DB_NAME", new_db_name)
            set_key(ENV_PATH, "DB_USER", new_db_user)
            set_key(ENV_PATH, "DB_PASSWORD", new_db_password)
        else:
            # 로컬 DB 모드: DATABASE_URI 만 저장합니다.
            set_key(ENV_PATH, "DATABASE_URI", new_db_uri)

        # 모델 설정 저장
        set_key(ENV_PATH, "OPENAI_MODEL_NAME", MODEL_NAME)
        set_key(ENV_PATH, "TEMPERATURE", str(TEMPERATURE))
        set_key(ENV_PATH, "TOP_P", str(TOP_P))

        st.success("설정이 .env 파일에 저장되었습니다. 앱을 재시작하면 변경 사항이 적용됩니다.")

    except Exception as e:
        # .env 파일 쓰기 권한 오류 등의 경우 에러를 표시합니다.
        st.error(f"설정 저장에 실패했습니다: {e}")
