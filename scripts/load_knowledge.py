#!/usr/bin/env python3
"""
지식 베이스 로드 스크립트

knowledge/ 디렉토리의 JSON 파일들을 ChromaDB에 임베딩하여 저장합니다.
"""
import sys
import json
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.models.schemas import KnowledgeDocument, Category, Severity
from app.core.rag import RAGEngine


def load_json_knowledge(file_path: Path) -> list:
    """JSON 파일에서 지식 로드"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def convert_to_document(data: dict) -> KnowledgeDocument:
    """딕셔너리를 KnowledgeDocument로 변환"""
    return KnowledgeDocument(
        id=data["id"],
        category=Category(data["category"]),
        title=data["title"],
        symptoms=data.get("symptoms", []),
        root_causes=data.get("root_causes", []),
        diagnosis_steps=data.get("diagnosis_steps", []),
        solutions=data.get("solutions", []),
        prevention=data.get("prevention", []),
        related_metrics=data.get("related_metrics", []),
        severity=Severity(data.get("severity", "medium")),
        tags=data.get("tags", []),
    )


def main():
    print("🚀 지식 베이스 로드 시작...")

    # 지식 디렉토리
    knowledge_dir = project_root / "knowledge" / "troubleshooting"

    if not knowledge_dir.exists():
        print(f"❌ 지식 디렉토리가 없습니다: {knowledge_dir}")
        sys.exit(1)

    # JSON 파일 목록
    json_files = list(knowledge_dir.glob("*.json"))
    print(f"📁 발견된 지식 파일: {len(json_files)}개")

    # RAG 엔진 초기화
    try:
        rag_engine = RAGEngine()
    except Exception as e:
        print(f"❌ RAG 엔진 초기화 실패: {str(e)}")
        print("💡 .env 파일에 OPENAI_API_KEY가 설정되어 있는지 확인하세요.")
        sys.exit(1)

    # 각 파일 처리
    total_loaded = 0
    total_failed = 0

    for json_file in json_files:
        print(f"\n📄 파일 처리 중: {json_file.name}")

        try:
            knowledge_list = load_json_knowledge(json_file)

            for data in knowledge_list:
                try:
                    doc = convert_to_document(data)
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

                    print(f"  ✅ {doc.id}: {doc.title}")
                    total_loaded += 1

                except Exception as e:
                    print(f"  ❌ {data.get('id', 'unknown')}: {str(e)}")
                    total_failed += 1

        except Exception as e:
            print(f"  ❌ 파일 처리 실패: {str(e)}")

    # PersistentClient는 자동 영속화
    print("\n💾 데이터베이스 영속화 완료 (PersistentClient 자동)")

    # 결과 출력
    print("\n" + "=" * 50)
    print(f"📊 로드 결과:")
    print(f"  - 성공: {total_loaded}개")
    print(f"  - 실패: {total_failed}개")
    print(f"  - 총 문서 수: {rag_engine.vector_store.count()}개")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
        print("\n✅ 지식 베이스 로드 완료!")
    except Exception as e:
        print(f"\n❌ 로드 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
