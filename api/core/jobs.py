from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional, Dict, Any, List
import uuid

JobType = Literal["crawl", "preprocess_embed", "reindex", "backup", "restore"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]

@dataclass
class JobEvent:
    ts: str
    type: str          # progress|info|warning|error|done
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

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
    errors: List[str] = field(default_factory=list)
    events: List[JobEvent] = field(default_factory=list)

    def push(self, type: str, message: str, **data):
        ev = JobEvent(ts=datetime.utcnow().isoformat(), type=type, message=message, data=data)
        self.events.append(ev)
        return ev

class JobRegistry:
    def __init__(self):
        self._jobs: Dict[str, JobState] = {}

    def create(self, job_type: JobType) -> JobState:
        jid = uuid.uuid4().hex[:12]
        st = JobState(id=jid, type=job_type)
        self._jobs[jid] = st
        return st

    def get(self, jid: str) -> Optional[JobState]:
        return self._jobs.get(jid)

JOBS = JobRegistry()
