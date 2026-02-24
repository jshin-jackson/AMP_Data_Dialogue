# Data Dialogue

**Data Dialogue** is an Applied Machine Learning Prototype (AMP) for Cloudera AI that enables users to query structured databases using natural language and receive dynamic responses in the form of human-readable summaries, SQL queries, and interactive visualizations.

Non-technical users can interact directly with their data — no SQL skills required.

---

## Business Use Case

Business users and executives often rely heavily on data analysts to extract insights from databases. This adds overhead, slows decisions, and introduces friction in fast-moving environments.

**Data Dialogue** eliminates these delays by:

- Letting users ask questions like *"What were the top 3 customer segments by revenue last month?"*
- Automatically generating and executing SQL queries behind the scenes
- Returning results in natural language, SQL, and interactive chart form

---

## Architecture

```
3_app/
├── app.py                   # Streamlit 메인 앱 (채팅 UI)
├── pages/
│   └── Settings UI.py       # 설정 페이지 (DB / 모델 설정)
└── src/
    ├── config.py            # 환경 변수 로드 및 SETTINGS 딕셔너리
    ├── database.py          # DB 연결 (@st.cache_resource 캐싱)
    ├── agent.py             # LLM + LangChain SQL 에이전트
    └── chart.py             # Vega-Lite 차트 생성
```

### 데이터 흐름

```
사용자 입력 (자연어)
    ↓
agent.py — LangChain SQL Agent
    ↓                    ↓
database.py          chart.py
(SQL 실행)       (Vega-Lite 생성)
    ↓                    ↓
app.py — Response / SQL Query / Chart 탭으로 결과 표시
```

---

## AMP 구성 요소

| 디렉토리 / 파일 | 설명 |
|---|---|
| `0_install-dependencies/` | Python 패키지 설치 및 샘플 SQLite DB 생성 스크립트 |
| `1_job-run-python-job/` | Cloudera AI에서 Streamlit 앱을 실행하는 진입점 |
| `3_app/` | 메인 애플리케이션 (UI, 에이전트, DB 연결, 차트 생성) |
| `assets/` | 샘플 미디어, 이미지 |
| `.project-metadata.yaml` | Cloudera AI AMP 스펙 (런타임, 태스크, 환경변수 정의) |

---

## 기술 스택

| 분류 | 기술 |
|---|---|
| Frontend | Streamlit |
| Database | SQLite (기본), PostgreSQL (로컬 또는 SSH 터널 원격) |
| Agent Orchestration | LangChain (`create_sql_agent`) |
| LLM | OpenAI GPT (모델 선택 가능) |
| Visualization | Vega-Lite / Altair |
| Python | 3.11 이상 |

---

## 환경 변수

### 필수 환경 변수

| 변수명 | 설명 | 기본값 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 | (필수 입력) |
| `OPENAI_BASE_URL` | OpenAI 호환 엔드포인트 URL. 공개 API 사용 시 기본값 유지 | `https://api.openai.com/v1` |
| `DATABASE_URI` | SQLAlchemy DB 접속 URI | `sqlite:///sample_sqlite.db` |

### 선택 환경 변수

| 변수명 | 설명 | 기본값 |
|---|---|---|
| `OPENAI_MODEL_NAME` | 사용할 OpenAI 모델 | `gpt-4o-mini` |
| `IS_REMOTE_DB` | 원격 DB 사용 여부 (`true` / `false`) | `false` |
| `SSH_HOST` | SSH 서버 호스트 (원격 DB 사용 시) | |
| `SSH_PORT` | SSH 포트 | `22` |
| `SSH_USERNAME` | SSH 사용자명 | |
| `SSH_PASSWORD` | SSH 비밀번호 | |
| `DB_HOST` | 원격 DB 내부 호스트 | |
| `DB_PORT` | 원격 DB 포트 | `5432` |
| `DB_NAME` | 원격 DB 이름 | |
| `DB_USER` | 원격 DB 사용자명 | |
| `DB_PASSWORD` | 원격 DB 비밀번호 | |

