"""
database.py
-----------
데이터베이스 연결을 담당하는 모듈입니다.

주요 기능:
  - 로컬 DB (SQLite, PostgreSQL 등) 직접 연결
  - 원격 DB SSH 터널을 통한 연결 (IS_REMOTE_DB=true 설정 시)
  - @st.cache_resource 를 사용해 Streamlit 재로드 시 연결을 재사용함으로써
    불필요한 재연결 오버헤드를 제거

SSH 터널은 프로세스 종료 시 atexit 핸들러를 통해 자동으로 닫힙니다.
"""

import atexit
import logging

import streamlit as st
from sshtunnel import SSHTunnelForwarder
from langchain_community.utilities import SQLDatabase

from src.config import SETTINGS

# 이 모듈 전용 로거를 생성합니다.
# 로그는 server.log 파일로 출력됩니다 (app.py 에서 basicConfig 설정).
logger = logging.getLogger(__name__)

# SSH 터널 객체를 모듈 수준 변수로 유지합니다.
# None 이면 터널이 열리지 않은 상태를 의미합니다.
_ssh_tunnel: SSHTunnelForwarder | None = None


def _close_ssh_tunnel() -> None:
    """
    SSH 터널을 안전하게 종료하는 정리 함수입니다.

    atexit 에 등록되어 Python 프로세스가 종료될 때 자동으로 호출됩니다.
    터널이 활성 상태일 때만 stop() 을 호출해 불필요한 예외를 방지합니다.
    """
    global _ssh_tunnel
    if _ssh_tunnel and _ssh_tunnel.is_active:
        _ssh_tunnel.stop()
        logger.info("SSH 터널이 정상적으로 종료되었습니다.")


# 프로세스 종료 시 SSH 터널을 자동으로 닫도록 등록합니다.
atexit.register(_close_ssh_tunnel)


def _get_database_uri() -> str:
    """
    데이터베이스 접속 URI 문자열을 반환합니다.

    IS_REMOTE_DB=true 인 경우:
      1. SSHTunnelForwarder 로 로컬 포트 포워딩 터널을 열고
      2. 터널의 로컬 바인드 포트를 사용해 PostgreSQL URI 를 동적으로 구성합니다.

    IS_REMOTE_DB=false 인 경우:
      config.py 의 DATABASE_URI 값을 그대로 반환합니다.

    반환값:
      SQLAlchemy 형식의 DB 접속 URI 문자열
    """
    global _ssh_tunnel

    if SETTINGS["IS_REMOTE_DB"]:
        logger.info("원격 DB 모드: SSH 터널을 시작합니다.")

        # SSHTunnelForwarder 는 SSH 서버를 통해 원격 DB 포트를
        # 로컬의 임의 포트로 포워딩해 줍니다.
        _ssh_tunnel = SSHTunnelForwarder(
            (SETTINGS["SSH_HOST"], int(SETTINGS["SSH_PORT"])),  # SSH 서버 주소:포트
            ssh_username=SETTINGS["SSH_USERNAME"],              # SSH 사용자명
            ssh_password=SETTINGS["SSH_PASSWORD"],              # SSH 비밀번호
            remote_bind_address=(
                SETTINGS["DB_HOST"],          # 원격 DB 내부 호스트
                int(SETTINGS["DB_PORT"]),     # 원격 DB 포트
            ),
        )
        _ssh_tunnel.start()  # 터널 연결 시작 (블로킹)

        # 터널이 열린 후 local_bind_port 에 실제 로컬 포트가 할당됩니다.
        # 이 포트로 localhost 에 연결하면 원격 DB 에 도달합니다.
        return (
            f"postgresql://{SETTINGS['DB_USER']}:{SETTINGS['DB_PASSWORD']}"
            f"@127.0.0.1:{_ssh_tunnel.local_bind_port}/{SETTINGS['DB_NAME']}"
        )

    # 로컬 모드: .env 의 DATABASE_URI 를 그대로 사용합니다.
    return SETTINGS["DATABASE_URI"]


@st.cache_resource(show_spinner="데이터베이스에 연결하는 중...")
def get_db() -> SQLDatabase | None:
    """
    LangChain SQLDatabase 인스턴스를 반환합니다.

    @st.cache_resource 데코레이터 덕분에:
      - 최초 호출 시 한 번만 DB 연결을 생성합니다.
      - 이후 모든 Streamlit 재로드(rerun)에서 동일한 연결 객체를 재사용합니다.
      - 서버를 재시작하기 전까지 연결이 유지됩니다.

    echo=False 설정으로 SQLAlchemy 의 SQL 로그 출력을 비활성화해
    server.log 파일이 불필요한 쿼리 로그로 채워지는 것을 방지합니다.

    반환값:
      SQLDatabase 인스턴스 (연결 성공 시) 또는 None (연결 실패 시)
    """
    try:
        uri = _get_database_uri()
        db = SQLDatabase.from_uri(uri, engine_args={"echo": False})
        logger.info("데이터베이스 연결에 성공했습니다.")
        return db
    except Exception as e:
        # 연결 실패 시 None 을 반환해 에이전트 초기화 단계에서
        # 안전하게 처리할 수 있도록 합니다.
        logger.error(f"데이터베이스 연결 실패: {e}")
        return None
