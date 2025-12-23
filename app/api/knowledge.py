from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from app.models.schemas import KnowledgeDocument
from app.core.rag import RAGEngine

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("", response_model=Dict[str, str])
async def add_knowledge(document: KnowledgeDocument) -> Dict[str, str]:
    """
    새로운 트러블슈팅 지식 추가
    """
    try:
        rag_engine = RAGEngine()

        # 문서를 텍스트로 변환하여 임베딩
        text = document.to_text_for_embedding()
        metadata = {
            "title": document.title,
            "category": document.category.value,
            "severity": document.severity.value,
            "tags": ",".join(document.tags),
        }

        rag_engine.add_knowledge(
            document_id=document.id,
            text=text,
            metadata=metadata,
        )

        return {"message": "지식이 추가되었습니다", "id": document.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"지식 추가 실패: {str(e)}")


@router.get("", response_model=Dict[str, Any])
async def list_knowledge(
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    지식 목록 조회
    """
    try:
        rag_engine = RAGEngine()
        documents = rag_engine.vector_store.list_all(limit=limit, offset=offset)
        total = rag_engine.vector_store.count()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "documents": documents,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목록 조회 실패: {str(e)}")


@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_knowledge(document_id: str) -> Dict[str, Any]:
    """
    특정 지식 상세 조회
    """
    try:
        rag_engine = RAGEngine()
        document = rag_engine.vector_store.get(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")


@router.delete("/{document_id}", response_model=Dict[str, str])
async def delete_knowledge(document_id: str) -> Dict[str, str]:
    """
    지식 삭제
    """
    try:
        rag_engine = RAGEngine()
        rag_engine.delete_knowledge(document_id)

        return {"message": "지식이 삭제되었습니다", "id": document_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 실패: {str(e)}")


@router.post("/bulk-import", response_model=Dict[str, Any])
async def bulk_import_knowledge(documents: List[KnowledgeDocument]) -> Dict[str, Any]:
    """
    대량 지식 임포트
    """
    try:
        rag_engine = RAGEngine()
        imported = 0
        failed = []

        for doc in documents:
            try:
                text = doc.to_text_for_embedding()
                metadata = {
                    "title": doc.title,
                    "category": doc.category.value,
                    "severity": doc.severity.value,
                    "tags": ",".join(doc.tags),
                }

                rag_engine.add_knowledge(
                    document_id=doc.id,
                    text=text,
                    metadata=metadata,
                )
                imported += 1
            except Exception as e:
                failed.append({"id": doc.id, "error": str(e)})

        return {
            "message": f"{imported}개의 지식이 임포트되었습니다",
            "imported": imported,
            "failed": failed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"임포트 실패: {str(e)}")
