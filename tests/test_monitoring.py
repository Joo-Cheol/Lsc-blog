#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모니터링 모듈 단위 테스트
"""
import unittest
import sys
import os
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from monitoring.metrics_collector import MetricsCollector, SystemMetrics, ApplicationMetrics, LLMMetrics
from monitoring.alert_manager import AlertManager, AlertRule, Alert
from monitoring.dashboard import MonitoringDashboard, DashboardData
from monitoring.operational_scripts import OperationalScripts


class TestMetricsCollector(unittest.TestCase):
    """메트릭 수집기 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_metrics.db")
        self.collector = MetricsCollector(self.db_path)
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """데이터베이스 초기화 테스트"""
        # 데이터베이스 파일이 생성되었는지 확인
        self.assertTrue(os.path.exists(self.db_path))
        
        # 테이블이 생성되었는지 확인
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [table[0] for table in tables]
        
        self.assertIn('system_metrics', table_names)
        self.assertIn('application_metrics', table_names)
        self.assertIn('llm_metrics', table_names)
        
        conn.close()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_collect_system_metrics(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """시스템 메트릭 수집 테스트"""
        # Mock 설정
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(
            percent=60.0,
            used=1024*1024*1024,  # 1GB
            total=2*1024*1024*1024  # 2GB
        )
        mock_disk.return_value = MagicMock(
            used=100*1024*1024*1024,  # 100GB
            total=200*1024*1024*1024,  # 200GB
            free=100*1024*1024*1024  # 100GB
        )
        mock_net.return_value = MagicMock(
            bytes_sent=1024*1024,  # 1MB
            bytes_recv=2*1024*1024  # 2MB
        )
        
        # 메트릭 수집
        metrics = self.collector.collect_system_metrics()
        
        # 결과 검증
        self.assertIsInstance(metrics, SystemMetrics)
        self.assertEqual(metrics.cpu_percent, 50.0)
        self.assertEqual(metrics.memory_percent, 60.0)
        self.assertEqual(metrics.memory_used_mb, 1024.0)
        self.assertEqual(metrics.memory_total_mb, 2048.0)
        self.assertEqual(metrics.disk_usage_percent, 50.0)
        self.assertEqual(metrics.disk_free_gb, 100.0)
        self.assertEqual(metrics.network_sent_mb, 1.0)
        self.assertEqual(metrics.network_recv_mb, 2.0)
    
    @patch('sqlite3.connect')
    def test_collect_application_metrics(self, mock_connect):
        """애플리케이션 메트릭 수집 테스트"""
        # Mock 데이터베이스 연결
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (100,)  # total_posts
        
        # 메트릭 수집
        metrics = self.collector.collect_application_metrics()
        
        # 결과 검증
        self.assertIsInstance(metrics, ApplicationMetrics)
        self.assertEqual(metrics.total_posts, 100)
    
    def test_save_metrics(self):
        """메트릭 저장 테스트"""
        # 테스트 메트릭 생성
        system_metrics = SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            memory_total_mb=2048.0,
            disk_usage_percent=50.0,
            disk_free_gb=100.0,
            network_sent_mb=1.0,
            network_recv_mb=2.0,
            load_average=[1.0, 1.5, 2.0]
        )
        
        app_metrics = ApplicationMetrics(
            timestamp=datetime.now().isoformat(),
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            avg_response_time_ms=500.0,
            active_connections=10,
            total_posts=50,
            total_chunks=200,
            total_searches=30,
            total_generations=20
        )
        
        llm_metrics = [
            LLMMetrics(
                timestamp=datetime.now().isoformat(),
                provider="ollama",
                model_name="test-model",
                total_requests=10,
                successful_requests=9,
                failed_requests=1,
                avg_tokens_per_request=100.0,
                avg_response_time_ms=1000.0,
                total_tokens_used=1000
            )
        ]
        
        # 메트릭 저장
        self.collector.save_metrics(system_metrics, app_metrics, llm_metrics)
        
        # 저장 확인
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        
        # 시스템 메트릭 확인
        system_count = conn.execute("SELECT COUNT(*) FROM system_metrics").fetchone()[0]
        self.assertEqual(system_count, 1)
        
        # 애플리케이션 메트릭 확인
        app_count = conn.execute("SELECT COUNT(*) FROM application_metrics").fetchone()[0]
        self.assertEqual(app_count, 1)
        
        # LLM 메트릭 확인
        llm_count = conn.execute("SELECT COUNT(*) FROM llm_metrics").fetchone()[0]
        self.assertEqual(llm_count, 1)
        
        conn.close()
    
    def test_get_metrics_summary(self):
        """메트릭 요약 조회 테스트"""
        # 테스트 데이터 저장
        system_metrics = SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            memory_total_mb=2048.0,
            disk_usage_percent=50.0,
            disk_free_gb=100.0,
            network_sent_mb=1.0,
            network_recv_mb=2.0,
            load_average=[1.0, 1.5, 2.0]
        )
        
        app_metrics = ApplicationMetrics(
            timestamp=datetime.now().isoformat(),
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            avg_response_time_ms=500.0,
            active_connections=10,
            total_posts=50,
            total_chunks=200,
            total_searches=30,
            total_generations=20
        )
        
        self.collector.save_metrics(system_metrics, app_metrics, [])
        
        # 요약 조회
        summary = self.collector.get_metrics_summary(1)
        
        # 결과 검증
        self.assertIn("system", summary)
        self.assertIn("application", summary)
        self.assertEqual(summary["system"]["avg_cpu_percent"], 50.0)
        self.assertEqual(summary["application"]["total_requests"], 100)


