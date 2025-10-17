from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Optional, Dict, Any, List
import uuid
import threading
import time
from collections import deque

JobType = Literal["crawl", "preprocess_embed", "reindex", "backup", "restore"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]

@dataclass
class JobEvent:
    ts: str
    type: str          # progress|info|warning|error|done
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    event_id: int = 0  # 순차적 이벤트 ID (재연결용)

@dataclass
class JobState:
    id: str
    type: JobType
    status: JobStatus = "queued"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    progress: float = 0.0                      # 0.0 ~ 1.0
    counters: Dict[str, int] = field(default_factory=lambda: {
        "found":0, "new":0, "skipped":0, "failed":0, "pages":0
    })
    results: Dict[str, Any] = field(default_factory=dict)  # e.g. {"posts":[{title,url,logno}]}
    errors: List[Dict[str, Any]] = field(default_factory=list)  # 구조화된 에러: {code, message, suggestion}
    events: deque = field(default_factory=lambda: deque(maxlen=500))  # RingBuffer
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    _event_counter: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def push(self, type: str, message: str, **data):
        with self._lock:
            self._event_counter += 1
            ev = JobEvent(
                ts=datetime.utcnow().isoformat(), 
                type=type, 
                message=message, 
                data=data,
                event_id=self._event_counter
            )
            self.events.append(ev)
            self.last_accessed_at = datetime.utcnow().isoformat()
        return ev
    
    def add_error(self, code: str, message: str, suggestion: str = ""):
        """구조화된 에러 추가"""
        with self._lock:
            self.errors.append({
                "code": code,
                "message": message,
                "suggestion": suggestion,
                "timestamp": datetime.utcnow().isoformat()
            })
            self.last_accessed_at = datetime.utcnow().isoformat()
    
    def get_events_since(self, since_event_id: int = 0) -> List[JobEvent]:
        """지정된 이벤트 ID 이후의 이벤트들 반환 (재연결용)"""
        with self._lock:
            return [ev for ev in self.events if ev.event_id > since_event_id]

class JobRegistry:
    def __init__(self, max_jobs: int = 1000, ttl_hours: int = 24):
        self._jobs: Dict[str, JobState] = {}
        self._lock = threading.Lock()
        self.max_jobs = max_jobs
        self.ttl_hours = ttl_hours
        self._cleanup_thread = None
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """백그라운드 정리 스레드 시작"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()

    def _cleanup_loop(self):
        """주기적으로 오래된 Job 정리"""
        while True:
            try:
                time.sleep(300)  # 5분마다 정리
                self._cleanup_old_jobs()
            except Exception:
                pass  # 백그라운드 스레드이므로 예외 무시

    def _cleanup_old_jobs(self):
        """TTL 초과 및 LRU 기반 Job 정리"""
        with self._lock:
            now = datetime.utcnow()
            ttl_cutoff = now - timedelta(hours=self.ttl_hours)
            
            # TTL 초과 Job 제거
            expired_jobs = []
            for jid, job in self._jobs.items():
                created_at = datetime.fromisoformat(job.created_at)
                if created_at < ttl_cutoff and job.status in ("succeeded", "failed"):
                    expired_jobs.append(jid)
            
            for jid in expired_jobs:
                del self._jobs[jid]
            
            # 최대 개수 초과 시 LRU 정리
            if len(self._jobs) > self.max_jobs:
                # last_accessed_at 기준으로 정렬하여 오래된 것부터 제거
                sorted_jobs = sorted(
                    self._jobs.items(),
                    key=lambda x: x[1].last_accessed_at
                )
                
                # 완료된 Job부터 제거
                for jid, job in sorted_jobs:
                    if job.status in ("succeeded", "failed") and len(self._jobs) > self.max_jobs:
                        del self._jobs[jid]

    def create(self, job_type: JobType) -> JobState:
        with self._lock:
            # 최대 개수 초과 시 정리
            if len(self._jobs) >= self.max_jobs:
                self._cleanup_old_jobs()
            
            jid = uuid.uuid4().hex[:12]
            st = JobState(id=jid, type=job_type)
            self._jobs[jid] = st
            return st

    def get(self, jid: str) -> Optional[JobState]:
        job = self._jobs.get(jid)
        if job:
            job.last_accessed_at = datetime.utcnow().isoformat()
        return job

    def get_stats(self) -> Dict[str, Any]:
        """JobRegistry 통계 정보"""
        with self._lock:
            status_counts = {}
            for job in self._jobs.values():
                status_counts[job.status] = status_counts.get(job.status, 0) + 1
            
            return {
                "total_jobs": len(self._jobs),
                "status_counts": status_counts,
                "max_jobs": self.max_jobs,
                "ttl_hours": self.ttl_hours
            }

JOBS = JobRegistry()
