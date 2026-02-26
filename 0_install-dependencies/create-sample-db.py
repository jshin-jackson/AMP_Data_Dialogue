"""
create-sample-db.py
-------------------
샘플 SQLite 데이터베이스를 생성하고 CSV 데이터를 로드하는 초기화 스크립트입니다.

실행 환경에 따라 경로를 자동으로 결정합니다:
  - Cloudera CML/CDSW 환경: /home/cdsw 디렉토리를 기준으로 DB 및 CSV 경로를 설정합니다.
  - 로컬 개발 환경: 이 스크립트가 위치한 디렉토리의 상위(프로젝트 루트)를 기준으로 합니다.

생성되는 테이블 목록:
  district, account, client, disposition, card, loan,
  CRMCallCenterLogs, CRMEvents, CRMReviews, bank_transactions, "order"

SQLite 호환성을 위한 주요 설계 결정:
  - PostgreSQL 의 ENUM 타입은 SQLite 가 지원하지 않으므로
    VARCHAR + CHECK 제약 조건으로 대체합니다.
  - 'transaction' 은 SQLite/SQL 예약어이므로 테이블명을 bank_transactions 으로 변경합니다.
  - 'order' 역시 SQL 예약어이므로 DDL 에서 큰따옴표로 감쌉니다.
  - 모든 테이블에 IF NOT EXISTS 를 적용해 멱등성을 보장합니다
    (이미 존재하면 오류 없이 건너뜁니다).

실행 방법:
  python create-sample-db.py
"""

from langchain_community.utilities import SQLDatabase

import sqlite3
import csv
import os


def load_csv_into_sqlite(db_name, csv_file_path, table_name):
    """
    CSV 파일의 데이터를 지정한 SQLite 테이블에 일괄 삽입합니다.

    처리 흐름:
      1. SQLite DB 에 연결합니다.
      2. CSV 파일을 열고 첫 번째 행(헤더)을 컬럼명으로 사용합니다.
      3. 헤더를 기반으로 parameterized INSERT SQL 을 동적으로 생성합니다.
      4. 컬럼 수가 맞지 않는 손상된 행은 스킵하고 경고를 출력합니다.
      5. executemany 로 유효한 행 전체를 일괄 삽입한 뒤 커밋합니다.

    매개변수:
      db_name (str): SQLite DB 파일 경로
      csv_file_path (str): 로드할 CSV 파일의 절대 경로
      table_name (str): 데이터를 삽입할 대상 테이블 이름

    예외 처리:
      - FileNotFoundError: CSV 파일이 존재하지 않을 때
      - sqlite3.OperationalError: 테이블·컬럼 불일치 등 SQLite 오류 시,
        insert_sql 이 이미 생성된 경우에만 추가 출력
        (헤더 읽기 전 예외 발생 시의 NameError 방지)
      - Exception: 예상치 못한 기타 오류
    """
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader)  # 첫 번째 행을 컬럼명으로 사용

            # 헤더를 바탕으로 INSERT 문을 동적으로 구성합니다.
            # ? 플레이스홀더(parameterized query)를 사용해 SQL 인젝션을 방지합니다.
            columns = ", ".join(header)
            placeholders = ", ".join("?" * len(header))
            insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

            # CSV 전체를 메모리에 올린 뒤 executemany 로 한 번에 삽입합니다.
            # 행별 execute 보다 훨씬 빠르고 트랜잭션 오버헤드를 줄입니다.
            data_to_insert = []
            for row in csv_reader:
                # 헤더와 컬럼 수가 다른 손상된 행은 삽입하지 않고 경고를 출력합니다.
                if len(row) == len(header):
                    data_to_insert.append(row)
                else:
                    print(f"Skipping malformed row: {row} (Column count mismatch)")

            cursor.executemany(insert_sql, data_to_insert)
            conn.commit()
            print(f"Successfully loaded data from '{csv_file_path}' into table '{table_name}'.")

    except FileNotFoundError:
        print(f"Error: CSV file not found at '{csv_file_path}'.")
    except sqlite3.OperationalError as e:
        print(f"SQLite Operational Error (e.g., table not found, column mismatch): {e}")
        # insert_sql 은 파일 오픈 및 헤더 읽기에 성공해야 생성됩니다.
        # 그 이전 단계에서 예외가 발생하면 변수가 존재하지 않으므로
        # locals() 로 안전하게 존재 여부를 확인합니다.
        if 'insert_sql' in locals():
            print(f"Attempted SQL: {insert_sql}")
    except Exception as e:
        print(f"An unexpected error occurred during data loading: {e}")
    finally:
        # 예외 발생 여부와 무관하게 DB 연결을 반드시 닫습니다.
        if conn:
            conn.close()