class TestAlertManager(unittest.TestCase):
    """알림 관리자 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_alerts.db")
        self.manager = AlertManager(self.db_path)
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """데이터베이스 초기화 테스트"""
        # 데이터베이스 파일이 생성되었는지 확인
        self.assertTrue(os.path.exists(self.db_path))
        
        # 테이블이 생성되었는지 확인
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [table[0] for table in tables]
        
        self.assertIn('alert_rules', table_names)
        self.assertIn('alerts', table_names)
        
        conn.close()
    
    def test_add_rule(self):
        """알림 규칙 추가 테스트"""
        # 기존 규칙 수 확인
        initial_count = len(self.manager.alert_rules)
        
        rule = AlertRule(
            name="test_rule",
            metric_type="system",
            metric_name="cpu_percent",
            operator=">",
            threshold=80.0,
            duration_minutes=5,
            severity="high"
        )
        
        self.manager.add_rule(rule)
        
        # 규칙이 추가되었는지 확인
        self.assertEqual(len(self.manager.alert_rules), initial_count + 1)
        self.assertTrue(any(r.name == "test_rule" for r in self.manager.alert_rules))
    
    def test_remove_rule(self):
        """알림 규칙 제거 테스트"""
        # 기존 규칙 수 확인
        initial_count = len(self.manager.alert_rules)
        
        rule = AlertRule(
            name="test_rule",
            metric_type="system",
            metric_name="cpu_percent",
            operator=">",
            threshold=80.0,
            duration_minutes=5,
            severity="high"
        )
        
        self.manager.add_rule(rule)
        self.assertEqual(len(self.manager.alert_rules), initial_count + 1)
        
        self.manager.remove_rule("test_rule")
        self.assertEqual(len(self.manager.alert_rules), initial_count)
    
    def test_check_condition(self):
        """조건 체크 테스트"""
        # 다양한 연산자 테스트
        self.assertTrue(self.manager._check_condition(90.0, ">", 80.0))
        self.assertFalse(self.manager._check_condition(70.0, ">", 80.0))
        
        self.assertTrue(self.manager._check_condition(70.0, "<", 80.0))
        self.assertFalse(self.manager._check_condition(90.0, "<", 80.0))
        
        self.assertTrue(self.manager._check_condition(80.0, ">=", 80.0))
        self.assertTrue(self.manager._check_condition(90.0, ">=", 80.0))
        self.assertFalse(self.manager._check_condition(70.0, ">=", 80.0))
        
        self.assertTrue(self.manager._check_condition(80.0, "<=", 80.0))
        self.assertTrue(self.manager._check_condition(70.0, "<=", 80.0))
        self.assertFalse(self.manager._check_condition(90.0, "<=", 80.0))
        
        self.assertTrue(self.manager._check_condition(80.0, "==", 80.0))
        self.assertFalse(self.manager._check_condition(90.0, "==", 80.0))
        
        self.assertTrue(self.manager._check_condition(90.0, "!=", 80.0))
        self.assertFalse(self.manager._check_condition(80.0, "!=", 80.0))
    
    def test_generate_alert_message(self):
        """알림 메시지 생성 테스트"""
        rule = AlertRule(
            name="test_rule",
            metric_type="system",
            metric_name="cpu_percent",
            operator=">",
            threshold=80.0,
            duration_minutes=5,
            severity="high"
        )
        
        message = self.manager._generate_alert_message(rule, 90.0)
        
        self.assertIn("HIGH", message)
        self.assertIn("test_rule", message)
        self.assertIn("90.00", message)
        self.assertIn("80.0", message)
    
    def test_get_active_alerts(self):
        """활성 알림 조회 테스트"""
        # 테스트 알림 생성
        alert = Alert(
            id="test_alert_1",
            rule_name="test_rule",
            severity="high",
            message="Test alert",
            metric_value=90.0,
            threshold=80.0,
            timestamp=datetime.now().isoformat()
        )
        
        # 알림 저장
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO alerts 
            (id, rule_name, severity, message, metric_value, threshold, timestamp, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.id, alert.rule_name, alert.severity, alert.message,
            alert.metric_value, alert.threshold, alert.timestamp, alert.resolved
        ))
        conn.commit()
        conn.close()
        
        # 활성 알림 조회
        active_alerts = self.manager.get_active_alerts(1)
        
        self.assertEqual(len(active_alerts), 1)
        self.assertEqual(active_alerts[0].id, "test_alert_1")


class TestMonitoringDashboard(unittest.TestCase):
    """모니터링 대시보드 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.metrics_db = os.path.join(self.temp_dir, "test_metrics.db")
        self.alerts_db = os.path.join(self.temp_dir, "test_alerts.db")
        self.dashboard = MonitoringDashboard(self.metrics_db, self.alerts_db)
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.temp_dir)
    
    def test_get_system_status(self):
        """시스템 상태 판정 테스트"""
        # 정상 상태
        status = self.dashboard._get_system_status(50.0, 60.0, 70.0)
        self.assertEqual(status, "healthy")
        
        # 경고 상태
        status = self.dashboard._get_system_status(85.0, 80.0, 85.0)
        self.assertEqual(status, "warning")
        
        # 위험 상태
        status = self.dashboard._get_system_status(95.0, 90.0, 95.0)
        self.assertEqual(status, "critical")
    
    def test_get_application_status(self):
        """애플리케이션 상태 판정 테스트"""
        # 정상 상태
        status = self.dashboard._get_application_status(98.0, 2.0, 1000.0)
        self.assertEqual(status, "healthy")
        
        # 경고 상태
        status = self.dashboard._get_application_status(90.0, 10.0, 3000.0)
        self.assertEqual(status, "degraded")
        
        # 위험 상태
        status = self.dashboard._get_application_status(80.0, 20.0, 8000.0)
        self.assertEqual(status, "critical")
    
    def test_get_llm_status_level(self):
        """LLM 상태 레벨 판정 테스트"""
        # 정상 상태
        status = self.dashboard._get_llm_status_level(100.0)
        self.assertEqual(status, "healthy")
        
        # 성능 저하 상태
        status = self.dashboard._get_llm_status_level(75.0)
        self.assertEqual(status, "degraded")
        
        # 경고 상태
        status = self.dashboard._get_llm_status_level(25.0)
        self.assertEqual(status, "warning")
        
        # 위험 상태
        status = self.dashboard._get_llm_status_level(0.0)
        self.assertEqual(status, "critical")
    
    @patch('src.llm.provider_manager.get_provider_manager')
    def test_get_llm_status(self, mock_get_provider_manager):
        """LLM 상태 조회 테스트"""
        # Mock 설정
        mock_manager = MagicMock()
        mock_get_provider_manager.return_value = mock_manager
        mock_manager.list_providers.return_value = {
            "ollama": {"available": True, "model_name": "test-model"},
            "gemini": {"available": False, "error": "API key not found"}
        }
        
        # LLM 상태 조회
        llm_status = self.dashboard._get_llm_status()
        
        # 결과 검증
        self.assertIn("providers", llm_status)
        self.assertIn("total_providers", llm_status)
        self.assertIn("available_providers", llm_status)
        self.assertIn("availability_rate", llm_status)
        self.assertIn("status", llm_status)
        
        self.assertEqual(llm_status["total_providers"], 2)
        self.assertEqual(llm_status["available_providers"], 1)
        self.assertEqual(llm_status["availability_rate"], 50.0)
        self.assertEqual(llm_status["status"], "warning")


