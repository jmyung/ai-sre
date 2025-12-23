# Redis AI SRE Assistant

AI 기반 Redis 장애 분석 및 트러블슈팅 가이드 시스템 (PoC)

## 개요

Redis 운영 중 발생하는 장애 상황을 OpenAI GPT-4와 RAG(Retrieval-Augmented Generation)를 활용하여 분석하고, 운영자의 노하우가 담긴 트러블슈팅 가이드를 제공합니다. 실제 Redis 서버에 연결하여 실시간 모니터링 및 자동 장애 감지가 가능합니다.

## 주요 기능

- **실시간 모니터링**: 실제 Redis 서버 연결 및 메트릭 수집 (사용자 설정 주기)
- **자동 장애 감지**: 메모리, 연결, 영속성 등 임계값 기반 알림
- **AI 장애 분석**: 에러 로그와 메트릭을 기반으로 GPT-4가 장애 원인 분석
- **RAG 기반 검색**: 축적된 트러블슈팅 지식에서 유사 사례 검색
- **트러블슈팅 가이드**: 즉시 조치 사항과 상세 해결 단계 제공
- **에러 유발 테스트**: OOM, Max Clients 등 장애 시나리오 테스트

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Python 3.11+, FastAPI |
| AI/LLM | OpenAI GPT-4 |
| Embedding | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB (로컬) |
| UI | Streamlit |
| Redis Client | redis-py |
| Container | Docker (Redis 7.2) |

## 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 열고 OPENAI_API_KEY 입력
```

### 2. 데이터베이스 초기화

```bash
# ChromaDB 초기화
python scripts/init_db.py

# 지식 베이스 로드
python scripts/load_knowledge.py
```

### 3. Redis 실행 (Docker)

```bash
# Redis 컨테이너 실행
docker-compose up -d

# 상태 확인
docker ps | grep redis
```

### 4. 서버 실행

```bash
# API 서버 실행 (터미널 1)
uvicorn app.main:app --reload --port 8000

# Streamlit UI 실행 (터미널 2)
streamlit run ui/streamlit_app.py --server.port 8501
```

### 5. 접속

| 서비스 | URL |
|--------|-----|
| Streamlit UI | http://localhost:8501 |
| API 문서 | http://localhost:8000/docs |
| Redis | localhost:6379 |

## 사용 방법

### 실시간 모니터링

1. "실시간 모니터링" 메뉴 선택
2. Redis 연결 정보 입력 (Host, Port)
3. "연결" 버튼 클릭
4. "모니터링 시작" 버튼 클릭
5. 실시간 메트릭 확인 (메모리, 클라이언트, OPS, 히트율)
6. 알림 발생 시 "현재 상태 AI 분석" 클릭

### 에러 유발 테스트

1. "실시간 모니터링" → Redis 연결
2. "에러 유발 테스트" 섹션에서:
   - **메모리 채우기**: 지정 MB 만큼 데이터 저장 → OOM 유발
   - **다중 연결**: maxclients 초과 테스트
   - **느린 쿼리**: KEYS * 명령으로 지연 유발
3. "현재 상태 AI 분석"으로 트러블슈팅 가이드 확인
4. "테스트 정리"로 데이터 삭제

### 수동 장애 분석

1. "장애 분석" 메뉴 선택
2. 에러 로그 입력
3. 메트릭 정보 입력 (선택)
4. "장애 분석 실행" 클릭
5. AI 분석 결과 확인

## 디렉토리 구조

```
ai-sre/
├── app/                          # 애플리케이션 코드
│   ├── api/                      # REST API
│   │   ├── analyze.py            # 장애 분석
│   │   ├── knowledge.py          # 지식 관리
│   │   ├── search.py             # RAG 검색
│   │   └── monitor.py            # 실시간 모니터링
│   ├── core/                     # 핵심 로직
│   │   ├── llm.py                # OpenAI 클라이언트
│   │   ├── rag.py                # RAG 엔진
│   │   └── redis_monitor.py      # Redis 모니터링
│   ├── db/
│   │   └── vectorstore.py        # ChromaDB
│   └── models/
│       └── schemas.py            # Pydantic 스키마
├── knowledge/                    # 지식 베이스
│   └── troubleshooting/          # 트러블슈팅 가이드 (JSON)
├── tests/
│   ├── mock_data/                # 테스트 데이터
│   └── test_scenarios.py         # pytest 테스트
├── ui/
│   └── streamlit_app.py          # Streamlit 대시보드
├── scripts/
│   ├── init_db.py                # DB 초기화
│   └── load_knowledge.py         # 지식 로드
├── docker-compose.yml            # Redis 컨테이너
├── requirements.txt              # Python 의존성
├── .env.example                  # 환경변수 템플릿
├── SPECIFICATION.md              # 상세 명세서
└── REPORT.md                     # 프로젝트 보고서
```

## API 엔드포인트

### 장애 분석
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/analyze` | 장애 분석 실행 |
| GET | `/api/v1/analyze/{id}` | 분석 결과 조회 |

