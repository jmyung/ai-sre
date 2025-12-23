import chromadb
from typing import List, Dict, Any, Optional

from app.config import get_settings


class VectorStore:
    def __init__(self):
        settings = get_settings()

        # ChromaDB 클라이언트 초기화 (새 API - PersistentClient 사용)
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
        )

        # 컬렉션 가져오기 또는 생성
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        document_id: str,
        document: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """문서 추가"""
        self.collection.add(
            ids=[document_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[metadata] if metadata else None,
        )

    def add_batch(
        self,
        document_ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """배치 문서 추가"""
        self.collection.add(
            ids=document_ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """유사 문서 검색"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # 결과 포맷팅
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted_results.append(
                    {
                        "id": doc_id,
                        "document": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    }
                )

        return formatted_results

    def get(self, document_id: str) -> Optional[Dict[str, Any]]:
        """문서 조회"""
        result = self.collection.get(
            ids=[document_id],
            include=["documents", "metadatas"],
        )
        if result["ids"]:
            return {
                "id": result["ids"][0],
                "document": result["documents"][0] if result["documents"] else "",
                "metadata": result["metadatas"][0] if result["metadatas"] else {},
            }
        return None

    def delete(self, document_id: str) -> None:
        """문서 삭제"""
        self.collection.delete(ids=[document_id])

    def count(self) -> int:
        """문서 수 조회"""
        return self.collection.count()

    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """모든 문서 조회"""
        result = self.collection.get(
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"],
        )

        formatted = []
        if result["ids"]:
            for i, doc_id in enumerate(result["ids"]):
                formatted.append(
                    {
                        "id": doc_id,
                        "document": result["documents"][i] if result["documents"] else "",
                        "metadata": result["metadatas"][i] if result["metadatas"] else {},
                    }
                )

        return formatted