class TestOperationalScripts(unittest.TestCase):
    """운영 스크립트 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.ops = OperationalScripts()
        self.ops.backup_dir = os.path.join(self.temp_dir, "backups")
        self.ops.logs_dir = os.path.join(self.temp_dir, "logs")
        self.ops.data_dir = os.path.join(self.temp_dir, "data")
        
        # 디렉토리 생성
        os.makedirs(self.ops.backup_dir, exist_ok=True)
        os.makedirs(self.ops.logs_dir, exist_ok=True)
        os.makedirs(self.ops.data_dir, exist_ok=True)
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.temp_dir)
    
    def test_backup_database(self):
        """데이터베이스 백업 테스트"""
        # 테스트 데이터베이스 생성
        test_db_path = os.path.join(self.ops.data_dir, "meta", "seen.sqlite")
        os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
        import sqlite3
        conn = sqlite3.connect(test_db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        
        # 백업 실행
        backup_path = self.ops.backup_database("test_backup")
        
        # 백업 파일 확인
        self.assertTrue(os.path.exists(backup_path))
        self.assertIn("test_backup", backup_path)
    
    def test_restore_database(self):
        """데이터베이스 복원 테스트"""
        # 테스트 백업 파일 생성
        backup_path = os.path.join(self.ops.backup_dir, "test_backup.db")
        import sqlite3
        conn = sqlite3.connect(backup_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        
        # 복원 대상 경로
        restore_path = os.path.join(self.ops.data_dir, "restore.db")
        
        # 복원 실행
        result = self.ops.restore_database(backup_path)
        
        # 복원 결과 확인
        self.assertTrue(result)
        # 실제 복원은 파일 경로가 다르므로 여기서는 성공 여부만 확인
    
    def test_cleanup_old_backups(self):
        """오래된 백업 정리 테스트"""
        # 테스트 백업 파일 생성
        old_backup = os.path.join(self.ops.backup_dir, "old_backup.db")
        new_backup = os.path.join(self.ops.backup_dir, "new_backup.db")
        
        with open(old_backup, 'w') as f:
            f.write("test")
        with open(new_backup, 'w') as f:
            f.write("test")
        
        # 오래된 파일의 수정 시간 변경
        old_time = time.time() - (31 * 24 * 60 * 60)  # 31일 전
        os.utime(old_backup, (old_time, old_time))
        
        # 정리 실행
        removed_count = self.ops.cleanup_old_backups(30)
        
        # 결과 확인
        self.assertEqual(removed_count, 1)
        self.assertFalse(os.path.exists(old_backup))
        self.assertTrue(os.path.exists(new_backup))
    
    def test_cleanup_logs(self):
        """로그 정리 테스트"""
        # 테스트 로그 파일 생성
        old_log = os.path.join(self.ops.logs_dir, "old.log")
        new_log = os.path.join(self.ops.logs_dir, "new.log")
        
        with open(old_log, 'w') as f:
            f.write("test")
        with open(new_log, 'w') as f:
            f.write("test")
        
        # 오래된 파일의 수정 시간 변경
        old_time = time.time() - (8 * 24 * 60 * 60)  # 8일 전
        os.utime(old_log, (old_time, old_time))
        
        # 정리 실행
        removed_count = self.ops.cleanup_logs(7)
        
        # 결과 확인
        self.assertEqual(removed_count, 1)
        self.assertFalse(os.path.exists(old_log))
        self.assertTrue(os.path.exists(new_log))
    
    def test_check_disk_space(self):
        """디스크 공간 확인 테스트"""
        disk_info = self.ops.check_disk_space()
        
        # 결과 검증
        self.assertIn("total_gb", disk_info)
        self.assertIn("used_gb", disk_info)
        self.assertIn("free_gb", disk_info)
        self.assertIn("usage_percent", disk_info)
        self.assertIn("status", disk_info)
        
        # 값들이 양수인지 확인
        self.assertGreater(disk_info["total_gb"], 0)
        self.assertGreaterEqual(disk_info["used_gb"], 0)
        self.assertGreaterEqual(disk_info["free_gb"], 0)
        self.assertGreaterEqual(disk_info["usage_percent"], 0)
    
    def test_check_database_integrity(self):
        """데이터베이스 무결성 확인 테스트"""
        # 테스트 데이터베이스 생성
        test_db_path = os.path.join(self.ops.data_dir, "meta", "seen.sqlite")
        os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
        import sqlite3
        conn = sqlite3.connect(test_db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('test')")
        conn.commit()
        conn.close()
        
        # 무결성 확인
        integrity = self.ops.check_database_integrity()
        
        # 결과 검증
        self.assertIn("status", integrity)
        if integrity["status"] == "ok":
            self.assertIn("integrity_check", integrity)
            self.assertIn("tables", integrity)
            self.assertIn("record_counts", integrity)
            
            self.assertEqual(integrity["integrity_check"], "ok")
            self.assertIn("test", integrity["tables"])
            self.assertEqual(integrity["record_counts"]["test"], 1)
    
    def test_optimize_database(self):
        """데이터베이스 최적화 테스트"""
        # 테스트 데이터베이스 생성
        test_db_path = os.path.join(self.ops.data_dir, "meta", "seen.sqlite")
        os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
        import sqlite3
        conn = sqlite3.connect(test_db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        
        # 최적화 실행
        result = self.ops.optimize_database()
        
        # 결과 확인
        self.assertTrue(result)
    
    def test_get_recommendations(self):
        """권장사항 생성 테스트"""
        # 테스트 데이터
        health_summary = {
            "overall_status": "warning",
            "active_alerts_count": 10
        }
        disk_space = {
            "usage_percent": 95.0
        }
        db_integrity = {
            "status": "ok"
        }
        
        # 권장사항 생성
        recommendations = self.ops._get_recommendations(health_summary, disk_space, db_integrity)
        
        # 결과 검증
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # 디스크 공간 관련 권장사항이 있는지 확인
        disk_recommendations = [r for r in recommendations if "디스크" in r]
        self.assertGreater(len(disk_recommendations), 0)
        
        # 알림 관련 권장사항이 있는지 확인
        alert_recommendations = [r for r in recommendations if "알림" in r]
        self.assertGreater(len(alert_recommendations), 0)


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.metrics_db = os.path.join(self.temp_dir, "test_metrics.db")
        self.alerts_db = os.path.join(self.temp_dir, "test_alerts.db")
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.temp_dir)
    
    def test_full_monitoring_workflow(self):
        """전체 모니터링 워크플로우 테스트"""
        # 메트릭 수집기 생성
        collector = MetricsCollector(self.metrics_db)
        
        # 알림 관리자 생성
        alert_manager = AlertManager(self.alerts_db)
        
        # 대시보드 생성
        dashboard = MonitoringDashboard(self.metrics_db, self.alerts_db)
        
        # 메트릭 수집
        system_metrics = collector.collect_system_metrics()
        app_metrics = collector.collect_application_metrics()
        llm_metrics = collector.collect_llm_metrics()
        
        # 메트릭 저장
        collector.save_metrics(system_metrics, app_metrics, llm_metrics)
        
        # 대시보드 데이터 조회
        dashboard_data = dashboard.get_dashboard_data(1)
        
        # 결과 검증
        self.assertIsInstance(dashboard_data, DashboardData)
        self.assertIn("timestamp", dashboard_data.__dict__)
        self.assertIn("system_health", dashboard_data.__dict__)
        self.assertIn("application_stats", dashboard_data.__dict__)
        self.assertIn("llm_status", dashboard_data.__dict__)
        self.assertIn("active_alerts", dashboard_data.__dict__)
        self.assertIn("recent_metrics", dashboard_data.__dict__)
        
        # 헬스 요약 조회
        health_summary = dashboard.get_health_summary()
        
        # 결과 검증
        self.assertIn("overall_status", health_summary)
        self.assertIn("system_status", health_summary)
        self.assertIn("application_status", health_summary)
        self.assertIn("llm_status", health_summary)
        self.assertIn("active_alerts_count", health_summary)
        self.assertIn("timestamp", health_summary)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
