#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Job 시스템 메트릭 수집기
"""
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from api.core.jobs import JOBS

logger = logging.getLogger(__name__)


class JobMetricsCollector:
    """Job 시스템 메트릭 수집기"""
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.operation_counters = defaultdict(int)
        self.operation_timings = defaultdict(list)
        self.job_completion_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.start_time = time.time()
        
    def record_operation(self, operation: str, duration_ms: float, success: bool = True):
        """작업 실행 기록"""
        self.operation_counters[operation] += 1
        self.operation_timings[operation].append(duration_ms)
        
        if not success:
            self.error_counts[operation] += 1
        
        # 최근 100개만 유지
        if len(self.operation_timings[operation]) > 100:
            self.operation_timings[operation] = self.operation_timings[operation][-100:]
    
    def record_job_completion(self, job_type: str, duration_ms: float, success: bool = True):
        """Job 완료 기록"""
        self.job_completion_times[job_type].append({
            'duration_ms': duration_ms,
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # 최근 50개만 유지
        if len(self.job_completion_times[job_type]) > 50:
            self.job_completion_times[job_type] = self.job_completion_times[job_type][-50:]
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """작업 통계 조회"""
        stats = {}
        
        for operation, timings in self.operation_timings.items():
            if timings:
                success_count = self.operation_counters[operation] - self.error_counts[operation]
                success_rate = (success_count / self.operation_counters[operation]) * 100 if self.operation_counters[operation] > 0 else 0
                
                stats[operation] = {
                    'total_count': self.operation_counters[operation],
                    'success_count': success_count,
                    'error_count': self.error_counts[operation],
                    'success_rate': success_rate,
                    'avg_duration_ms': sum(timings) / len(timings),
                    'min_duration_ms': min(timings),
                    'max_duration_ms': max(timings),
                    'recent_count': len(timings)
                }
        
        return stats
    
    def get_job_stats(self) -> Dict[str, Any]:
        """Job 통계 조회"""
        stats = {}
        
        for job_type, completions in self.job_completion_times.items():
            if completions:
                successful = [c for c in completions if c['success']]
                failed = [c for c in completions if not c['success']]
                
                success_rate = (len(successful) / len(completions)) * 100 if completions else 0
                avg_duration = sum(c['duration_ms'] for c in successful) / len(successful) if successful else 0
                
                stats[job_type] = {
                    'total_completions': len(completions),
                    'successful': len(successful),
                    'failed': len(failed),
                    'success_rate': success_rate,
                    'avg_duration_ms': avg_duration,
                    'recent_completions': len(completions)
                }
        
        return stats
    
    def get_recent_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """최근 Job 목록 조회"""
        try:
            jobs = []
            for job_id, job in JOBS._jobs.items():
                job_dict = {
                    'id': job.id,
                    'type': job.type,
                    'status': job.status,
                    'created_at': job.created_at,
                    'started_at': job.started_at,
                    'finished_at': job.finished_at,
                    'progress': job.progress,
                    'counters': job.counters,
                    'results': job.results,
                    'error_count': len(job.errors),
                    'event_count': len(job.events)
                }
                jobs.append(job_dict)
            
            # 생성 시간 기준 정렬 (최신순)
            jobs.sort(key=lambda x: x['created_at'], reverse=True)
            return jobs[:limit]
            
        except Exception as e:
            logger.error(f"최근 Job 조회 실패: {e}")
            return []
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """대시보드용 메트릭 조회"""
        try:
            # Job 시스템 통계
            job_registry_stats = JOBS.get_stats()
            
            # 최근 Job 목록
            recent_jobs = self.get_recent_jobs(10)
            
            # 작업 통계
            operation_stats = self.get_operation_stats()
            
            # Job 완료 통계
            job_stats = self.get_job_stats()
            
            # 현재 실행 중인 Job 수
            running_jobs = len([j for j in recent_jobs if j['status'] == 'running'])
            
            # 최근 1시간 성공률
            recent_success_rate = 0
            if operation_stats:
                total_ops = sum(stats['total_count'] for stats in operation_stats.values())
                total_success = sum(stats['success_count'] for stats in operation_stats.values())
                if total_ops > 0:
                    recent_success_rate = (total_success / total_ops) * 100
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': time.time() - self.start_time,
                'job_registry': job_registry_stats,
                'recent_jobs': recent_jobs,
                'running_jobs': running_jobs,
                'operation_stats': operation_stats,
                'job_stats': job_stats,
                'recent_success_rate': recent_success_rate,
                'total_operations': sum(self.operation_counters.values()),
                'total_errors': sum(self.error_counts.values())
            }
            
        except Exception as e:
            logger.error(f"대시보드 메트릭 조회 실패: {e}")
            return {}


# 전역 인스턴스
job_metrics = JobMetricsCollector()