def create_sqlite_database(db_name="sample_sqlite.db"):
    """
    샘플 뱅킹 데이터를 위한 SQLite 데이터베이스 스키마를 생성합니다.

    SQLite 호환성을 위한 주요 변경 사항:
      - PostgreSQL ENUM 타입 → VARCHAR + CHECK 제약 조건
        (SQLite 는 ENUM 네이티브 타입을 지원하지 않습니다)
      - 예약어 테이블명 처리:
          'transaction' → bank_transactions (이름 변경)
          'order'       → 큰따옴표로 감싸서 사용 ("order")
      - SERIAL → INTEGER PRIMARY KEY AUTOINCREMENT (SQLite 문법)
      - 모든 테이블에 IF NOT EXISTS 적용 (멱등성 보장)

    매개변수:
      db_name (str): 생성할 SQLite DB 파일의 절대 경로
                     (기본값: 'sample_sqlite.db')
    """
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # ── SQLite 호환 DDL ──────────────────────────────────────────────────
        # PostgreSQL ENUM → VARCHAR + CHECK 제약으로 변환

        # 지역 정보 테이블: district_id 를 PK 로 사용하며
        # account, client 등 다른 테이블에서 외래 키로 참조합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS district (
                district_id INTEGER NOT NULL PRIMARY KEY,
                city        VARCHAR(50) NOT NULL,
                state_name  VARCHAR(50) NOT NULL,
                state_abbrev VARCHAR(50) NOT NULL,
                region      VARCHAR(50) NOT NULL,
                division    VARCHAR(50) NOT NULL
            );
        """)

        # 계좌 테이블: frequency 컬럼은 ENUM 대신 CHECK 제약으로 허용값을 제한합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account (
                account_id  VARCHAR NOT NULL,
                district_id INTEGER NOT NULL,
                frequency   VARCHAR NOT NULL CHECK(frequency IN (
                                'Issuance After Transaction',
                                'Monthly Issuance',
                                'Weekly Issuance'
                            )),
                date        TEXT NOT NULL
            );
        """)

        # 고객 정보 테이블: 이름·주소·연락처·인구통계 정보를 포함합니다.
        # middle, address_2 는 선택적(NULL 허용) 컬럼입니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client (
                client_id   VARCHAR NOT NULL PRIMARY KEY,
                sex         VARCHAR NOT NULL,
                fulldate    TEXT NOT NULL,
                day         INTEGER NOT NULL,
                month       INTEGER NOT NULL,
                year        INTEGER NOT NULL,
                age         INTEGER NOT NULL,
                social      VARCHAR NOT NULL,
                first       VARCHAR NOT NULL,
                middle      VARCHAR NULL,
                last        VARCHAR NOT NULL,
                phone       INTEGER NOT NULL,
                email       VARCHAR NOT NULL,
                address_1   VARCHAR NOT NULL,
                address_2   VARCHAR NULL,
                city        VARCHAR NOT NULL,
                state       VARCHAR NOT NULL,
                zipcode     VARCHAR NOT NULL,
                district_id INTEGER NOT NULL
            );
        """)

        # 처분(disposition) 테이블: 고객과 계좌 간의 관계(소유·공동소유 등)를 기록합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disposition (
                disp_id    VARCHAR(10) NOT NULL PRIMARY KEY,
                client_id  VARCHAR(10) NOT NULL,
                account_id VARCHAR(10) NULL,
                disp_type  VARCHAR(50) NULL
            );
        """)

        # 카드 테이블: card_type 은 ENUM 대신 CHECK 제약으로 허용 카드 종류를 제한합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card (
                card_id   VARCHAR(50) NOT NULL PRIMARY KEY,
                disp_id   VARCHAR(50) NOT NULL,
                card_type VARCHAR NOT NULL CHECK(card_type IN (
                              'VISA Signature',
                              'VISA Standard',
                              'VISA Infinite'
                          )),
                year      INTEGER NOT NULL,
                month     INTEGER NOT NULL,
                day       INTEGER NOT NULL,
                fulldate  TEXT NOT NULL
            );
        """)

        # 대출 테이블: 대출 금액·기간·납입액·상태·목적을 기록합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan (
                loan_id    VARCHAR(50) NOT NULL,
                account_id VARCHAR(50) NOT NULL,
                amount     INTEGER NOT NULL,
                duration   INTEGER NOT NULL,
                payments   INTEGER NOT NULL,
                status     VARCHAR(50) NOT NULL,
                year       INTEGER NOT NULL,
                month      INTEGER NOT NULL,
                day        INTEGER NOT NULL,
                fulldate   TEXT NOT NULL,
                location   INTEGER NOT NULL,
                purpose    VARCHAR(50) NOT NULL
            );
        """)

        # 콜센터 로그 테이블: 고객 민원 접수·처리 이력을 기록합니다.
        # call_id, priority 등은 데이터 누락 가능성이 있어 NULL 을 허용합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CRMCallCenterLogs (
                Date_received  VARCHAR(50) NOT NULL,
                Complaint_ID   VARCHAR(50) NOT NULL,
                rand_client    VARCHAR(50) NULL,
                phonefinal     VARCHAR(50) NULL,
                vru_line       VARCHAR(50) NULL,
                call_id        INTEGER NULL,
                priority       INTEGER NULL,
                complaint_type VARCHAR(50) NULL,
                outcome        VARCHAR(50) NULL,
                server         VARCHAR(50) NULL,
                ser_start      VARCHAR(50) NOT NULL,
                ser_exit       VARCHAR(50) NOT NULL,
                ser_time       VARCHAR(50) NOT NULL
            );
        """)

        # 이체 주문 테이블: 'order' 는 SQL 예약어이므로 큰따옴표로 이름을 감쌉니다.
        # account_id 에 CASCADE 외래 키를 설정해 계좌 삭제 시 연계 주문도 삭제합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "order" (
                order_id   INTEGER NOT NULL PRIMARY KEY,
                account_id VARCHAR(50) NOT NULL,
                bank_to    VARCHAR(50) NOT NULL,
                account_to INTEGER NOT NULL,
                amount     INTEGER NOT NULL,
                k_symbol   VARCHAR(50) NULL,
                FOREIGN KEY (account_id) REFERENCES account(account_id) ON DELETE CASCADE
            );
        """)

        # CRM 이벤트 테이블: 소비자 민원 상세 정보를 기록합니다.
        # Consumer_complaint_narrative 는 최대 20,000자의 자유 텍스트 컬럼입니다.
        # createdAt / updatedAt 은 CURRENT_TIMESTAMP 기본값을 사용합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CRMEvents (
                Date_received                TEXT NOT NULL,
                Product                      VARCHAR(50) NOT NULL,
                Sub_product                  VARCHAR(50) NULL,
                Issue                        VARCHAR(50) NOT NULL,
                Sub_issue                    VARCHAR(50) NOT NULL,
                Consumer_complaint_narrative VARCHAR(20000) NULL,
                Tags                         VARCHAR(50) NULL,
                Consumer_consent_provided    VARCHAR(50) NULL,
                Submitted_via                VARCHAR(50) NULL,
                Date_sent_to_company         VARCHAR(50) NULL,
                Company_response_to_consumer VARCHAR(50) NULL,
                Timely_response              VARCHAR(50) NULL,
                Consumer_disputed            VARCHAR(50) NULL,
                Complaint_ID                 VARCHAR(50) NOT NULL PRIMARY KEY,
                Client_ID                    VARCHAR(50) NULL,
                createdAt                    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatedAt                    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # CRM 리뷰 테이블: 고객 제품 평점 및 리뷰를 기록합니다.
        # reviewId 는 SQLite AUTOINCREMENT 로 자동 증가합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CRMReviews (
                reviewId    INTEGER PRIMARY KEY AUTOINCREMENT,
                Date        TEXT NOT NULL,
                Stars       INTEGER NOT NULL,
                Reviews     VARCHAR NULL,
                Product     VARCHAR(50) NOT NULL,
                district_id INTEGER NOT NULL
            );
        """)

        # 은행 거래 테이블: 'transaction' 이 SQLite 예약어이므로 bank_transactions 으로 명명합니다.
        # k_symbol, bank, account, date, fulldatewithtime 은 데이터 누락 가능성이 있어 NULL 허용입니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bank_transactions (
                trans_id         VARCHAR(50) NOT NULL PRIMARY KEY,
                account_id       VARCHAR(50) NOT NULL,
                transaction_type VARCHAR(50) NOT NULL,
                operation        VARCHAR(50) NULL,
                amount           INTEGER NOT NULL,
                balance          INTEGER NOT NULL,
                k_symbol         VARCHAR(50) NULL,
                bank             VARCHAR(50) NULL,
                account          VARCHAR(50) NULL,
                date             TEXT NULL,
                fulldatewithtime VARCHAR(50) NULL
            );
        """)

        conn.commit()
        print(f"Database '{db_name}' and tables created successfully with updated naming conventions.")

    except sqlite3.Error as e:
        print(f"An error occurred during database creation: {e}")
    finally:
        # 예외 발생 여부와 무관하게 DB 연결을 반드시 닫습니다.
        if conn:
            conn.close()


