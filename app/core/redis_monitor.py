"""
Redis 실시간 모니터링 모듈

실제 Redis 서버에 연결하여 메트릭 수집, 에러 감지, 장애 분석을 수행합니다.
"""
import redis
import asyncio
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RedisAlert:
    """Redis 알림"""
    timestamp: datetime
    level: AlertLevel
    category: str
    message: str
    metrics: Dict[str, Any]
    raw_info: Optional[str] = None


@dataclass
class MonitorConfig:
    """모니터링 설정"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    interval_seconds: int = 10  # 모니터링 주기
    # 임계값 설정
    memory_warning_percent: float = 80.0
    memory_critical_percent: float = 90.0
    clients_warning: int = 1000
    clients_critical: int = 5000
    rejected_connections_threshold: int = 10
    blocked_clients_threshold: int = 50
    ops_per_sec_low_threshold: int = 100  # 급격한 하락 감지용


@dataclass
class MonitoringState:
    """모니터링 상태"""
    is_running: bool = False
    last_check: Optional[datetime] = None
    last_metrics: Dict[str, Any] = field(default_factory=dict)
    alerts: List[RedisAlert] = field(default_factory=list)
    error_logs: List[str] = field(default_factory=list)
    connection_status: str = "disconnected"


class RedisMonitor:
    """Redis 실시간 모니터"""

    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.state = MonitoringState()
        self._client: Optional[redis.Redis] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._alert_callbacks: List[Callable[[RedisAlert], None]] = []
        self._previous_metrics: Dict[str, Any] = {}

    def connect(self) -> bool:
        """Redis 연결"""
        try:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # 연결 테스트
            self._client.ping()
            self.state.connection_status = "connected"
            logger.info(f"Redis 연결 성공: {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            self.state.connection_status = f"error: {str(e)}"
            logger.error(f"Redis 연결 실패: {str(e)}")
            return False

    def disconnect(self):
        """Redis 연결 해제"""
        if self._client:
            self._client.close()
            self._client = None
        self.state.connection_status = "disconnected"

    def get_info(self) -> Dict[str, Any]:
        """Redis INFO 명령 실행"""
        if not self._client:
            return {}
        try:
            return self._client.info()
        except Exception as e:
            self._add_error_log(f"INFO 명령 실패: {str(e)}")
            return {}

    def get_metrics(self) -> Dict[str, Any]:
        """주요 메트릭 수집"""
        info = self.get_info()
        if not info:
            return {}

        metrics = {
            # Memory
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "used_memory_peak": info.get("used_memory_peak", 0),
            "used_memory_rss": info.get("used_memory_rss", 0),
            "maxmemory": info.get("maxmemory", 0),
            "maxmemory_human": info.get("maxmemory_human", "0B"),
            "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
            "evicted_keys": info.get("evicted_keys", 0),

            # Clients
            "connected_clients": info.get("connected_clients", 0),
            "blocked_clients": info.get("blocked_clients", 0),
            "rejected_connections": info.get("rejected_connections", 0),

            # Stats
            "total_connections_received": info.get("total_connections_received", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),

            # Replication
            "role": info.get("role", "unknown"),
            "connected_slaves": info.get("connected_slaves", 0),
            "master_link_status": info.get("master_link_status", "n/a"),

            # Persistence
            "rdb_last_bgsave_status": info.get("rdb_last_bgsave_status", "ok"),
            "rdb_changes_since_last_save": info.get("rdb_changes_since_last_save", 0),
            "aof_enabled": info.get("aof_enabled", 0),
            "aof_last_bgrewrite_status": info.get("aof_last_bgrewrite_status", "ok"),

            # Server
            "redis_version": info.get("redis_version", "unknown"),
            "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            "uptime_in_days": info.get("uptime_in_days", 0),

            # Cluster (if applicable)
            "cluster_enabled": info.get("cluster_enabled", 0),

            # Timestamp
            "collected_at": datetime.now().isoformat(),
        }

        # 히트율 계산
        hits = metrics["keyspace_hits"]
        misses = metrics["keyspace_misses"]
        if hits + misses > 0:
            metrics["hit_rate"] = round(hits / (hits + misses) * 100, 2)
        else:
            metrics["hit_rate"] = 0

        # 메모리 사용률 계산
        if metrics["maxmemory"] > 0:
            metrics["memory_usage_percent"] = round(
                metrics["used_memory"] / metrics["maxmemory"] * 100, 2
            )
        else:
            metrics["memory_usage_percent"] = 0

        return metrics

    def check_health(self) -> List[RedisAlert]:
        """건강 상태 체크 및 알림 생성"""
        alerts = []
        metrics = self.get_metrics()

        if not metrics:
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                category="connection",
                message="Redis 서버에 연결할 수 없습니다",
                metrics={},
            ))
            return alerts

        # 메모리 체크
        if metrics.get("memory_usage_percent", 0) >= self.config.memory_critical_percent:
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                category="memory",
                message=f"메모리 사용량 위험: {metrics['memory_usage_percent']}% (임계값: {self.config.memory_critical_percent}%)",
                metrics=metrics,
            ))
        elif metrics.get("memory_usage_percent", 0) >= self.config.memory_warning_percent:
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                category="memory",
                message=f"메모리 사용량 경고: {metrics['memory_usage_percent']}% (임계값: {self.config.memory_warning_percent}%)",
                metrics=metrics,
            ))

        # 클라이언트 연결 체크
        connected = metrics.get("connected_clients", 0)
        if connected >= self.config.clients_critical:
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                category="connection",
                message=f"연결 클라이언트 위험: {connected}개 (임계값: {self.config.clients_critical})",
                metrics=metrics,
            ))
        elif connected >= self.config.clients_warning:
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                category="connection",
                message=f"연결 클라이언트 경고: {connected}개 (임계값: {self.config.clients_warning})",
                metrics=metrics,
            ))

        # 거부된 연결 체크
        rejected = metrics.get("rejected_connections", 0)
        prev_rejected = self._previous_metrics.get("rejected_connections", 0)
        if rejected - prev_rejected >= self.config.rejected_connections_threshold:
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                category="connection",
                message=f"연결 거부 발생: {rejected - prev_rejected}건 (총 {rejected}건)",
                metrics=metrics,
            ))

        # 차단된 클라이언트 체크
        blocked = metrics.get("blocked_clients", 0)
        if blocked >= self.config.blocked_clients_threshold:
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                category="connection",
                message=f"차단된 클라이언트: {blocked}개",
                metrics=metrics,
            ))

        # RDB 저장 상태 체크
        if metrics.get("rdb_last_bgsave_status") != "ok":
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                category="persistence",
                message="RDB 스냅샷 저장 실패",
                metrics=metrics,
            ))

        # AOF 상태 체크
        if metrics.get("aof_enabled") and metrics.get("aof_last_bgrewrite_status") != "ok":
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                category="persistence",
                message="AOF rewrite 실패",
                metrics=metrics,
            ))

        # 복제 상태 체크
        if metrics.get("role") == "slave" and metrics.get("master_link_status") == "down":
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                category="replication",
                message="마스터 연결 끊김",
                metrics=metrics,
            ))

        # 메모리 단편화 체크
        frag_ratio = metrics.get("mem_fragmentation_ratio", 1)
        if frag_ratio > 1.5:
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                category="memory",
                message=f"메모리 단편화 비율 높음: {frag_ratio}",
                metrics=metrics,
            ))

        # evicted keys 체크
        evicted = metrics.get("evicted_keys", 0)
        prev_evicted = self._previous_metrics.get("evicted_keys", 0)
        if evicted > prev_evicted:
            alerts.append(RedisAlert(
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                category="memory",
                message=f"키 퇴출 발생: {evicted - prev_evicted}건",
                metrics=metrics,
            ))

        self._previous_metrics = metrics
        return alerts

    def _add_error_log(self, message: str):
        """에러 로그 추가"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        self.state.error_logs.append(log_entry)
        # 최대 100개 유지
        if len(self.state.error_logs) > 100:
            self.state.error_logs = self.state.error_logs[-100:]

    def add_alert_callback(self, callback: Callable[[RedisAlert], None]):
        """알림 콜백 등록"""
        self._alert_callbacks.append(callback)

    def _notify_alert(self, alert: RedisAlert):
        """알림 발송"""
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"알림 콜백 실패: {str(e)}")

    def start_monitoring(self):
        """모니터링 시작"""
        if self.state.is_running:
            logger.warning("모니터링이 이미 실행 중입니다")
            return

        if not self._client:
            if not self.connect():
                return

        self._stop_event.clear()
        self.state.is_running = True

        def monitor_loop():
            while not self._stop_event.is_set():
                try:
                    metrics = self.get_metrics()
                    self.state.last_metrics = metrics
                    self.state.last_check = datetime.now()

                    alerts = self.check_health()
                    for alert in alerts:
                        self.state.alerts.append(alert)
                        self._notify_alert(alert)
                        logger.warning(f"[{alert.level.value.upper()}] {alert.message}")

                    # 최대 100개 알림 유지
                    if len(self.state.alerts) > 100:
                        self.state.alerts = self.state.alerts[-100:]

                except Exception as e:
                    self._add_error_log(f"모니터링 오류: {str(e)}")
                    logger.error(f"모니터링 오류: {str(e)}")

                self._stop_event.wait(self.config.interval_seconds)

            self.state.is_running = False

        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"모니터링 시작 (주기: {self.config.interval_seconds}초)")

    def stop_monitoring(self):
        """모니터링 중지"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.state.is_running = False
        logger.info("모니터링 중지")

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        return {
            "is_running": self.state.is_running,
            "connection_status": self.state.connection_status,
            "last_check": self.state.last_check.isoformat() if self.state.last_check else None,
            "last_metrics": self.state.last_metrics,
            "recent_alerts": [
                {
                    "timestamp": a.timestamp.isoformat(),
                    "level": a.level.value,
                    "category": a.category,
                    "message": a.message,
                }
                for a in self.state.alerts[-10:]
            ],
            "error_logs": self.state.error_logs[-10:],
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "interval_seconds": self.config.interval_seconds,
            },
        }

    def get_alerts_for_analysis(self) -> Dict[str, Any]:
        """분석을 위한 알림 데이터 반환"""
        if not self.state.alerts:
            return None

        # 최근 알림 중 가장 심각한 것 선택
        critical_alerts = [a for a in self.state.alerts if a.level == AlertLevel.CRITICAL]
        if critical_alerts:
            alert = critical_alerts[-1]
        else:
            alert = self.state.alerts[-1]

        return {
            "timestamp": alert.timestamp.isoformat(),
            "error_logs": [alert.message] + self.state.error_logs[-5:],
            "metrics": alert.metrics,
            "redis_version": alert.metrics.get("redis_version", "unknown"),
            "deployment_type": "standalone",  # TODO: 자동 감지
            "description": f"자동 감지된 장애: {alert.message}",
        }


# 싱글톤 인스턴스
_monitor_instance: Optional[RedisMonitor] = None


def get_monitor() -> RedisMonitor:
    """모니터 싱글톤 인스턴스 반환"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = RedisMonitor()
    return _monitor_instance


def reset_monitor():
    """모니터 인스턴스 리셋"""
    global _monitor_instance
    if _monitor_instance:
        _monitor_instance.stop_monitoring()
        _monitor_instance.disconnect()
    _monitor_instance = None
