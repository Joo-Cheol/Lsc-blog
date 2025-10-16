#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모니터링 대시보드
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DashboardData:
    """대시보드 데이터"""
    timestamp: str
    system_health: Dict[str, Any]
    application_stats: Dict[str, Any]
    llm_status: Dict[str, Any]
    active_alerts: List[Dict[str, Any]]
    recent_metrics: Dict[str, Any]


class MonitoringDashboard:
    """모니터링 대시보드"""
    
    def __init__(self, metrics_db: str = "monitoring/metrics.db", 
                 alerts_db: str = "monitoring/alerts.db"):
        self.metrics_db = metrics_db
        self.alerts_db = alerts_db
    
    def get_dashboard_data(self, hours: int = 24) -> DashboardData:
        """대시보드 데이터 조회"""
        try:
            # 시스템 상태
            system_health = self._get_system_health(hours)
            
            # 애플리케이션 통계
            application_stats = self._get_application_stats(hours)
            
            # LLM 상태
            llm_status = self._get_llm_status()
            
            # 활성 알림
            active_alerts = self._get_active_alerts(hours)
            
            # 최근 메트릭
            recent_metrics = self._get_recent_metrics(hours)
            
            return DashboardData(
                timestamp=datetime.now().isoformat(),
                system_health=system_health,
                application_stats=application_stats,
                llm_status=llm_status,
                active_alerts=active_alerts,
                recent_metrics=recent_metrics
            )
            
        except Exception as e:
            logger.error(f"대시보드 데이터 조회 실패: {e}")
            return DashboardData(
                timestamp=datetime.now().isoformat(),
                system_health={},
                application_stats={},
                llm_status={},
                active_alerts=[],
                recent_metrics={}
            )
    
    def _get_system_health(self, hours: int) -> Dict[str, Any]:
        """시스템 상태 조회"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            since_str = since.isoformat()
            
            conn = sqlite3.connect(self.metrics_db)
            
            # 최근 시스템 메트릭
            latest = conn.execute("""
                SELECT cpu_percent, memory_percent, disk_usage_percent, 
                       memory_used_mb, memory_total_mb, disk_free_gb
                FROM system_metrics 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (since_str,)).fetchone()
            
            # 평균값들
            averages = conn.execute("""
                SELECT 
                    AVG(cpu_percent) as avg_cpu,
                    AVG(memory_percent) as avg_memory,
                    AVG(disk_usage_percent) as avg_disk,
                    MAX(cpu_percent) as max_cpu,
                    MAX(memory_percent) as max_memory,
                    MAX(disk_usage_percent) as max_disk
                FROM system_metrics 
                WHERE timestamp >= ?
            """, (since_str,)).fetchone()
            
            conn.close()
            
            if latest:
                return {
                    "current": {
                        "cpu_percent": latest[0] or 0,
                        "memory_percent": latest[1] or 0,
                        "disk_usage_percent": latest[2] or 0,
                        "memory_used_mb": latest[3] or 0,
                        "memory_total_mb": latest[4] or 0,
                        "disk_free_gb": latest[5] or 0
                    },
                    "averages": {
                        "avg_cpu_percent": averages[0] or 0,
                        "avg_memory_percent": averages[1] or 0,
                        "avg_disk_percent": averages[2] or 0,
                        "max_cpu_percent": averages[3] or 0,
                        "max_memory_percent": averages[4] or 0,
                        "max_disk_percent": averages[5] or 0
                    },
                    "status": self._get_system_status(latest[0], latest[1], latest[2])
                }
            else:
                return {
                    "current": {},
                    "averages": {},
                    "status": "unknown"
                }
                
        except Exception as e:
            logger.error(f"시스템 상태 조회 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_system_status(self, cpu: float, memory: float, disk: float) -> str:
        """시스템 상태 판정"""
        if cpu > 90 or memory > 95 or disk > 95:
            return "critical"
        elif cpu > 80 or memory > 85 or disk > 90:
            return "warning"
        elif cpu > 60 or memory > 70 or disk > 80:
            return "degraded"
        else:
            return "healthy"
    
    def _get_application_stats(self, hours: int) -> Dict[str, Any]:
        """애플리케이션 통계 조회"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            since_str = since.isoformat()
            
            conn = sqlite3.connect(self.metrics_db)
            
            # 최근 애플리케이션 메트릭
            latest = conn.execute("""
                SELECT total_requests, successful_requests, failed_requests,
                       avg_response_time_ms, total_posts, total_chunks,
                       total_searches, total_generations
                FROM application_metrics 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (since_str,)).fetchone()
            
            # 합계들
            totals = conn.execute("""
                SELECT 
                    SUM(total_requests) as total_requests,
                    SUM(successful_requests) as successful_requests,
                    SUM(failed_requests) as failed_requests,
                    AVG(avg_response_time_ms) as avg_response_time,
                    MAX(total_posts) as total_posts,
                    MAX(total_chunks) as total_chunks,
                    SUM(total_searches) as total_searches,
                    SUM(total_generations) as total_generations
                FROM application_metrics 
                WHERE timestamp >= ?
            """, (since_str,)).fetchone()
            
            conn.close()
            
            if latest and totals:
                total_requests = totals[0] or 0
                successful_requests = totals[1] or 0
                failed_requests = totals[2] or 0
                
                success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
                error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
                
                return {
                    "current": {
                        "total_requests": latest[0] or 0,
                        "successful_requests": latest[1] or 0,
                        "failed_requests": latest[2] or 0,
                        "avg_response_time_ms": latest[3] or 0,
                        "total_posts": latest[4] or 0,
                        "total_chunks": latest[5] or 0,
                        "total_searches": latest[6] or 0,
                        "total_generations": latest[7] or 0
                    },
                    "totals": {
                        "total_requests": total_requests,
                        "successful_requests": successful_requests,
                        "failed_requests": failed_requests,
                        "avg_response_time_ms": totals[3] or 0,
                        "total_posts": totals[4] or 0,
                        "total_chunks": totals[5] or 0,
                        "total_searches": totals[6] or 0,
                        "total_generations": totals[7] or 0
                    },
                    "rates": {
                        "success_rate": success_rate,
                        "error_rate": error_rate
                    },
                    "status": self._get_application_status(success_rate, error_rate, totals[3] or 0)
                }
            else:
                return {
                    "current": {},
                    "totals": {},
                    "rates": {},
                    "status": "unknown"
                }
                
        except Exception as e:
            logger.error(f"애플리케이션 통계 조회 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_application_status(self, success_rate: float, error_rate: float, response_time: float) -> str:
        """애플리케이션 상태 판정"""
        if error_rate > 20 or response_time > 10000:
            return "critical"
        elif error_rate > 10 or response_time > 5000:
            return "warning"
        elif success_rate < 95 or response_time > 2000:
            return "degraded"
        else:
            return "healthy"
    
    def _get_llm_status(self) -> Dict[str, Any]:
        """LLM 상태 조회"""
        try:
            from src.llm.provider_manager import get_provider_manager
            
            manager = get_provider_manager()
            providers = manager.list_providers()
            
            provider_status = {}
            total_providers = len(providers)
            available_providers = 0
            
            for name, info in providers.items():
                available = info.get("available", False)
                if available:
                    available_providers += 1
                
                provider_status[name] = {
                    "available": available,
                    "model_name": info.get("model_name", "unknown"),
                    "error": info.get("error")
                }
            
            availability_rate = (available_providers / total_providers * 100) if total_providers > 0 else 0
            
            return {
                "providers": provider_status,
                "total_providers": total_providers,
                "available_providers": available_providers,
                "availability_rate": availability_rate,
                "status": self._get_llm_status_level(availability_rate)
            }
            
        except Exception as e:
            logger.error(f"LLM 상태 조회 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_llm_status_level(self, availability_rate: float) -> str:
        """LLM 상태 레벨 판정"""
        if availability_rate == 0:
            return "critical"
        elif availability_rate < 50:
            return "warning"
        elif availability_rate < 100:
            return "degraded"
        else:
            return "healthy"
    
    def _get_active_alerts(self, hours: int) -> List[Dict[str, Any]]:
        """활성 알림 조회"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            since_str = since.isoformat()
            
            conn = sqlite3.connect(self.alerts_db)
            rows = conn.execute("""
                SELECT id, rule_name, severity, message, metric_value, threshold,
                       timestamp, resolved
                FROM alerts 
                WHERE timestamp >= ? AND resolved = 0
                ORDER BY timestamp DESC
                LIMIT 10
            """, (since_str,)).fetchall()
            conn.close()
            
            alerts = []
            for row in rows:
                alerts.append({
                    "id": row[0],
                    "rule_name": row[1],
                    "severity": row[2],
                    "message": row[3],
                    "metric_value": row[4],
                    "threshold": row[5],
                    "timestamp": row[6],
                    "resolved": bool(row[7])
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"활성 알림 조회 실패: {e}")
            return []
    
    def _get_recent_metrics(self, hours: int) -> Dict[str, Any]:
        """최근 메트릭 조회"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            since_str = since.isoformat()
            
            conn = sqlite3.connect(self.metrics_db)
            
            # 최근 시스템 메트릭 (시간순)
            system_metrics = conn.execute("""
                SELECT timestamp, cpu_percent, memory_percent, disk_usage_percent
                FROM system_metrics 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (since_str,)).fetchall()
            
            # 최근 애플리케이션 메트릭
            app_metrics = conn.execute("""
                SELECT timestamp, total_requests, avg_response_time_ms
                FROM application_metrics 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (since_str,)).fetchall()
            
            conn.close()
            
            return {
                "system": [
                    {
                        "timestamp": row[0],
                        "cpu_percent": row[1],
                        "memory_percent": row[2],
                        "disk_usage_percent": row[3]
                    }
                    for row in system_metrics
                ],
                "application": [
                    {
                        "timestamp": row[0],
                        "total_requests": row[1],
                        "avg_response_time_ms": row[2]
                    }
                    for row in app_metrics
                ]
            }
            
        except Exception as e:
            logger.error(f"최근 메트릭 조회 실패: {e}")
            return {}
    
    def get_health_summary(self) -> Dict[str, Any]:
        """헬스 요약 조회"""
        try:
            dashboard_data = self.get_dashboard_data(1)  # 최근 1시간
            
            # 전체 상태 판정
            system_status = dashboard_data.system_health.get("status", "unknown")
            app_status = dashboard_data.application_stats.get("status", "unknown")
            llm_status = dashboard_data.llm_status.get("status", "unknown")
            
            # 최고 우선순위 상태 선택
            status_priority = {
                "critical": 4,
                "warning": 3,
                "degraded": 2,
                "healthy": 1,
                "unknown": 0,
                "error": 5
            }
            
            overall_status = max([system_status, app_status, llm_status], 
                               key=lambda x: status_priority.get(x, 0))
            
            return {
                "overall_status": overall_status,
                "system_status": system_status,
                "application_status": app_status,
                "llm_status": llm_status,
                "active_alerts_count": len(dashboard_data.active_alerts),
                "timestamp": dashboard_data.timestamp
            }
            
        except Exception as e:
            logger.error(f"헬스 요약 조회 실패: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 전역 대시보드 인스턴스
_dashboard: Optional[MonitoringDashboard] = None


def get_dashboard() -> MonitoringDashboard:
    """대시보드 인스턴스 조회"""
    global _dashboard
    if _dashboard is None:
        _dashboard = MonitoringDashboard()
    return _dashboard


if __name__ == "__main__":
    # 테스트 실행
    dashboard = MonitoringDashboard()
    
    # 대시보드 데이터 조회
    data = dashboard.get_dashboard_data(1)
    print("대시보드 데이터:")
    print(json.dumps(asdict(data), indent=2, ensure_ascii=False))
    
    # 헬스 요약 조회
    health = dashboard.get_health_summary()
    print("\n헬스 요약:")
    print(json.dumps(health, indent=2, ensure_ascii=False))
