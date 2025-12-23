"""
Redis AI SRE Assistant - Streamlit UI

장애 분석 및 트러블슈팅 가이드를 위한 웹 인터페이스
"""
import streamlit as st
import httpx
import json
import time
from datetime import datetime
from pathlib import Path

# 설정
API_BASE_URL = "http://localhost:8000"

# 페이지 설정
st.set_page_config(
    page_title="Redis AI SRE Assistant",
    page_icon="🔴",
    layout="wide",
)

# 사이드바
st.sidebar.title("🔴 Redis AI SRE")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "메뉴",
    ["실시간 모니터링", "장애 분석", "지식 검색", "테스트 시나리오", "지식 관리"]
)


def check_api_health():
    """API 서버 상태 확인"""
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


def analyze_incident(incident_data: dict):
    """장애 분석 API 호출"""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/api/v1/analyze",
            json=incident_data,
            timeout=60.0,
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"분석 실패: {response.text}")
            return None
    except Exception as e:
        st.error(f"API 호출 실패: {str(e)}")
        return None


def search_knowledge(query: str, category: str = None, top_k: int = 5):
    """지식 검색 API 호출"""
    try:
        params = {"query": query, "top_k": top_k}
        if category:
            params["category"] = category

        response = httpx.get(
            f"{API_BASE_URL}/api/v1/search/similar",
            params=params,
            timeout=30.0,
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"검색 실패: {response.text}")
            return None
    except Exception as e:
        st.error(f"API 호출 실패: {str(e)}")
        return None