### 지식 관리
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/knowledge` | 지식 추가 |
| GET | `/api/v1/knowledge` | 목록 조회 |
| DELETE | `/api/v1/knowledge/{id}` | 지식 삭제 |

### 검색
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/search` | RAG 검색 |
| GET | `/api/v1/search/similar` | 유사 장애 검색 |

### 모니터링
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/monitor/connect` | Redis 연결 |
| POST | `/api/v1/monitor/start` | 모니터링 시작 |
| POST | `/api/v1/monitor/stop` | 모니터링 중지 |
| GET | `/api/v1/monitor/status` | 상태 조회 |
| GET | `/api/v1/monitor/metrics` | 메트릭 조회 |
| GET | `/api/v1/monitor/alerts` | 알림 목록 |
| POST | `/api/v1/monitor/analyze` | AI 분석 |

## 테스트 시나리오

| ID | 장애 유형 | 심각도 | 설명 |
|----|----------|--------|------|
| SC-001 | OOM | Critical | 메모리 초과 |
| SC-002 | Max Clients | High | 연결 수 초과 |
| SC-003 | Replication Lag | High | 복제 지연 |
| SC-004 | Cluster Node Failure | Critical | 클러스터 노드 장애 |
| SC-005 | Slow Query | Medium | 느린 쿼리 |
| SC-006 | AOF Rewrite Failure | High | AOF 재작성 실패 |
| SC-007 | RDB Save Failure | High | RDB 저장 실패 |
| SC-008 | Connection Timeout | Medium | 연결 타임아웃 |

## 지식 베이스

### 등록된 지식 (10개)

| 카테고리 | 제목 |
|----------|------|
| memory | Redis OOM 장애 대응 |
| memory | 메모리 단편화 문제 해결 |
| connection | Max Clients 초과 장애 대응 |
| connection | 연결 타임아웃 문제 해결 |
| replication | 복제 지연 문제 해결 |
| replication | Full Resync 반복 문제 |
| cluster | Cluster 노드 장애 대응 |
| cluster | MOVED/ASK 리다이렉션 문제 |
| persistence | RDB 스냅샷 저장 실패 해결 |
| persistence | AOF Rewrite 실패 해결 |

### 지식 추가

```json
{
  "id": "kb-custom-001",
  "category": "memory",
  "title": "커스텀 메모리 이슈 해결",
  "symptoms": ["증상 1", "증상 2"],
  "root_causes": ["원인 1", "원인 2"],
  "diagnosis_steps": ["진단 1", "진단 2"],
  "solutions": ["해결 1", "해결 2"],
  "prevention": ["예방 1", "예방 2"],
  "severity": "high",
  "tags": ["memory", "custom"]
}
```

## 테스트

```bash
# 전체 테스트 실행
pytest tests/ -v

# 특정 시나리오 테스트
pytest tests/test_scenarios.py -v -k "SC001"
```

## 서버 종료

```bash
# 프로세스 종료
pkill -f uvicorn
pkill -f streamlit

# Redis 컨테이너 종료
docker-compose down
```

## 문서

- [SPECIFICATION.md](SPECIFICATION.md) - 상세 명세서
- [REPORT.md](REPORT.md) - 프로젝트 보고서

## 라이선스

MIT License
# ai-sre
