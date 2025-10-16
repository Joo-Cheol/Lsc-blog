#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
알림 관리자
"""
import json
import smtplib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    """알림 규칙"""
    name: str
    metric_type: str  # 'system', 'application', 'llm'
    metric_name: str
    operator: str  # '>', '<', '>=', '<=', '==', '!='
    threshold: float
    duration_minutes: int  # 이 조건이 지속되어야 하는 시간
    severity: str  # 'low', 'medium', 'high', 'critical'
    enabled: bool = True
    last_triggered: Optional[str] = None
    cooldown_minutes: int = 60  # 알림 간격


@dataclass
class Alert:
    """알림"""
    id: str
    rule_name: str
    severity: str
    message: str
    metric_value: float
    threshold: float
    timestamp: str
    resolved: bool = False
    resolved_at: Optional[str] = None


class AlertManager:
    """알림 관리자"""
    
    def __init__(self, db_path: str = "monitoring/alerts.db"):
        self.db_path = db_path
        self._init_database()
        self.alert_rules: List[AlertRule] = []
        self.notification_handlers: List[Callable[[Alert], None]] = []
        self._load_default_rules()
    
    def _init_database(self):
        """데이터베이스 초기화"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                metric_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                operator TEXT NOT NULL,
                threshold REAL NOT NULL,
                duration_minutes INTEGER NOT NULL,
                severity TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                last_triggered TEXT,
                cooldown_minutes INTEGER DEFAULT 60
            );
            
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                rule_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                metric_value REAL NOT NULL,
                threshold REAL NOT NULL,
                timestamp TEXT NOT NULL,
                resolved BOOLEAN DEFAULT 0,
                resolved_at TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
            CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
            CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved);
        """)
        conn.commit()
        conn.close()
    
    def _load_default_rules(self):
        """기본 알림 규칙 로드"""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric_type="system",
                metric_name="cpu_percent",
                operator=">",
                threshold=80.0,
                duration_minutes=5,
                severity="high"
            ),
            AlertRule(
                name="high_memory_usage",
                metric_type="system",
                metric_name="memory_percent",
                operator=">",
                threshold=85.0,
                duration_minutes=5,
                severity="high"
            ),
            AlertRule(
                name="low_disk_space",
                metric_type="system",
                metric_name="disk_usage_percent",
                operator=">",
                threshold=90.0,
                duration_minutes=10,
                severity="critical"
            ),
            AlertRule(
                name="high_error_rate",
                metric_type="application",
                metric_name="error_rate",
                operator=">",
                threshold=10.0,
                duration_minutes=5,
                severity="high"
            ),
            AlertRule(
                name="slow_response_time",
                metric_type="application",
                metric_name="avg_response_time_ms",
                operator=">",
                threshold=5000.0,
                duration_minutes=5,
                severity="medium"
            ),
            AlertRule(
                name="llm_provider_down",
                metric_type="llm",
                metric_name="availability",
                operator="==",
                threshold=0.0,
                duration_minutes=1,
                severity="critical"
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule):
        """알림 규칙 추가"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO alert_rules 
                (name, metric_type, metric_name, operator, threshold, duration_minutes,
                 severity, enabled, last_triggered, cooldown_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.name, rule.metric_type, rule.metric_name, rule.operator,
                rule.threshold, rule.duration_minutes, rule.severity,
                rule.enabled, rule.last_triggered, rule.cooldown_minutes
            ))
            conn.commit()
            conn.close()
            
            # 메모리에도 추가
            existing_rule = next((r for r in self.alert_rules if r.name == rule.name), None)
            if existing_rule:
                self.alert_rules.remove(existing_rule)
            self.alert_rules.append(rule)
            
            logger.info(f"알림 규칙 추가: {rule.name}")
            
        except Exception as e:
            logger.error(f"알림 규칙 추가 실패: {e}")
    
    def remove_rule(self, rule_name: str):
        """알림 규칙 제거"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM alert_rules WHERE name = ?", (rule_name,))
            conn.commit()
            conn.close()
            
            # 메모리에서도 제거
            self.alert_rules = [r for r in self.alert_rules if r.name != rule_name]
            
            logger.info(f"알림 규칙 제거: {rule_name}")
            
        except Exception as e:
            logger.error(f"알림 규칙 제거 실패: {e}")
    
    def load_rules_from_db(self):
        """데이터베이스에서 규칙 로드"""
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("""
                SELECT name, metric_type, metric_name, operator, threshold,
                       duration_minutes, severity, enabled, last_triggered, cooldown_minutes
                FROM alert_rules
            """).fetchall()
            conn.close()
            
            self.alert_rules = []
            for row in rows:
                rule = AlertRule(
                    name=row[0],
                    metric_type=row[1],
                    metric_name=row[2],
                    operator=row[3],
                    threshold=row[4],
                    duration_minutes=row[5],
                    severity=row[6],
                    enabled=bool(row[7]),
                    last_triggered=row[8],
                    cooldown_minutes=row[9]
                )
                self.alert_rules.append(rule)
            
            logger.info(f"알림 규칙 {len(self.alert_rules)}개 로드됨")
            
        except Exception as e:
            logger.error(f"알림 규칙 로드 실패: {e}")
    
    def check_metrics(self, metrics: Dict[str, Any]):
        """메트릭 체크 및 알림 생성"""
        try:
            current_time = datetime.now()
            
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                # 쿨다운 체크
                if rule.last_triggered:
                    last_triggered = datetime.fromisoformat(rule.last_triggered)
                    if (current_time - last_triggered).total_seconds() < rule.cooldown_minutes * 60:
                        continue
                
                # 메트릭 값 조회
                metric_value = self._get_metric_value(metrics, rule.metric_type, rule.metric_name)
                if metric_value is None:
                    continue
                
                # 조건 체크
                if self._check_condition(metric_value, rule.operator, rule.threshold):
                    # 지속 시간 체크 (실제 구현에서는 더 정교한 로직 필요)
                    alert = Alert(
                        id=f"{rule.name}_{int(current_time.timestamp())}",
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=self._generate_alert_message(rule, metric_value),
                        metric_value=metric_value,
                        threshold=rule.threshold,
                        timestamp=current_time.isoformat()
                    )
                    
                    self._trigger_alert(alert)
                    
                    # 규칙의 마지막 트리거 시간 업데이트
                    rule.last_triggered = current_time.isoformat()
                    self._update_rule_last_triggered(rule.name, current_time.isoformat())
                    
        except Exception as e:
            logger.error(f"메트릭 체크 실패: {e}")
    
    def _get_metric_value(self, metrics: Dict[str, Any], metric_type: str, metric_name: str) -> Optional[float]:
        """메트릭 값 조회"""
        try:
            if metric_type == "system":
                return metrics.get("system", {}).get(metric_name)
            elif metric_type == "application":
                return metrics.get("application", {}).get(metric_name)
            elif metric_type == "llm":
                # LLM 메트릭은 별도 처리
                return self._get_llm_metric_value(metrics, metric_name)
            return None
        except:
            return None
    
    def _get_llm_metric_value(self, metrics: Dict[str, Any], metric_name: str) -> Optional[float]:
        """LLM 메트릭 값 조회"""
        try:
            if metric_name == "availability":
                # Provider 가용성 체크
                from src.llm.provider_manager import get_provider_manager
                manager = get_provider_manager()
                providers = manager.list_providers()
                
                available_count = sum(1 for p in providers.values() if p.get("available", False))
                total_count = len(providers)
                
                return (available_count / total_count) * 100 if total_count > 0 else 0
            return None
        except:
            return None
    
    def _check_condition(self, value: float, operator: str, threshold: float) -> bool:
        """조건 체크"""
        try:
            if operator == ">":
                return value > threshold
            elif operator == "<":
                return value < threshold
            elif operator == ">=":
                return value >= threshold
            elif operator == "<=":
                return value <= threshold
            elif operator == "==":
                return abs(value - threshold) < 0.001
            elif operator == "!=":
                return abs(value - threshold) >= 0.001
            return False
        except:
            return False
    
    def _generate_alert_message(self, rule: AlertRule, metric_value: float) -> str:
        """알림 메시지 생성"""
        severity_emoji = {
            "low": "🟡",
            "medium": "🟠", 
            "high": "🔴",
            "critical": "🚨"
        }
        
        emoji = severity_emoji.get(rule.severity, "⚠️")
        
        return f"{emoji} {rule.severity.upper()}: {rule.name}\n" \
               f"현재 값: {metric_value:.2f} {rule.operator} {rule.threshold}\n" \
               f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    def _trigger_alert(self, alert: Alert):
        """알림 트리거"""
        try:
            # 데이터베이스에 저장
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO alerts 
                (id, rule_name, severity, message, metric_value, threshold, timestamp, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.id, alert.rule_name, alert.severity, alert.message,
                alert.metric_value, alert.threshold, alert.timestamp, alert.resolved
            ))
            conn.commit()
            conn.close()
            
            # 알림 핸들러 실행
            for handler in self.notification_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"알림 핸들러 실행 실패: {e}")
            
            logger.warning(f"알림 트리거: {alert.rule_name} - {alert.message}")
            
        except Exception as e:
            logger.error(f"알림 트리거 실패: {e}")
    
    def _update_rule_last_triggered(self, rule_name: str, timestamp: str):
        """규칙의 마지막 트리거 시간 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                UPDATE alert_rules SET last_triggered = ? WHERE name = ?
            """, (timestamp, rule_name))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"규칙 업데이트 실패: {e}")
    
    def add_notification_handler(self, handler: Callable[[Alert], None]):
        """알림 핸들러 추가"""
        self.notification_handlers.append(handler)
    
    def get_active_alerts(self, hours: int = 24) -> List[Alert]:
        """활성 알림 조회"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            since_str = since.isoformat()
            
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("""
                SELECT id, rule_name, severity, message, metric_value, threshold,
                       timestamp, resolved, resolved_at
                FROM alerts 
                WHERE timestamp >= ? AND resolved = 0
                ORDER BY timestamp DESC
            """, (since_str,)).fetchall()
            conn.close()
            
            alerts = []
            for row in rows:
                alert = Alert(
                    id=row[0],
                    rule_name=row[1],
                    severity=row[2],
                    message=row[3],
                    metric_value=row[4],
                    threshold=row[5],
                    timestamp=row[6],
                    resolved=bool(row[7]),
                    resolved_at=row[8]
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"활성 알림 조회 실패: {e}")
            return []
    
    def resolve_alert(self, alert_id: str):
        """알림 해결"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                UPDATE alerts SET resolved = 1, resolved_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), alert_id))
            conn.commit()
            conn.close()
            
            logger.info(f"알림 해결: {alert_id}")
            
        except Exception as e:
            logger.error(f"알림 해결 실패: {e}")


# 전역 알림 관리자 인스턴스
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """알림 관리자 인스턴스 조회"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def check_alerts(metrics: Dict[str, Any]):
    """알림 체크 (편의 함수)"""
    manager = get_alert_manager()
    manager.check_metrics(metrics)


if __name__ == "__main__":
    # 테스트 실행
    manager = AlertManager()
    
    # 테스트 메트릭
    test_metrics = {
        "system": {
            "cpu_percent": 85.0,
            "memory_percent": 90.0,
            "disk_usage_percent": 95.0
        },
        "application": {
            "error_rate": 15.0,
            "avg_response_time_ms": 6000.0
        }
    }
    
    manager.check_metrics(test_metrics)
    
    active_alerts = manager.get_active_alerts(1)
    print(f"활성 알림 {len(active_alerts)}개:")
    for alert in active_alerts:
        print(f"- {alert.severity}: {alert.message}")
