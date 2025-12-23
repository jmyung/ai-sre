"""
Redis AI SRE Assistant 테스트 시나리오

이 모듈은 다양한 Redis 장애 시나리오를 테스트합니다.
"""
import pytest
import json
from pathlib import Path
from datetime import datetime

# Mock 데이터 경로
MOCK_DATA_PATH = Path(__file__).parent / "mock_data" / "test_incidents.json"


def load_test_scenarios():
    """테스트 시나리오 로드"""
    with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["scenarios"]


class TestIncidentAnalysis:
    """장애 분석 테스트"""

    @pytest.fixture
    def scenarios(self):
        return load_test_scenarios()

    def test_load_scenarios(self, scenarios):
        """시나리오 로드 테스트"""
        assert len(scenarios) == 8
        assert all("id" in s for s in scenarios)
        assert all("incident" in s for s in scenarios)

    @pytest.mark.parametrize("scenario_id", [
        "SC-001",  # OOM
        "SC-002",  # Max Clients
        "SC-003",  # Replication Lag
        "SC-004",  # Cluster Node Failure
        "SC-005",  # Slow Query
        "SC-006",  # AOF Rewrite Failure
        "SC-007",  # RDB Save Failure
        "SC-008",  # Connection Timeout
    ])
    def test_scenario_structure(self, scenarios, scenario_id):
        """각 시나리오 구조 검증"""
        scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
        assert scenario is not None, f"시나리오 {scenario_id}를 찾을 수 없습니다"

        # 필수 필드 검증
        assert "name" in scenario
        assert "description" in scenario
        assert "severity" in scenario
        assert "incident" in scenario
        assert "expected_category" in scenario

        # incident 구조 검증
        incident = scenario["incident"]
        assert "error_logs" in incident
        assert "metrics" in incident
        assert "redis_version" in incident
        assert "deployment_type" in incident


class TestMockIncidentInput:
    """Mock 장애 입력 테스트"""

    def test_oom_scenario(self):
        """SC-001: OOM 시나리오 테스트"""
        scenarios = load_test_scenarios()
        scenario = next(s for s in scenarios if s["id"] == "SC-001")

        incident = scenario["incident"]

        # OOM 특징 검증
        assert incident["metrics"]["used_memory"] >= incident["metrics"]["maxmemory"]
        assert any("OOM" in log for log in incident["error_logs"])

    def test_max_clients_scenario(self):
        """SC-002: Max Clients 시나리오 테스트"""
        scenarios = load_test_scenarios()
        scenario = next(s for s in scenarios if s["id"] == "SC-002")

        incident = scenario["incident"]

        # Max Clients 특징 검증
        assert incident["metrics"]["connected_clients"] >= 10000
        assert incident["metrics"]["rejected_connections"] > 0
        assert any("max number of clients" in log for log in incident["error_logs"])

    def test_replication_scenario(self):
        """SC-003: 복제 지연 시나리오 테스트"""
        scenarios = load_test_scenarios()
        scenario = next(s for s in scenarios if s["id"] == "SC-003")

        incident = scenario["incident"]

        # Replication 특징 검증
        assert incident["metrics"]["master_link_status"] == "down"
        assert incident["deployment_type"] == "sentinel"

    def test_cluster_failure_scenario(self):
        """SC-004: 클러스터 노드 장애 시나리오 테스트"""
        scenarios = load_test_scenarios()
        scenario = next(s for s in scenarios if s["id"] == "SC-004")

        incident = scenario["incident"]

        # Cluster 특징 검증
        assert incident["metrics"]["cluster_state"] == "fail"
        assert incident["metrics"]["cluster_slots_fail"] > 0
        assert incident["deployment_type"] == "cluster"


class TestAnalysisExpectations:
    """분석 결과 기대값 테스트"""

    @pytest.fixture
    def scenarios(self):
        return load_test_scenarios()

    def test_expected_categories(self, scenarios):
        """예상 카테고리 검증"""
        expected_categories = {
            "SC-001": "memory",
            "SC-002": "connection",
            "SC-003": "replication",
            "SC-004": "cluster",
            "SC-005": "performance",
            "SC-006": "persistence",
            "SC-007": "persistence",
            "SC-008": "connection",
        }

        for scenario in scenarios:
            expected = expected_categories.get(scenario["id"])
            assert scenario["expected_category"] == expected, \
                f"{scenario['id']}의 expected_category가 {expected}이어야 합니다"


# Integration Test (실제 API 호출 시 사용)
class TestIntegration:
    """통합 테스트 (API 서버 필요)"""

    @pytest.mark.skip(reason="API 서버 실행 필요")
    def test_analyze_oom_incident(self):
        """OOM 장애 분석 통합 테스트"""
        import httpx

        scenarios = load_test_scenarios()
        scenario = next(s for s in scenarios if s["id"] == "SC-001")

        response = httpx.post(
            "http://localhost:8000/api/v1/analyze",
            json=scenario["incident"],
        )

        assert response.status_code == 200
        result = response.json()
        assert result["category"] == "memory"
        assert result["severity"] == "critical"

    @pytest.mark.skip(reason="API 서버 실행 필요")
    def test_search_knowledge(self):
        """지식 검색 통합 테스트"""
        import httpx

        response = httpx.get(
            "http://localhost:8000/api/v1/search/similar",
            params={"query": "OOM memory maxmemory", "top_k": 3},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["total_found"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
