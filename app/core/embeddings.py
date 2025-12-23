from openai import OpenAI
from typing import List

from app.config import get_settings


class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model

    def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """복수 텍스트 임베딩"""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]
