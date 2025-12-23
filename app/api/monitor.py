"""
Redis 모니터링 API

실시간 모니터링, 에러 유발, 장애 분석 연동
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.redis_monitor import (
    RedisMonitor,
    MonitorConfig,
    get_monitor,
    reset_monitor,
)
from app.core.rag import RAGEngine
from app.models.schemas import IncidentInput, AnalysisResult, RedisMetrics

router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])


class MonitorConfigRequest(BaseModel):
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    interval_seconds: int = 10
    memory_warning_percent: float = 80.0
    memory_critical_percent: float = 90.0
    clients_warning: int = 1000
    clients_critical: int = 5000


class ConnectionRequest(BaseModel):
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None


# 분석 결과 캐시
analysis_history: List[Dict[str, Any]] = []


@router.post("/connect")
async def connect_redis(request: ConnectionRequest) -> Dict[str, Any]:
    """Redis 서버 연결"""
    monitor = get_monitor()

    # 기존 연결 해제
    if monitor.state.connection_status == "connected":
        monitor.disconnect()

    # 새 설정 적용
    monitor.config.host = request.host
    monitor.config.port = request.port
    monitor.config.password = request.password

    if monitor.connect():
        return {
            "status": "connected",
            "host": request.host,
            "port": request.port,
            "message": "Redis 서버에 연결되었습니다",
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Redis 연결 실패: {monitor.state.connection_status}"
        )


@router.post("/disconnect")
async def disconnect_redis() -> Dict[str, str]:
    """Redis 연결 해제"""
    monitor = get_monitor()
    monitor.stop_monitoring()
    monitor.disconnect()
    return {"status": "disconnected", "message": "연결이 해제되었습니다"}


@router.post("/start")
async def start_monitoring(config: Optional[MonitorConfigRequest] = None) -> Dict[str, Any]:
    """모니터링 시작"""
    monitor = get_monitor()

    if config:
        monitor.config.host = config.host
        monitor.config.port = config.port
        monitor.config.password = config.password
        monitor.config.interval_seconds = config.interval_seconds
        monitor.config.memory_warning_percent = config.memory_warning_percent
        monitor.config.memory_critical_percent = config.memory_critical_percent
        monitor.config.clients_warning = config.clients_warning
        monitor.config.clients_critical = config.clients_critical

    if not monitor._client:
        if not monitor.connect():
            raise HTTPException(status_code=500, detail="Redis 연결 실패")

    monitor.start_monitoring()

    return {
        "status": "started",
        "interval_seconds": monitor.config.interval_seconds,
        "message": f"모니터링이 시작되었습니다 (주기: {monitor.config.interval_seconds}초)",
    }


@router.post("/stop")
async def stop_monitoring() -> Dict[str, str]:
    """모니터링 중지"""
    monitor = get_monitor()
    monitor.stop_monitoring()
    return {"status": "stopped", "message": "모니터링이 중지되었습니다"}


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """모니터링 상태 조회"""
    monitor = get_monitor()
    return monitor.get_status()


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """현재 메트릭 조회"""
    monitor = get_monitor()

    if monitor.state.connection_status != "connected":
        if not monitor.connect():
            raise HTTPException(status_code=500, detail="Redis 연결 실패")

    metrics = monitor.get_metrics()
    if not metrics:
        raise HTTPException(status_code=500, detail="메트릭 수집 실패")

    return metrics


@router.get("/alerts")
async def get_alerts(limit: int = 20) -> Dict[str, Any]:
    """알림 목록 조회"""
    monitor = get_monitor()
    alerts = monitor.state.alerts[-limit:]

    return {
        "total": len(monitor.state.alerts),
        "alerts": [
            {
                "timestamp": a.timestamp.isoformat(),
                "level": a.level.value,
                "category": a.category,
                "message": a.message,
            }
            for a in reversed(alerts)
        ],
    }


@router.post("/analyze")
async def analyze_current_state() -> Dict[str, Any]:
    """현재 상태 분석 (AI 기반)"""
    monitor = get_monitor()

    if monitor.state.connection_status != "connected":
        if not monitor.connect():
            raise HTTPException(status_code=500, detail="Redis 연결 실패")

    # 현재 메트릭 수집
    metrics = monitor.get_metrics()
    if not metrics:
        raise HTTPException(status_code=500, detail="메트릭 수집 실패")

    # 알림 체크
    alerts = monitor.check_health()

    # 알림이 없으면 정상 상태
    if not alerts:
        return {
            "status": "healthy",
            "message": "Redis 서버가 정상 상태입니다",
            "metrics": metrics,
            "analyzed_at": datetime.now().isoformat(),
        }

    # 알림이 있으면 AI 분석 수행
    error_logs = [a.message for a in alerts]
    incident_data = {
        "timestamp": datetime.now().isoformat(),
        "error_logs": error_logs,
        "metrics": {
            "used_memory": metrics.get("used_memory"),
            "maxmemory": metrics.get("maxmemory"),
            "connected_clients": metrics.get("connected_clients"),
            "blocked_clients": metrics.get("blocked_clients"),
            "rejected_connections": metrics.get("rejected_connections"),
            "instantaneous_ops_per_sec": metrics.get("instantaneous_ops_per_sec"),
            "master_link_status": metrics.get("master_link_status"),
        },
        "redis_version": metrics.get("redis_version", "unknown"),
        "deployment_type": "standalone",
        "description": f"자동 감지된 장애 알림 {len(alerts)}건",
    }

    try:
        rag_engine = RAGEngine()
        incident = IncidentInput(**incident_data)
        result = rag_engine.analyze_incident(incident)

        analysis_result = {
            "status": "alert",
            "incident_id": result.incident_id,
            "severity": result.severity.value,
            "category": result.category.value,
            "summary": result.summary,
            "root_cause_analysis": result.root_cause_analysis,
            "immediate_actions": result.immediate_actions,
            "detailed_steps": result.detailed_steps,
            "prevention_tips": result.prevention_tips,
            "confidence_score": result.confidence_score,
            "alerts": [{"level": a.level.value, "message": a.message} for a in alerts],
            "metrics": metrics,
            "analyzed_at": datetime.now().isoformat(),
        }

        # 히스토리 저장
        analysis_history.append(analysis_result)
        if len(analysis_history) > 50:
            analysis_history.pop(0)

        return analysis_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@router.get("/analysis-history")
async def get_analysis_history(limit: int = 10) -> Dict[str, Any]:
    """분석 히스토리 조회"""
    return {
        "total": len(analysis_history),
        "history": analysis_history[-limit:],
    }


# === 에러 유발 테스트 엔드포인트 ===

@router.post("/test/fill-memory")
async def test_fill_memory(size_mb: int = 50) -> Dict[str, Any]:
    """
    메모리 채우기 테스트
    대량의 데이터를 Redis에 저장하여 메모리 압박 유발
    """
    monitor = get_monitor()

    if monitor.state.connection_status != "connected":
        if not monitor.connect():
            raise HTTPException(status_code=500, detail="Redis 연결 실패")

    try:
        import redis
        client = redis.Redis(
            host=monitor.config.host,
            port=monitor.config.port,
            password=monitor.config.password,
        )

        # 1MB 크기의 값 생성
        value = "x" * (1024 * 1024)
        keys_created = 0

        for i in range(size_mb):
            key = f"test:memory:{i}"
            client.set(key, value)
            keys_created += 1

        return {
            "status": "success",
            "message": f"{size_mb}MB 데이터를 저장했습니다",
            "keys_created": keys_created,
        }

    except redis.exceptions.ResponseError as e:
        return {
            "status": "error_triggered",
            "message": f"예상된 에러 발생: {str(e)}",
            "error_type": "OOM" if "OOM" in str(e) else "other",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/many-connections")
async def test_many_connections(count: int = 50) -> Dict[str, Any]:
    """
    다중 연결 테스트
    여러 연결을 생성하여 maxclients 압박 유발
    """
    monitor = get_monitor()

    if monitor.state.connection_status != "connected":
        if not monitor.connect():
            raise HTTPException(status_code=500, detail="Redis 연결 실패")

    try:
        import redis
        connections = []
        successful = 0
        failed = 0

        for i in range(count):
            try:
                client = redis.Redis(
                    host=monitor.config.host,
                    port=monitor.config.port,
                    password=monitor.config.password,
                )
                client.ping()
                connections.append(client)
                successful += 1
            except redis.exceptions.ConnectionError as e:
                failed += 1
                if "max number of clients reached" in str(e):
                    break

        # 연결 유지 (테스트용)
        # 실제로는 connections를 저장해두고 나중에 정리해야 함

        return {
            "status": "success" if failed == 0 else "partial",
            "message": f"연결 {successful}개 성공, {failed}개 실패",
            "successful_connections": successful,
            "failed_connections": failed,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/slow-query")
async def test_slow_query() -> Dict[str, Any]:
    """
    느린 쿼리 테스트
    DEBUG SLEEP 또는 대량 KEYS 명령으로 지연 유발
    """
    monitor = get_monitor()

    if monitor.state.connection_status != "connected":
        if not monitor.connect():
            raise HTTPException(status_code=500, detail="Redis 연결 실패")

    try:
        import redis
        import time

        client = redis.Redis(
            host=monitor.config.host,
            port=monitor.config.port,
            password=monitor.config.password,
        )

        # 대량의 키 생성
        for i in range(10000):
            client.set(f"slowtest:{i}", f"value{i}")

        # KEYS 명령 실행 (느린 쿼리)
        start = time.time()
        keys = client.keys("slowtest:*")
        elapsed = time.time() - start

        return {
            "status": "success",
            "message": f"KEYS 명령 실행 완료",
            "keys_found": len(keys),
            "elapsed_seconds": round(elapsed, 3),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/cleanup")
async def test_cleanup() -> Dict[str, Any]:
    """
    테스트 데이터 정리
    테스트로 생성된 키들 삭제
    """
    monitor = get_monitor()

    if monitor.state.connection_status != "connected":
        if not monitor.connect():
            raise HTTPException(status_code=500, detail="Redis 연결 실패")

    try:
        import redis

        client = redis.Redis(
            host=monitor.config.host,
            port=monitor.config.port,
            password=monitor.config.password,
        )

        # 테스트 키 패턴들
        patterns = ["test:memory:*", "slowtest:*"]
        total_deleted = 0

        for pattern in patterns:
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match=pattern, count=1000)
                if keys:
                    client.delete(*keys)
                    total_deleted += len(keys)
                if cursor == 0:
                    break

        return {
            "status": "success",
            "message": f"테스트 데이터 정리 완료",
            "keys_deleted": total_deleted,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/info")
async def get_redis_info() -> Dict[str, Any]:
    """Redis INFO 전체 조회"""
    monitor = get_monitor()

    if monitor.state.connection_status != "connected":
        if not monitor.connect():
            raise HTTPException(status_code=500, detail="Redis 연결 실패")

    return monitor.get_info()
