from typing import List, Dict, Any, Optional

from app.config import get_settings
from app.core.embeddings import EmbeddingService
from app.core.llm import OpenAIClient
from app.db.vectorstore import VectorStore
from app.models.schemas import IncidentInput, AnalysisResult, Severity, Category


class RAGEngine:
    def __init__(self):
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.llm = OpenAIClient()

    def search_similar(
        self,
        query: str,
        top_k: Optional[int] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """유사 문서 검색"""
        if top_k is None:
            top_k = self.settings.rag_top_k

        # 쿼리 임베딩
        query_embedding = self.embedding_service.embed_text(query)

        # 벡터 검색
        where_filter = None
        if category:
            where_filter = {"category": category}

        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            where=where_filter,
        )

        return results

    def analyze_incident(self, incident: IncidentInput) -> AnalysisResult:
        """장애 분석 실행"""
        # 장애 정보를 기반으로 검색 쿼리 생성
        search_query = self._build_search_query(incident)

        # 유사 문서 검색
        similar_docs = self.search_similar(search_query)

        # 컨텍스트 추출
        context = [doc["document"] for doc in similar_docs]

        # LLM 분석 요청
        incident_prompt = incident.to_analysis_prompt()
        analysis = self.llm.analyze_incident(incident_prompt, context)

        # 결과 구성
        result = AnalysisResult(
            severity=Severity(analysis.get("severity", "medium")),
            category=Category(analysis.get("category", "performance")),
            summary=analysis.get("summary", ""),
            root_cause_analysis=analysis.get("root_cause_analysis", ""),
            immediate_actions=analysis.get("immediate_actions", []),
            detailed_steps=analysis.get("detailed_steps", []),
            prevention_tips=analysis.get("prevention_tips", []),
            confidence_score=analysis.get("confidence_score", 0.5),
            related_cases=[
                {"id": doc.get("id"), "title": doc.get("metadata", {}).get("title", "")}
                for doc in similar_docs[:3]
            ],
        )

        return result

    def _build_search_query(self, incident: IncidentInput) -> str:
        """장애 정보를 기반으로 검색 쿼리 생성"""
        query_parts = []

        # 에러 로그에서 키워드 추출
        if incident.error_logs:
            query_parts.append(" ".join(incident.error_logs[:3]))

        # 메트릭 기반 키워드
        if incident.metrics:
            if incident.metrics.rejected_connections and incident.metrics.rejected_connections > 0:
                query_parts.append("connection rejected max clients")
            if incident.metrics.used_memory and incident.metrics.maxmemory:
                if incident.metrics.used_memory >= incident.metrics.maxmemory * 0.9:
                    query_parts.append("memory full OOM maxmemory")
            if incident.metrics.master_link_status == "down":
                query_parts.append("replication master link down")
            if incident.metrics.cluster_state == "fail":
                query_parts.append("cluster fail node")

        # 사용자 설명
        if incident.description:
            query_parts.append(incident.description)

        return " ".join(query_parts) if query_parts else "redis error troubleshooting"

    def add_knowledge(
        self,
        document_id: str,
        text: str,
        metadata: Dict[str, Any],
    ) -> None:
        """지식 추가"""
        embedding = self.embedding_service.embed_text(text)
        self.vector_store.add(
            document_id=document_id,
            document=text,
            embedding=embedding,
            metadata=metadata,
        )

    def delete_knowledge(self, document_id: str) -> None:
        """지식 삭제"""
        self.vector_store.delete(document_id)
