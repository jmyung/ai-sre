# Redis AI SRE Assistant - PoC 명세서

## 1. 프로젝트 개요

### 1.1 목적
Redis 서버 장애 상황을 AI 기반으로 분석하고, 운영자의 트러블슈팅 노하우를 RAG(Retrieval-Augmented Generation)로 활용하여 신속한 장애 대응 가이드를 제공하는 시스템

### 1.2 주요 기능
- Redis 장애 로그/메트릭 분석
- 운영 노하우 기반 트러블슈팅 가이드 제공
- 유사 장애 사례 검색 및 해결책 추천
- 실시간 상태 모니터링 대시보드 (선택)

### 1.3 기술 스택
| 구분 | 기술 |
|------|------|
| Backend | Python 3.11+ |
| AI/LLM | OpenAI API (GPT-4) |
| Vector DB | ChromaDB (로컬) |
| Embedding | OpenAI text-embedding-3-small |
| Web Framework | FastAPI |
| Frontend | Streamlit (간단한 UI) |

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 인터페이스                           │
│                    (Streamlit Dashboard)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Server                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 장애 분석 API │  │ RAG 검색 API │  │ 지식 관리 API │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   OpenAI API     │ │    ChromaDB      │ │  Test Data       │
│   (GPT-4)        │ │   (Vector DB)    │ │  (Mock Redis)    │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 3. 디렉토리 구조

```
ai-sre/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 엔트리포인트
│   ├── config.py               # 환경설정
│   ├── api/
│   │   ├── __init__.py
│   │   ├── analyze.py          # 장애 분석 API
│   │   ├── knowledge.py        # 지식 관리 API
│   │   └── search.py           # RAG 검색 API
│   ├── core/
│   │   ├── __init__.py
│   │   ├── llm.py              # OpenAI 클라이언트
│   │   ├── rag.py              # RAG 엔진
│   │   └── embeddings.py       # 임베딩 처리
│   ├── db/
│   │   ├── __init__.py
│   │   └── vectorstore.py      # ChromaDB 연동
│   └── models/
│       ├── __init__.py
│       └── schemas.py          # Pydantic 모델
├── knowledge/
│   ├── troubleshooting/        # 트러블슈팅 가이드 문서
│   ├── runbooks/               # 운영 런북
│   └── cases/                  # 장애 사례
├── tests/
│   ├── __init__.py
│   ├── test_scenarios.py       # 테스트 시나리오
│   └── mock_data/              # 테스트 데이터
├── data/
│   └── chroma/                 # ChromaDB 저장소
├── ui/
│   └── streamlit_app.py        # Streamlit UI
├── scripts/
│   ├── init_db.py              # DB 초기화
│   └── load_knowledge.py       # 지식 로드
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. 핵심 컴포넌트 상세

### 4.1 RAG 지식 베이스 구조

#### 지식 카테고리
```python
KNOWLEDGE_CATEGORIES = {
    "memory": "메모리 관련 장애",
    "connection": "연결 관련 장애",
    "replication": "복제 관련 장애",
    "cluster": "클러스터 관련 장애",
    "performance": "성능 관련 장애",
    "persistence": "영속성 관련 장애",
    "security": "보안 관련 장애"
}
```

#### 지식 문서 스키마
```python
class KnowledgeDocument(BaseModel):
    id: str
    category: str
    title: str
    symptoms: List[str]           # 증상
    root_causes: List[str]        # 근본 원인
    diagnosis_steps: List[str]    # 진단 절차
    solutions: List[str]          # 해결 방법
    prevention: List[str]         # 예방 조치
    related_metrics: List[str]    # 관련 메트릭
    severity: str                 # critical/high/medium/low
    tags: List[str]
    created_at: datetime
    updated_at: datetime
```

### 4.2 장애 입력 스키마

```python
class IncidentInput(BaseModel):
    timestamp: datetime
    error_logs: List[str]         # Redis 에러 로그
    metrics: Optional[Dict] = {
        "used_memory": int,
        "used_memory_peak": int,
        "connected_clients": int,
        "blocked_clients": int,
        "total_connections_received": int,
        "rejected_connections": int,
        "instantaneous_ops_per_sec": int,
        "keyspace_hits": int,
        "keyspace_misses": int,
        "master_link_status": str,
        "connected_slaves": int,
        "cluster_state": str
    }
    redis_info: Optional[str]     # INFO 명령 결과
    redis_version: str
    deployment_type: str          # standalone/sentinel/cluster
    description: Optional[str]    # 사용자 설명