`3_app/src/.env.sample` 파일을 복사해 `3_app/src/.env` 로 저장한 뒤 값을 입력하세요.

---

## Cloudera AI에서 설치 및 실행

### 1단계: ZIP 파일 준비

GitHub에서 ZIP을 다운로드한 뒤 최상위 디렉토리를 제거하고 재패키징합니다.

```bash
unzip AMP_Data_Dialogue-main.zip
cd AMP_Data_Dialogue-main
zip -r AMP_Data_Dialogue.zip .
```

### 2단계: Cloudera AI Workbench에서 프로젝트 생성

1. Cloudera AI Workbench 접속
2. **New Project** 클릭
3. 프로젝트 이름 입력
4. **Initial Setup** 에서 **AMP** 선택
5. **Upload a zip, tar.gz or tgz file** 선택
6. `AMP_Data_Dialogue.zip` 업로드
7. **Create Project** 클릭

AMP가 자동으로 다음 작업을 순서대로 실행합니다:

| 태스크 | 스크립트 | 설명 |
|---|---|---|
| Install Dependencies | `0_install-dependencies/install-dependencies.py` | Python 패키지 설치 및 샘플 DB 생성 |
| Start Data Dialogue | `1_job-run-python-job/job.py` | Streamlit 앱 실행 |

### 3단계: 환경 변수 설정

Cloudera AI 프로젝트 설정에서 아래 환경 변수를 입력합니다:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (사설 엔드포인트 사용 시)
- `DATABASE_URI` (기본 SQLite 외 다른 DB 사용 시)

---

## 로컬 개발 환경 실행

```bash
# 저장소 클론
git clone https://github.com/jshin-jackson/AMP_Data_Dialogue.git
cd AMP_Data_Dialogue

# Python 가상환경 생성 (Python 3.11 이상 필요)
python3.11 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r 0_install-dependencies/requirements.txt

# 샘플 DB 생성
python 0_install-dependencies/create-sample-db.py

# 환경 변수 설정
cp 3_app/src/.env.sample 3_app/src/.env
# .env 파일을 열어 OPENAI_API_KEY 등 값을 입력

# 앱 실행
cd 3_app
streamlit run app.py
```

---

## 사용 방법

앱이 실행되면 채팅 입력창에 자연어로 질문을 입력합니다.

**예시 질의:**

- `지난달 대출 건수를 지역별로 보여줘`
- `카드 종류별 고객 수를 비교해줘`
- `잔액이 가장 높은 계좌 상위 5개를 알려줘`

### 응답 탭 구성

| 탭 | 설명 |
|---|---|
| **Response** | LLM이 생성한 자연어 요약 (마크다운 형식) |
| **SQL Query** | 실제 실행된 SQL 쿼리 (신택스 하이라이팅) |
| **Chart** | 데이터를 시각화한 인터랙티브 차트 (Vega-Lite) |

### 설정 변경

좌하단 기어 아이콘을 클릭하면 설정 페이지로 이동합니다.

- **Database Settings**: 로컬 / 원격(SSH 터널) DB 전환 및 접속 정보 입력
- **Model Settings**: OpenAI 모델 선택, Temperature, Top P 조정
- **Save Settings**: 변경된 설정을 `.env` 파일에 저장 (앱 재시작 후 적용)

---

## 샘플 데이터

기본 설치 시 금융 도메인 샘플 SQLite 데이터베이스가 생성됩니다.

| 테이블 | 설명 |
|---|---|
| `account` | 계좌 정보 |
| `client` | 고객 정보 |
| `district` | 지역 정보 |
| `card` | 카드 정보 |
| `loan` | 대출 정보 |
| `disposition` | 계좌-고객 관계 |
| `bank_transactions` | 은행 거래 내역 |
| `CRMCallCenterLogs` | 콜센터 로그 |
| `CRMEvents` | CRM 이벤트 |
| `CRMReviews` | 고객 리뷰 |

---

## 라이선스

© 2025 Cloudera, Inc. All Rights Reserved.
