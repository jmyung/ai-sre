from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional

from app.models.schemas import SearchQuery, SearchResult
from app.core.rag import RAGEngine

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("", response_model=SearchResult)
async def search_knowledge(query: SearchQuery) -> SearchResult:
    """
    RAG 기반 유사 사례/지식 검색
    """
    try:
        rag_engine = RAGEngine()

        category = query.category.value if query.category else None
        results = rag_engine.search_similar(
            query=query.query,
            top_k=query.top_k,
            category=category,
        )

        return SearchResult(
            documents=results,
            query=query.query,
            total_found=len(results),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")


@router.get("/similar", response_model=SearchResult)
async def search_similar(
    query: str = Query(..., description="검색 쿼리"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    top_k: int = Query(5, ge=1, le=20, description="반환할 결과 수"),
) -> SearchResult:
    """
    유사 장애 검색 (GET 방식)
    """
    try:
        rag_engine = RAGEngine()

        results = rag_engine.search_similar(
            query=query,
            top_k=top_k,
            category=category,
        )

        return SearchResult(
            documents=results,
            query=query,
            total_found=len(results),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")
