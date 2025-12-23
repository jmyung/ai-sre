from openai import OpenAI
from typing import List, Dict, Any, Optional
import json

from app.config import get_settings


class OpenAIClient:
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def analyze_incident(
        self,
        incident_prompt: str,
        context: List[str],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """장애 상황 분석"""
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()

        # 컨텍스트를 포함한 메시지 구성
        context_text = "\n\n---\n\n".join(context) if context else "관련 사례 없음"

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""다음 Redis 장애 상황을 분석해주세요.

## 참고할 유사 사례 및 지식:
{context_text}

---

{incident_prompt}

## 응답 형식
다음 JSON 형식으로 응답해주세요:
{{
    "severity": "critical|high|medium|low",
    "category": "memory|connection|replication|cluster|performance|persistence|security",
    "summary": "장애 요약 (1-2문장)",
    "root_cause_analysis": "근본 원인 분석 (상세)",
    "immediate_actions": ["즉시 조치 1", "즉시 조치 2", ...],
    "detailed_steps": [
        {{"step": 1, "action": "조치 내용", "command": "실행 명령어(있는 경우)", "expected_result": "예상 결과"}},
        ...
    ],
    "prevention_tips": ["예방 조치 1", "예방 조치 2", ...],
    "confidence_score": 0.0-1.0
}}
""",
            },
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        return result

    def _get_default_system_prompt(self) -> str:
        return """당신은 Redis 전문 SRE 엔지니어입니다.
Redis 장애 상황을 분석하고 트러블슈팅 가이드를 제공합니다.

분석 시 다음 원칙을 따르세요:
1. 에러 로그와 메트릭을 기반으로 정확한 원인을 파악합니다.
2. 제공된 유사 사례와 지식을 참고하여 검증된 해결책을 제시합니다.
3. 즉시 조치 사항과 상세 해결 단계를 명확히 구분합니다.
4. Redis 공식 문서와 베스트 프랙티스를 기반으로 답변합니다.
5. 재발 방지를 위한 예방 조치도 반드시 포함합니다.
6. 확실하지 않은 부분은 confidence_score에 반영합니다.

항상 JSON 형식으로 응답하세요."""

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """일반 채팅"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
