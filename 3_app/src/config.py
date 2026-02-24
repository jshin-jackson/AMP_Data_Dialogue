"""
config.py
---------
애플리케이션 전체에서 사용하는 환경 변수를 로드하고 SETTINGS 딕셔너리로 노출하는
순수 설정 모듈입니다.

이 파일에는 Streamlit 호출이 없으므로, 어떤 모듈에서도 안전하게 import 할 수 있습니다.
환경 변수는 3_app/src/.env 파일 또는 시스템 환경에서 읽어옵니다.
"""

import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 시스템 환경으로 로드합니다.
# 이미 시스템 환경에 동일한 키가 있으면 .env 값은 무시됩니다.
load_dotenv()

# ── 데이터베이스 연결 방식 ──────────────────────────────────────────────────
# IS_REMOTE_DB=true 이면 SSH 터널을 통해 원격 PostgreSQL에 연결합니다.
# IS_REMOTE_DB=false(기본값)이면 로컬 SQLite 또는 직접 접근 가능한 DB를 사용합니다.
IS_REMOTE_DB = os.getenv("IS_REMOTE_DB", "false").lower().strip() == "true"

# 로컬 DB 접속 URI (SQLAlchemy 형식)
# 예: sqlite:///sample_sqlite.db, postgresql://user:pw@host:5432/dbname
DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///sample_sqlite.db")

# ── SSH 터널 설정 (IS_REMOTE_DB=true 일 때만 사용) ────────────────────────
SSH_HOST = os.getenv("SSH_HOST", "")          # SSH 서버 호스트 주소
SSH_USERNAME = os.getenv("SSH_USERNAME", "")  # SSH 접속 사용자명
SSH_PORT = int(os.getenv("SSH_PORT", "22"))   # SSH 포트 (기본값 22)
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "")  # SSH 접속 비밀번호

# ── 원격 데이터베이스 설정 (SSH 터널 내부에서 접근하는 DB) ─────────────────
DB_HOST = os.getenv("DB_HOST", "")        # DB 서버 내부 호스트
DB_NAME = os.getenv("DB_NAME", "")        # 데이터베이스 이름
DB_PORT = int(os.getenv("DB_PORT", "5432"))  # DB 포트 (PostgreSQL 기본값 5432)
DB_USER = os.getenv("DB_USER", "")        # DB 접속 사용자명
DB_PASSWORD = os.getenv("DB_PASSWORD", "")  # DB 접속 비밀번호

# ── OpenAI API 설정 ────────────────────────────────────────────────────────
# OPENAI_BASE_URL: 사설 OpenAI 호환 엔드포인트 사용 시 입력합니다.
#   공개 OpenAI 서비스를 사용하면 빈 문자열("")로 두면 됩니다.
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")          # OpenAI API 키
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")  # 사용할 모델명

# ── LLM 동작 파라미터 ──────────────────────────────────────────────────────
# MODEL_NAME: 설정 UI에서 사용자가 선택한 모델명 (OPENAI_MODEL_NAME 과 동기화)
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
# TEMPERATURE: 응답의 창의성 조절 (0.0 = 결정론적, 2.0 = 매우 창의적)
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
# TOP_P: 핵 샘플링 확률 (0.0~1.0, TEMPERATURE와 함께 응답 다양성을 제어)
TOP_P = float(os.getenv("TOP_P", "0.9"))

# ── 전체 설정 딕셔너리 ────────────────────────────────────────────────────
# 다른 모듈에서는 이 SETTINGS 딕셔너리를 import 해서 사용합니다.
# IS_REMOTE_DB 값에 따라 불필요한 필드를 None 으로 설정해 오용을 방지합니다.
SETTINGS: dict = {
    "IS_REMOTE_DB": IS_REMOTE_DB,

    # 로컬 DB URI: 원격 모드에서는 None
    "DATABASE_URI": DATABASE_URI if not IS_REMOTE_DB else None,

    # SSH 터널 설정: 로컬 모드에서는 모두 None
    "SSH_HOST": SSH_HOST if IS_REMOTE_DB else None,
    "SSH_USERNAME": SSH_USERNAME if IS_REMOTE_DB else None,
    "SSH_PORT": SSH_PORT if IS_REMOTE_DB else None,
    "SSH_PASSWORD": SSH_PASSWORD if IS_REMOTE_DB else None,

    # 원격 DB 설정: 로컬 모드에서는 모두 None
    "DB_HOST": DB_HOST if IS_REMOTE_DB else None,
    "DB_NAME": DB_NAME if IS_REMOTE_DB else None,
    "DB_PORT": DB_PORT if IS_REMOTE_DB else None,
    "DB_USER": DB_USER if IS_REMOTE_DB else None,
    "DB_PASSWORD": DB_PASSWORD if IS_REMOTE_DB else None,

    # OpenAI 및 LLM 파라미터: 연결 방식과 무관하게 항상 포함
    "OPENAI_BASE_URL": OPENAI_BASE_URL,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "OPENAI_MODEL_NAME": OPENAI_MODEL_NAME,
    "MODEL_NAME": MODEL_NAME,
    "TEMPERATURE": TEMPERATURE,
    "TOP_P": TOP_P,
}
