#!/usr/bin/env python3
"""
ChromaDB 초기화 스크립트

벡터 데이터베이스를 초기화하고 기본 설정을 적용합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb


def init_database():
    """데이터베이스 초기화"""
    print("🚀 ChromaDB 초기화 시작...")

    # 저장 디렉토리 생성
    data_dir = project_root / "data" / "chroma"
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 데이터 디렉토리: {data_dir}")

    # ChromaDB 클라이언트 초기화 (새 API)
    client = chromadb.PersistentClient(path=str(data_dir))

    # 컬렉션 생성
    collection_name = "redis_knowledge"
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"✅ 컬렉션 '{collection_name}' 생성/확인 완료")
    print(f"📊 현재 문서 수: {collection.count()}")

    return True


if __name__ == "__main__":
    try:
        init_database()
        print("\n✅ 데이터베이스 초기화 완료!")
    except Exception as e:
        print(f"\n❌ 초기화 실패: {str(e)}")
        sys.exit(1)
