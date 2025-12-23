from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.models.schemas import IncidentInput, AnalysisResult
from app.core.rag import RAGEngine

router = APIRouter(prefix="/api/v1/analyze", tags=["analyze"])

# 분석 결과 캐시 (PoC용 인메모리)
analysis_cache: Dict[str, AnalysisResult] = {}


@router.post("", response_model=AnalysisResult)
async def analyze_incident(incident: IncidentInput) -> AnalysisResult:
    """
    Redis 장애 분석

    장애 로그와 메트릭을 분석하여 트러블슈팅 가이드를 제공합니다.
    """
    try:
        rag_engine = RAGEngine()
        result = rag_engine.analyze_incident(incident)

        # 결과 캐시
        analysis_cache[result.incident_id] = result

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@router.get("/{incident_id}", response_model=AnalysisResult)
async def get_analysis(incident_id: str) -> AnalysisResult:
    """
    이전 분석 결과 조회
    """
    if incident_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")

    return analysis_cache[incident_id]


@router.get("", response_model=Dict[str, Any])
async def list_analyses() -> Dict[str, Any]:
    """
    모든 분석 결과 목록 조회
    """
    return {
        "total": len(analysis_cache),
        "analyses": [
            {
                "incident_id": k,
                "severity": v.severity,
                "category": v.category,
                "summary": v.summary,
                "analyzed_at": v.analyzed_at,
            }
            for k, v in analysis_cache.items()
        ]
    }
