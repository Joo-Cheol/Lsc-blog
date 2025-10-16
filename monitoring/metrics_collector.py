#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메트릭 수집기
"""
import time
import psutil
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """시스템 메트릭"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float
    load_average: List[float]


@dataclass
class ApplicationMetrics:
    """애플리케이션 메트릭"""
    timestamp: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    active_connections: int
    total_posts: int
    total_chunks: int
    total_searches: int
    total_generations: int


@dataclass
class LLMMetrics:
    """LLM 메트릭"""
    timestamp: str
    provider: str
    model_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_tokens_per_request: float
    avg_response_time_ms: float
    total_tokens_used: int


class MetricsCollector:
    """메트릭 수집기"""
    
    def __init__(self, db_path: str = "monitoring/metrics.db"):
        self.db_path = db_path
        self._init_database()
        self._last_network_stats = None
        self._last_collection_time = None
    
    def _init_database(self):
        """데이터베이스 초기화"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                memory_used_mb REAL,
                memory_total_mb REAL,
                disk_usage_percent REAL,
                disk_free_gb REAL,
                network_sent_mb REAL,
                network_recv_mb REAL,
                load_average TEXT
            );
            
            CREATE TABLE IF NOT EXISTS application_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_requests INTEGER,
                successful_requests INTEGER,
                failed_requests INTEGER,
                avg_response_time_ms REAL,
                active_connections INTEGER,
                total_posts INTEGER,
                total_chunks INTEGER,
                total_searches INTEGER,
                total_generations INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS llm_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                provider TEXT,
                model_name TEXT,
                total_requests INTEGER,
                successful_requests INTEGER,
                failed_requests INTEGER,
                avg_tokens_per_request REAL,
                avg_response_time_ms REAL,
                total_tokens_used INTEGER
            );
            
            CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_metrics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_app_timestamp ON application_metrics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_llm_timestamp ON llm_metrics(timestamp);
        """)
        conn.commit()
        conn.close()
    
    def collect_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_total_mb = memory.total / (1024 * 1024)
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # 네트워크 통계
            network = psutil.net_io_counters()
            network_sent_mb = network.bytes_sent / (1024 * 1024)
            network_recv_mb = network.bytes_recv / (1024 * 1024)
            
            # 로드 평균 (Unix 계열에서만 사용 가능)
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                load_average = [0.0, 0.0, 0.0]
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_total_mb=memory_total_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                load_average=load_average
            )
        except Exception as e:
            logger.error(f"시스템 메트릭 수집 실패: {e}")
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_total_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0,
                load_average=[0.0, 0.0, 0.0]
            )
    
    def collect_application_metrics(self) -> ApplicationMetrics:
        """애플리케이션 메트릭 수집"""
        try:
            # 데이터베이스에서 통계 조회
            conn = sqlite3.connect("src/data/meta/seen.sqlite")
            
            # 포스트 수
            total_posts = conn.execute("SELECT COUNT(*) FROM seen_posts").fetchone()[0]
            
            # 청크 수 (벡터 인덱스에서 조회)
            try:
                from src.vector.simple_index import SimpleVectorIndex
                from src.vector.embedder import EmbeddingService
                
                embedder = EmbeddingService()
                index = SimpleVectorIndex("./src/data/indexes/default/chroma", embedder)
                stats = index.get_index_stats()
                total_chunks = stats.get("total_chunks", 0)
            except:
                total_chunks = 0
            
            conn.close()
            
            # API 통계 (실제 구현에서는 별도 테이블에서 조회)
            total_requests = 0
            successful_requests = 0
            failed_requests = 0
            avg_response_time_ms = 0.0
            active_connections = 0
            total_searches = 0
            total_generations = 0
            
            return ApplicationMetrics(
                timestamp=datetime.now().isoformat(),
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                avg_response_time_ms=avg_response_time_ms,
                active_connections=active_connections,
                total_posts=total_posts,
                total_chunks=total_chunks,
                total_searches=total_searches,
                total_generations=total_generations
            )
        except Exception as e:
            logger.error(f"애플리케이션 메트릭 수집 실패: {e}")
            return ApplicationMetrics(
                timestamp=datetime.now().isoformat(),
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time_ms=0.0,
                active_connections=0,
                total_posts=0,
                total_chunks=0,
                total_searches=0,
                total_generations=0
            )
    
    def collect_llm_metrics(self) -> List[LLMMetrics]:
        """LLM 메트릭 수집"""
        try:
            from src.llm.provider_manager import get_provider_manager
            
            manager = get_provider_manager()
            providers = manager.list_providers()
            
            llm_metrics = []
            for provider_name, provider_info in providers.items():
                if provider_info.get("available", False):
                    # 실제 구현에서는 각 Provider별 통계를 수집
                    metrics = LLMMetrics(
                        timestamp=datetime.now().isoformat(),
                        provider=provider_name,
                        model_name=provider_info.get("model_name", "unknown"),
                        total_requests=0,
                        successful_requests=0,
                        failed_requests=0,
                        avg_tokens_per_request=0.0,
                        avg_response_time_ms=0.0,
                        total_tokens_used=0
                    )
                    llm_metrics.append(metrics)
            
            return llm_metrics
        except Exception as e:
            logger.error(f"LLM 메트릭 수집 실패: {e}")
            return []
    
    def save_metrics(self, system_metrics: SystemMetrics, 
                    app_metrics: ApplicationMetrics, 
                    llm_metrics: List[LLMMetrics]):
        """메트릭 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 시스템 메트릭 저장
            conn.execute("""
                INSERT INTO system_metrics 
                (timestamp, cpu_percent, memory_percent, memory_used_mb, memory_total_mb,
                 disk_usage_percent, disk_free_gb, network_sent_mb, network_recv_mb, load_average)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                system_metrics.timestamp,
                system_metrics.cpu_percent,
                system_metrics.memory_percent,
                system_metrics.memory_used_mb,
                system_metrics.memory_total_mb,
                system_metrics.disk_usage_percent,
                system_metrics.disk_free_gb,
                system_metrics.network_sent_mb,
                system_metrics.network_recv_mb,
                json.dumps(system_metrics.load_average)
            ))
            
            # 애플리케이션 메트릭 저장
            conn.execute("""
                INSERT INTO application_metrics 
                (timestamp, total_requests, successful_requests, failed_requests,
                 avg_response_time_ms, active_connections, total_posts, total_chunks,
                 total_searches, total_generations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                app_metrics.timestamp,
                app_metrics.total_requests,
                app_metrics.successful_requests,
                app_metrics.failed_requests,
                app_metrics.avg_response_time_ms,
                app_metrics.active_connections,
                app_metrics.total_posts,
                app_metrics.total_chunks,
                app_metrics.total_searches,
                app_metrics.total_generations
            ))
            
            # LLM 메트릭 저장
            for llm_metric in llm_metrics:
                conn.execute("""
                    INSERT INTO llm_metrics 
                    (timestamp, provider, model_name, total_requests, successful_requests,
                     failed_requests, avg_tokens_per_request, avg_response_time_ms, total_tokens_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    llm_metric.timestamp,
                    llm_metric.provider,
                    llm_metric.model_name,
                    llm_metric.total_requests,
                    llm_metric.successful_requests,
                    llm_metric.failed_requests,
                    llm_metric.avg_tokens_per_request,
                    llm_metric.avg_response_time_ms,
                    llm_metric.total_tokens_used
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"메트릭 저장 실패: {e}")
    
    def collect_and_save(self):
        """메트릭 수집 및 저장"""
        try:
            system_metrics = self.collect_system_metrics()
            app_metrics = self.collect_application_metrics()
            llm_metrics = self.collect_llm_metrics()
            
            self.save_metrics(system_metrics, app_metrics, llm_metrics)
            
            logger.info(f"메트릭 수집 완료: {system_metrics.timestamp}")
            
        except Exception as e:
            logger.error(f"메트릭 수집 및 저장 실패: {e}")
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """메트릭 요약 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 최근 N시간 데이터 조회
            since = datetime.now() - timedelta(hours=hours)
            since_str = since.isoformat()
            
            # 시스템 메트릭 요약
            system_summary = conn.execute("""
                SELECT 
                    AVG(cpu_percent) as avg_cpu,
                    MAX(cpu_percent) as max_cpu,
                    AVG(memory_percent) as avg_memory,
                    MAX(memory_percent) as max_memory,
                    AVG(disk_usage_percent) as avg_disk,
                    MAX(disk_usage_percent) as max_disk
                FROM system_metrics 
                WHERE timestamp >= ?
            """, (since_str,)).fetchone()
            
            # 애플리케이션 메트릭 요약
            app_summary = conn.execute("""
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
            
            return {
                "period_hours": hours,
                "system": {
                    "avg_cpu_percent": system_summary[0] or 0,
                    "max_cpu_percent": system_summary[1] or 0,
                    "avg_memory_percent": system_summary[2] or 0,
                    "max_memory_percent": system_summary[3] or 0,
                    "avg_disk_percent": system_summary[4] or 0,
                    "max_disk_percent": system_summary[5] or 0
                },
                "application": {
                    "total_requests": app_summary[0] or 0,
                    "successful_requests": app_summary[1] or 0,
                    "failed_requests": app_summary[2] or 0,
                    "avg_response_time_ms": app_summary[3] or 0,
                    "total_posts": app_summary[4] or 0,
                    "total_chunks": app_summary[5] or 0,
                    "total_searches": app_summary[6] or 0,
                    "total_generations": app_summary[7] or 0
                }
            }
            
        except Exception as e:
            logger.error(f"메트릭 요약 조회 실패: {e}")
            return {"error": str(e)}


# 전역 메트릭 수집기 인스턴스
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """메트릭 수집기 인스턴스 조회"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def collect_metrics():
    """메트릭 수집 (편의 함수)"""
    collector = get_metrics_collector()
    collector.collect_and_save()


if __name__ == "__main__":
    # 테스트 실행
    collector = MetricsCollector()
    collector.collect_and_save()
    
    summary = collector.get_metrics_summary(1)
    print("메트릭 요약:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