# ── 실행 환경 감지 및 경로 설정 ──────────────────────────────────────────────
# /home/cdsw 디렉토리가 존재하면 Cloudera CML/CDSW 환경으로 판단합니다.
# 존재하지 않으면 이 스크립트의 상위 디렉토리(프로젝트 루트)를 기준으로 경로를 계산합니다.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))   # 0_install-dependencies/
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)               # 프로젝트 루트
BASE_DIR = "/home/cdsw" if os.path.exists("/home/cdsw") else _PROJECT_ROOT

# DB 파일 경로: BASE_DIR/sample_sqlite.db
db = os.path.join(BASE_DIR, "sample_sqlite.db")

# CSV 파일 디렉토리: BASE_DIR/0_install-dependencies/sample_data_csv/
CSV_DIR = os.path.join(BASE_DIR, "0_install-dependencies", "sample_data_csv")

# 기존 DB 파일이 있으면 삭제하고 새로 생성합니다 (초기화 스크립트이므로 항상 재생성).
if os.path.exists(db):
    os.remove(db)

# ── 스키마 생성 ───────────────────────────────────────────────────────────────
create_sqlite_database(db)

# ── CSV 데이터 로드 ───────────────────────────────────────────────────────────
# 파일 번호 순서대로 로드합니다. 01·03 이 모두 account 테이블인 것은 의도된 설계입니다
# (01: 기본 계좌 데이터, 03: 추가 계좌 데이터를 같은 테이블에 병합).
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "01_account.csv"),        "account")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "02_district.csv"),       "district")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "03_account.csv"),        "account")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "04_card.csv"),           "card")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "05_client.csv"),         "client")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "06_crmcallcentrelog.csv"), "CRMCallCenterLogs")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "07_crmevents.csv"),      "CRMEvents")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "08_crmreviews.csv"),     "CRMReviews")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "09_disposition.csv"),    "disposition")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "10_loan.csv"),           "loan")
load_csv_into_sqlite(db, os.path.join(CSV_DIR, "11_transaction.csv"),    "bank_transactions")
