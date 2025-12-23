from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    MEMORY = "memory"
    CONNECTION = "connection"
    REPLICATION = "replication"
    CLUSTER = "cluster"
    PERFORMANCE = "performance"
    PERSISTENCE = "persistence"
    SECURITY = "security"


class DeploymentType(str, Enum):
    STANDALONE = "standalone"
    SENTINEL = "sentinel"
    CLUSTER = "cluster"


# 지식 문서 스키마
class KnowledgeDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: Category
    title: str
    symptoms: List[str] = Field(description="장애 증상")
    root_causes: List[str] = Field(description="근본 원인")
    diagnosis_steps: List[str] = Field(description="진단 절차")
    solutions: List[str] = Field(description="해결 방법")
    prevention: List[str] = Field(description="예방 조치")
    related_metrics: List[str] = Field(default=[], description="관련 메트릭")
    severity: Severity = Severity.MEDIUM
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_text_for_embedding(self) -> str:
        """임베딩을 위한 텍스트 변환"""
        return f"""
제목: {self.title}
카테고리: {self.category.value}
심각도: {self.severity.value}

증상:
{chr(10).join(f'- {s}' for s in self.symptoms)}

근본 원인:
{chr(10).join(f'- {c}' for c in self.root_causes)}

진단 절차:
{chr(10).join(f'{i+1}. {s}' for i, s in enumerate(self.diagnosis_steps))}

해결 방법:
{chr(10).join(f'{i+1}. {s}' for i, s in enumerate(self.solutions))}

예방 조치:
{chr(10).join(f'- {p}' for p in self.prevention)}

태그: {', '.join(self.tags)}
""".strip()


# Redis 메트릭 스키마
class RedisMetrics(BaseModel):
    used_memory: Optional[int] = None
    used_memory_peak: Optional[int] = None
    used_memory_rss: Optional[int] = None
    maxmemory: Optional[int] = None
    connected_clients: Optional[int] = None
    blocked_clients: Optional[int] = None
    total_connections_received: Optional[int] = None
    rejected_connections: Optional[int] = None
    instantaneous_ops_per_sec: Optional[int] = None
    keyspace_hits: Optional[int] = None
    keyspace_misses: Optional[int] = None
    master_link_status: Optional[str] = None
    connected_slaves: Optional[int] = None
    cluster_state: Optional[str] = None
    cluster_slots_ok: Optional[int] = None
    cluster_slots_fail: Optional[int] = None
    rdb_last_bgsave_status: Optional[str] = None
    aof_last_bgrewrite_status: Optional[str] = None
    loading: Optional[int] = None
    rdb_changes_since_last_save: Optional[int] = None


# 장애 입력 스키마
class IncidentInput(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    error_logs: List[str] = Field(description="Redis 에러 로그")
    metrics: Optional[RedisMetrics] = None
    redis_info: Optional[str] = Field(None, description="INFO 명령 결과")
    redis_version: str = "7.0.0"
    deployment_type: DeploymentType = DeploymentType.STANDALONE
    description: Optional[str] = Field(None, description="사용자 설명")

    def to_analysis_prompt(self) -> str:
        """분석을 위한 프롬프트 생성"""
        prompt = f"""
## Redis 장애 상황 분석 요청

### 기본 정보
- 발생 시간: {self.timestamp}
- Redis 버전: {self.redis_version}
- 배포 타입: {self.deployment_type.value}

### 에러 로그
```
{chr(10).join(self.error_logs)}
```
"""
        if self.metrics:
            prompt += f"""
### 메트릭 정보
- used_memory: {self.metrics.used_memory}
- maxmemory: {self.metrics.maxmemory}
- connected_clients: {self.metrics.connected_clients}
- blocked_clients: {self.metrics.blocked_clients}
- rejected_connections: {self.metrics.rejected_connections}
- ops/sec: {self.metrics.instantaneous_ops_per_sec}
- master_link_status: {self.metrics.master_link_status}
- cluster_state: {self.metrics.cluster_state}
"""
        if self.description:
            prompt += f"""
### 사용자 설명
{self.description}
"""
        return prompt


# 분석 결과 스키마
class AnalysisResult(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    severity: Severity
    category: Category
    summary: str = Field(description="장애 요약")
    root_cause_analysis: str = Field(description="근본 원인 분석")
    immediate_actions: List[str] = Field(description="즉시 조치 사항")
    detailed_steps: List[Dict[str, Any]] = Field(description="상세 해결 단계")
    related_cases: List[Dict[str, Any]] = Field(default=[], description="유사 사례")
    prevention_tips: List[str] = Field(description="재발 방지 팁")
    confidence_score: float = Field(ge=0, le=1, description="분석 신뢰도")
    references: List[str] = Field(default=[], description="참조 문서")
    analyzed_at: datetime = Field(default_factory=datetime.now)


# 검색 관련 스키마
class SearchQuery(BaseModel):
    query: str
    category: Optional[Category] = None
    severity: Optional[Severity] = None
    top_k: int = 5


class SearchResult(BaseModel):
    documents: List[Dict[str, Any]]
    query: str
    total_found: int