```

### 4.3 분석 결과 스키마

```python
class AnalysisResult(BaseModel):
    incident_id: str
    severity: str
    category: str
    summary: str                  # 장애 요약
    root_cause_analysis: str      # 근본 원인 분석
    immediate_actions: List[str]  # 즉시 조치 사항
    detailed_steps: List[Dict]    # 상세 해결 단계
    related_cases: List[Dict]     # 유사 사례
    prevention_tips: List[str]    # 재발 방지 팁
    confidence_score: float       # 분석 신뢰도
    references: List[str]         # 참조 문서
```

---

## 5. API 엔드포인트

### 5.1 장애 분석 API

```
POST /api/v1/analyze
- 장애 로그/메트릭을 분석하여 트러블슈팅 가이드 제공

GET /api/v1/analyze/{incident_id}
- 이전 분석 결과 조회
```

### 5.2 지식 관리 API

```
POST /api/v1/knowledge
- 새로운 트러블슈팅 지식 추가

GET /api/v1/knowledge
- 지식 목록 조회

GET /api/v1/knowledge/{id}
- 특정 지식 상세 조회

PUT /api/v1/knowledge/{id}
- 지식 수정

DELETE /api/v1/knowledge/{id}
- 지식 삭제

POST /api/v1/knowledge/bulk-import
- 대량 지식 임포트
```

### 5.3 검색 API

```
POST /api/v1/search
- RAG 기반 유사 사례/지식 검색

GET /api/v1/search/similar?query={query}
- 유사 장애 검색
```

---

## 6. 환경 설정

### 6.1 .env 파일

```env
# OpenAI
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./data/chroma
CHROMA_COLLECTION_NAME=redis_knowledge

# App
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=INFO

# RAG Settings
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7
```

### 6.2 requirements.txt

```
fastapi==0.109.0
uvicorn==0.27.0
openai==1.12.0
chromadb==0.4.22
pydantic==2.6.0
python-dotenv==1.0.0
streamlit==1.31.0
httpx==0.26.0
tiktoken==0.5.2
langchain==0.1.6
langchain-openai==0.0.5
pytest==8.0.0
pytest-asyncio==0.23.4
```

---

## 7. 테스트 시나리오

### 7.1 장애 시나리오 목록

| 시나리오 ID | 장애 유형 | 심각도 | 설명 |
|------------|----------|--------|------|
| SC-001 | OOM (Out of Memory) | Critical | 메모리 초과로 인한 장애 |
| SC-002 | Max Clients | High | 최대 클라이언트 연결 초과 |
| SC-003 | Replication Lag | High | 복제 지연 |
| SC-004 | Cluster Node Failure | Critical | 클러스터 노드 장애 |
| SC-005 | Slow Query | Medium | 느린 쿼리로 인한 성능 저하 |
| SC-006 | AOF Rewrite Failure | High | AOF 재작성 실패 |
| SC-007 | RDB Save Failure | High | RDB 스냅샷 저장 실패 |
| SC-008 | Network Partition | Critical | 네트워크 단절 |

---

## 8. 실행 방법

### 8.1 초기 설정

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력

# 4. DB 초기화 및 지식 로드
python scripts/init_db.py
python scripts/load_knowledge.py
```

### 8.2 서버 실행

```bash
# API 서버 실행
uvicorn app.main:app --reload --port 8000

# Streamlit UI 실행 (별도 터미널)
streamlit run ui/streamlit_app.py
```

### 8.3 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 특정 시나리오 테스트
pytest tests/test_scenarios.py -v -k "SC001"
```

---

## 9. 확장 계획 (향후)

1. **실시간 모니터링 연동**: Prometheus/Grafana 연동
2. **알림 시스템**: Slack/PagerDuty 연동
3. **자동 복구**: 자동화된 복구 스크립트 실행
4. **다중 LLM 지원**: Claude, Gemini 등 추가
5. **팀 협업 기능**: 장애 대응 히스토리 공유