def load_test_scenarios():
    """테스트 시나리오 로드"""
    mock_data_path = Path(__file__).parent.parent / "tests" / "mock_data" / "test_incidents.json"
    try:
        with open(mock_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["scenarios"]
    except Exception as e:
        st.error(f"시나리오 로드 실패: {str(e)}")
        return []


# API 상태 표시
api_status = check_api_health()
if api_status:
    st.sidebar.success("✅ API 서버 연결됨")
else:
    st.sidebar.error("❌ API 서버 연결 실패")
    st.sidebar.info("uvicorn app.main:app --reload --port 8000")

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 사용 방법
1. **실시간 모니터링**: Redis 서버 연결 및 모니터링
2. **장애 분석**: 에러 로그와 메트릭 입력
3. **지식 검색**: 키워드로 트러블슈팅 검색
4. **테스트 시나리오**: 샘플 장애 시나리오 테스트
5. **지식 관리**: 지식 베이스 관리
""")


# ========== 실시간 모니터링 ==========
if menu == "실시간 모니터링":
    st.title("📡 Redis 실시간 모니터링")
    st.markdown("실제 Redis 서버에 연결하여 실시간으로 상태를 모니터링하고 장애를 감지합니다.")

    # 연결 설정
    st.subheader("🔗 Redis 연결 설정")
    conn_col1, conn_col2, conn_col3 = st.columns([2, 1, 1])

    with conn_col1:
        redis_host = st.text_input("Host", value="localhost")
    with conn_col2:
        redis_port = st.number_input("Port", value=6379, min_value=1, max_value=65535)
    with conn_col3:
        redis_password = st.text_input("Password (선택)", type="password")

    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button("🔌 연결", type="primary", disabled=not api_status):
            try:
                response = httpx.post(
                    f"{API_BASE_URL}/api/v1/monitor/connect",
                    json={
                        "host": redis_host,
                        "port": redis_port,
                        "password": redis_password if redis_password else None,
                    },
                    timeout=10.0,
                )
                if response.status_code == 200:
                    st.success("Redis 서버에 연결되었습니다!")
                    st.rerun()
                else:
                    st.error(f"연결 실패: {response.json().get('detail', response.text)}")
            except Exception as e:
                st.error(f"연결 실패: {str(e)}")

    with col_btn2:
        if st.button("🔴 연결 해제"):
            try:
                httpx.post(f"{API_BASE_URL}/api/v1/monitor/disconnect", timeout=5.0)
                st.info("연결이 해제되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    # 모니터링 상태 조회
    monitor_status = None
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v1/monitor/status", timeout=5.0)
        if response.status_code == 200:
            monitor_status = response.json()
    except Exception:
        pass

    st.markdown("---")

    if monitor_status and monitor_status.get("connection_status") == "connected":
        st.success(f"✅ Redis 연결됨: {monitor_status['config']['host']}:{monitor_status['config']['port']}")

        # 모니터링 제어
        st.subheader("⚙️ 모니터링 설정")
        mon_col1, mon_col2 = st.columns(2)

        with mon_col1:
            interval = st.slider("모니터링 주기 (초)", min_value=5, max_value=60, value=10)

        with mon_col2:
            if monitor_status.get("is_running"):
                st.info(f"🟢 모니터링 실행 중 (주기: {monitor_status['config']['interval_seconds']}초)")
                if st.button("⏹️ 모니터링 중지"):
                    httpx.post(f"{API_BASE_URL}/api/v1/monitor/stop", timeout=5.0)
                    st.rerun()
            else:
                st.warning("🔴 모니터링 중지됨")
                if st.button("▶️ 모니터링 시작", type="primary"):
                    httpx.post(
                        f"{API_BASE_URL}/api/v1/monitor/start",
                        json={"interval_seconds": interval},
                        timeout=10.0,
                    )
                    st.rerun()

        st.markdown("---")

        # 실시간 메트릭 표시
        st.subheader("📊 실시간 메트릭")

        # 자동 새로고침 옵션
        auto_refresh = st.checkbox("자동 새로고침 (5초)", value=False)

        if st.button("🔄 새로고침") or auto_refresh:
            try:
                metrics_response = httpx.get(f"{API_BASE_URL}/api/v1/monitor/metrics", timeout=10.0)
                if metrics_response.status_code == 200:
                    metrics = metrics_response.json()

                    # 메트릭 카드
                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

                    with m_col1:
                        memory_pct = metrics.get("memory_usage_percent", 0)
                        st.metric(
                            "메모리 사용률",
                            f"{memory_pct}%",
                            delta=None,
                            delta_color="inverse" if memory_pct > 80 else "normal"
                        )
                        st.caption(f"{metrics.get('used_memory_human', 'N/A')} / {metrics.get('maxmemory_human', 'N/A')}")

                    with m_col2:
                        clients = metrics.get("connected_clients", 0)
                        st.metric("연결 클라이언트", clients)
                        blocked = metrics.get("blocked_clients", 0)
                        if blocked > 0:
                            st.warning(f"차단: {blocked}")

                    with m_col3:
                        ops = metrics.get("instantaneous_ops_per_sec", 0)
                        st.metric("OPS/초", f"{ops:,}")

                    with m_col4:
                        hit_rate = metrics.get("hit_rate", 0)
                        st.metric("히트율", f"{hit_rate}%")

                    # 추가 메트릭
                    st.markdown("---")
                    detail_col1, detail_col2 = st.columns(2)

                    with detail_col1:
                        st.markdown("**서버 정보**")
                        st.text(f"Redis 버전: {metrics.get('redis_version', 'N/A')}")
                        st.text(f"Uptime: {metrics.get('uptime_in_days', 0)}일")
                        st.text(f"Role: {metrics.get('role', 'N/A')}")
                        st.text(f"Fragmentation: {metrics.get('mem_fragmentation_ratio', 0)}")

                    with detail_col2:
                        st.markdown("**영속성 상태**")
                        rdb_status = metrics.get("rdb_last_bgsave_status", "ok")
                        aof_status = metrics.get("aof_last_bgrewrite_status", "ok")
                        st.text(f"RDB 상태: {'✅' if rdb_status == 'ok' else '❌'} {rdb_status}")
                        st.text(f"AOF 상태: {'✅' if aof_status == 'ok' else '❌'} {aof_status}")
                        st.text(f"미저장 변경: {metrics.get('rdb_changes_since_last_save', 0):,}")

                else:
                    st.error("메트릭 수집 실패")
            except Exception as e:
                st.error(f"메트릭 조회 실패: {str(e)}")

        # 자동 새로고침
        if auto_refresh:
            time.sleep(5)
            st.rerun()

        st.markdown("---")

        # 알림 목록
        st.subheader("🚨 최근 알림")
        try:
            alerts_response = httpx.get(f"{API_BASE_URL}/api/v1/monitor/alerts?limit=10", timeout=5.0)
            if alerts_response.status_code == 200:
                alerts_data = alerts_response.json()

                if alerts_data["alerts"]:
                    for alert in alerts_data["alerts"]:
                        level = alert["level"]
                        icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(level, "⚪")
                        st.markdown(f"{icon} **[{alert['timestamp'][:19]}]** [{alert['category']}] {alert['message']}")
                else:
                    st.info("알림이 없습니다.")
        except Exception as e:
            st.error(f"알림 조회 실패: {str(e)}")

        st.markdown("---")

        # AI 분석 버튼
        st.subheader("🤖 AI 장애 분석")
        if st.button("🔍 현재 상태 AI 분석", type="primary"):
            with st.spinner("AI가 현재 상태를 분석하고 있습니다..."):
                try:
                    analysis_response = httpx.post(
                        f"{API_BASE_URL}/api/v1/monitor/analyze",
                        timeout=60.0,
                    )
                    if analysis_response.status_code == 200:
                        result = analysis_response.json()

                        if result["status"] == "healthy":
                            st.success("✅ Redis 서버가 정상 상태입니다!")
                        else:
                            st.warning(f"⚠️ 장애 감지됨!")

                            # 분석 결과 표시
                            severity_color = {
                                "critical": "🔴",
                                "high": "🟠",
                                "medium": "🟡",
                                "low": "🟢",
                            }

                            r_col1, r_col2, r_col3 = st.columns(3)
                            with r_col1:
                                st.metric("심각도", f"{severity_color.get(result.get('severity', ''), '⚪')} {result.get('severity', 'N/A').upper()}")
                            with r_col2:
                                st.metric("카테고리", result.get("category", "N/A"))
                            with r_col3:
                                st.metric("신뢰도", f"{result.get('confidence_score', 0)*100:.0f}%")

                            st.markdown(f"### 📌 요약\n{result.get('summary', '')}")
                            st.markdown(f"### 🔬 근본 원인\n{result.get('root_cause_analysis', '')}")

                            st.markdown("### ⚡ 즉시 조치")
                            for action in result.get("immediate_actions", []):
                                st.markdown(f"- {action}")

                            with st.expander("상세 해결 단계"):
                                for step in result.get("detailed_steps", []):
                                    st.markdown(f"**Step {step.get('step', '?')}**: {step.get('action', '')}")
                                    if step.get("command"):
                                        st.code(step["command"], language="bash")

                    else:
                        st.error(f"분석 실패: {analysis_response.text}")
                except Exception as e:
                    st.error(f"분석 실패: {str(e)}")

        st.markdown("---")

        # 에러 유발 테스트
        st.subheader("🧪 에러 유발 테스트")
        st.warning("⚠️ 테스트 환경에서만 사용하세요!")

        test_col1, test_col2, test_col3, test_col4 = st.columns(4)

        with test_col1:
            mem_size = st.number_input("메모리 (MB)", value=50, min_value=1, max_value=200)
            if st.button("💾 메모리 채우기"):
                with st.spinner("메모리 채우는 중..."):
                    try:
                        resp = httpx.post(
                            f"{API_BASE_URL}/api/v1/monitor/test/fill-memory?size_mb={mem_size}",
                            timeout=60.0,
                        )
                        st.json(resp.json())
                    except Exception as e:
                        st.error(str(e))

        with test_col2:
            conn_count = st.number_input("연결 수", value=50, min_value=1, max_value=200)
            if st.button("🔌 다중 연결"):
                with st.spinner("연결 생성 중..."):
                    try:
                        resp = httpx.post(
                            f"{API_BASE_URL}/api/v1/monitor/test/many-connections?count={conn_count}",
                            timeout=30.0,
                        )
                        st.json(resp.json())
                    except Exception as e:
                        st.error(str(e))

        with test_col3:
            if st.button("🐢 느린 쿼리"):
                with st.spinner("느린 쿼리 실행 중..."):
                    try:
                        resp = httpx.post(
                            f"{API_BASE_URL}/api/v1/monitor/test/slow-query",
                            timeout=60.0,
                        )
                        st.json(resp.json())
                    except Exception as e:
                        st.error(str(e))

        with test_col4:
            if st.button("🧹 테스트 정리"):
                with st.spinner("정리 중..."):
                    try:
                        resp = httpx.post(
                            f"{API_BASE_URL}/api/v1/monitor/test/cleanup",
                            timeout=30.0,
                        )
                        st.json(resp.json())
                    except Exception as e:
                        st.error(str(e))

    else:
        st.info("Redis 서버에 연결해주세요.")


# ========== 장애 분석 ==========
elif menu == "장애 분석":
    st.title("🔍 Redis 장애 분석")
    st.markdown("Redis 장애 상황을 AI가 분석하고 트러블슈팅 가이드를 제공합니다.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📝 장애 정보 입력")

        error_logs = st.text_area(
            "에러 로그 (줄바꿈으로 구분)",
            height=150,
            placeholder="OOM command not allowed when used memory > 'maxmemory'\nCan't save in background: fork: Cannot allocate memory",
        )

        deployment_type = st.selectbox("배포 타입", ["standalone", "sentinel", "cluster"])
        redis_version = st.text_input("Redis 버전", value="7.0.11")
        description = st.text_area(
            "장애 상황 설명",
            placeholder="프로덕션 Redis 서버에서 갑자기 쓰기 요청이 모두 실패하기 시작함...",
        )

    with col2:
        st.subheader("📊 메트릭 정보")

        m_col1, m_col2 = st.columns(2)

        with m_col1:
            used_memory = st.number_input("used_memory (bytes)", value=0, min_value=0)
            maxmemory = st.number_input("maxmemory (bytes)", value=0, min_value=0)
            connected_clients = st.number_input("connected_clients", value=0, min_value=0)
            rejected_connections = st.number_input("rejected_connections", value=0, min_value=0)

        with m_col2:
            blocked_clients = st.number_input("blocked_clients", value=0, min_value=0)
            ops_per_sec = st.number_input("instantaneous_ops_per_sec", value=0, min_value=0)
            master_link_status = st.selectbox("master_link_status", ["up", "down", "N/A"])
            cluster_state = st.selectbox("cluster_state", ["ok", "fail", "N/A"])

    if st.button("🚀 장애 분석 실행", type="primary", disabled=not api_status):
        if not error_logs.strip():
            st.warning("에러 로그를 입력해주세요.")
        else:
            with st.spinner("AI가 장애를 분석하고 있습니다..."):
                incident_data = {
                    "timestamp": datetime.now().isoformat(),
                    "error_logs": [log.strip() for log in error_logs.strip().split("\n") if log.strip()],
                    "metrics": {
                        "used_memory": used_memory if used_memory > 0 else None,
                        "maxmemory": maxmemory if maxmemory > 0 else None,
                        "connected_clients": connected_clients if connected_clients > 0 else None,
                        "blocked_clients": blocked_clients if blocked_clients > 0 else None,
                        "rejected_connections": rejected_connections if rejected_connections > 0 else None,
                        "instantaneous_ops_per_sec": ops_per_sec if ops_per_sec > 0 else None,
                        "master_link_status": master_link_status if master_link_status != "N/A" else None,
                        "cluster_state": cluster_state if cluster_state != "N/A" else None,
                    },
                    "redis_version": redis_version,
                    "deployment_type": deployment_type,
                    "description": description if description else None,
                }

                result = analyze_incident(incident_data)

                if result:
                    st.success("분석이 완료되었습니다!")
                    st.markdown("---")
                    st.subheader("📋 분석 결과")

                    r_col1, r_col2, r_col3 = st.columns(3)
                    with r_col1:
                        severity_color = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                        st.metric("심각도", f"{severity_color.get(result['severity'], '⚪')} {result['severity'].upper()}")
                    with r_col2:
                        st.metric("카테고리", result["category"])
                    with r_col3:
                        st.metric("신뢰도", f"{result['confidence_score']*100:.0f}%")

                    st.markdown(f"### 📌 요약\n{result['summary']}")
                    st.markdown(f"### 🔬 근본 원인 분석\n{result['root_cause_analysis']}")

                    st.markdown("### ⚡ 즉시 조치 사항")
                    for action in result["immediate_actions"]:
                        st.markdown(f"- {action}")

                    st.markdown("### 📝 상세 해결 단계")
                    for step in result["detailed_steps"]:
                        with st.expander(f"Step {step.get('step', '?')}: {step.get('action', '')}"):
                            if step.get("command"):
                                st.code(step["command"], language="bash")
                            if step.get("expected_result"):
                                st.info(f"예상 결과: {step['expected_result']}")

                    st.markdown("### 🛡️ 재발 방지 팁")
                    for tip in result["prevention_tips"]:
                        st.markdown(f"- {tip}")


# ========== 지식 검색 ==========
elif menu == "지식 검색":
    st.title("🔎 지식 검색")
    st.markdown("Redis 트러블슈팅 지식 베이스를 검색합니다.")

    query = st.text_input("검색어", placeholder="OOM memory maxmemory eviction...")

    col1, col2 = st.columns([2, 1])
    with col1:
        category = st.selectbox(
            "카테고리 필터 (선택)",
            ["전체", "memory", "connection", "replication", "cluster", "performance", "persistence", "security"]
        )
    with col2:
        top_k = st.slider("결과 수", min_value=1, max_value=10, value=5)

    if st.button("🔍 검색", type="primary", disabled=not api_status):
        if not query.strip():
            st.warning("검색어를 입력해주세요.")
        else:
            with st.spinner("검색 중..."):
                cat = category if category != "전체" else None
                results = search_knowledge(query, cat, top_k)

                if results and results["documents"]:
                    st.success(f"{results['total_found']}개의 결과를 찾았습니다.")

                    for doc in results["documents"]:
                        metadata = doc.get("metadata", {})
                        with st.expander(f"📄 {metadata.get('title', 'Unknown')} ({metadata.get('category', 'N/A')})"):
                            st.markdown(f"**심각도:** {metadata.get('severity', 'N/A')}")
                            st.markdown(f"**태그:** {metadata.get('tags', 'N/A')}")
                            st.markdown("---")
                            st.text(doc.get("document", "")[:1000] + "...")
                            st.caption(f"유사도 점수: {1 - doc.get('distance', 0):.4f}")
                else:
                    st.info("검색 결과가 없습니다.")


# ========== 테스트 시나리오 ==========
elif menu == "테스트 시나리오":
    st.title("🧪 테스트 시나리오")
    st.markdown("사전 정의된 장애 시나리오로 시스템을 테스트합니다.")

    scenarios = load_test_scenarios()

    if scenarios:
        scenario_options = {f"{s['id']}: {s['name']}": s for s in scenarios}
        selected = st.selectbox("시나리오 선택", list(scenario_options.keys()))

        scenario = scenario_options[selected]

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"### {scenario['name']}")
            st.markdown(f"**설명:** {scenario['description']}")
            st.markdown(f"**심각도:** {scenario['severity'].upper()}")
            st.markdown(f"**예상 카테고리:** {scenario['expected_category']}")

        with col2:
            st.markdown("### 장애 데이터")
            st.json(scenario["incident"])

        if st.button("🚀 이 시나리오로 분석 테스트", type="primary", disabled=not api_status):
            with st.spinner("AI가 장애를 분석하고 있습니다..."):
                result = analyze_incident(scenario["incident"])

                if result:
                    st.success("분석 완료!")
                    st.markdown("---")
                    st.subheader("📊 분석 결과 vs 예상 결과")

                    comp_col1, comp_col2 = st.columns(2)
                    with comp_col1:
                        st.markdown("**분석 결과**")
                        st.metric("카테고리", result["category"])
                        st.metric("심각도", result["severity"])
                    with comp_col2:
                        st.markdown("**예상 결과**")
                        st.metric("카테고리", scenario["expected_category"])
                        st.metric("심각도", scenario["expected_severity"])

                    category_match = result["category"] == scenario["expected_category"]
                    severity_match = result["severity"] == scenario["expected_severity"]

                    if category_match and severity_match:
                        st.success("✅ 분석 결과가 예상과 일치합니다!")
                    else:
                        st.warning("⚠️ 분석 결과가 예상과 다릅니다.")

                    with st.expander("전체 분석 결과 보기"):
                        st.json(result)


# ========== 지식 관리 ==========
elif menu == "지식 관리":
    st.title("📚 지식 관리")
    st.markdown("Redis 트러블슈팅 지식 베이스를 관리합니다.")

    tab1, tab2 = st.tabs(["지식 목록", "지식 추가"])

    with tab1:
        if st.button("🔄 새로고침", disabled=not api_status):
            pass

        if api_status:
            try:
                response = httpx.get(f"{API_BASE_URL}/api/v1/knowledge", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    st.info(f"총 {data['total']}개의 지식이 등록되어 있습니다.")

                    for doc in data["documents"]:
                        metadata = doc.get("metadata", {})
                        with st.expander(f"📄 {metadata.get('title', doc['id'])}"):
                            st.markdown(f"**카테고리:** {metadata.get('category', 'N/A')}")
                            st.markdown(f"**심각도:** {metadata.get('severity', 'N/A')}")
                            st.text(doc.get("document", "")[:500])
                else:
                    st.error("지식 목록 조회 실패")
            except Exception as e:
                st.error(f"API 호출 실패: {str(e)}")

    with tab2:
        st.markdown("새로운 트러블슈팅 지식을 추가합니다.")

        title = st.text_input("제목")
        category = st.selectbox(
            "카테고리",
            ["memory", "connection", "replication", "cluster", "performance", "persistence", "security"]
        )
        severity = st.selectbox("심각도", ["critical", "high", "medium", "low"])

        symptoms = st.text_area("증상 (줄바꿈으로 구분)")
        root_causes = st.text_area("근본 원인 (줄바꿈으로 구분)")
        diagnosis_steps = st.text_area("진단 절차 (줄바꿈으로 구분)")
        solutions = st.text_area("해결 방법 (줄바꿈으로 구분)")
        prevention = st.text_area("예방 조치 (줄바꿈으로 구분)")
        tags = st.text_input("태그 (쉼표로 구분)")

        if st.button("➕ 지식 추가", disabled=not api_status):
            if not all([title, symptoms, solutions]):
                st.warning("제목, 증상, 해결 방법은 필수입니다.")
            else:
                knowledge_data = {
                    "title": title,
                    "category": category,
                    "severity": severity,
                    "symptoms": [s.strip() for s in symptoms.split("\n") if s.strip()],
                    "root_causes": [s.strip() for s in root_causes.split("\n") if s.strip()],
                    "diagnosis_steps": [s.strip() for s in diagnosis_steps.split("\n") if s.strip()],
                    "solutions": [s.strip() for s in solutions.split("\n") if s.strip()],
                    "prevention": [s.strip() for s in prevention.split("\n") if s.strip()],
                    "tags": [t.strip() for t in tags.split(",") if t.strip()],
                }

                try:
                    response = httpx.post(
                        f"{API_BASE_URL}/api/v1/knowledge",
                        json=knowledge_data,
                        timeout=30.0,
                    )
                    if response.status_code == 200:
                        st.success("지식이 추가되었습니다!")
                    else:
                        st.error(f"추가 실패: {response.text}")
                except Exception as e:
                    st.error(f"API 호출 실패: {str(e)}")


# 푸터
st.markdown("---")
st.caption("Redis AI SRE Assistant v0.2.0 | Powered by OpenAI GPT-4 + ChromaDB | 실시간 모니터링 지원")
