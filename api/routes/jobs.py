from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from api.core.jobs import JOBS
import json
import asyncio
import time

router = APIRouter()

@router.get("/jobs/{job_id}")
def get_job(job_id: str, include_events: bool = Query(False)):
    job = JOBS.get(job_id)
    if not job:
        return {"ok": False, "error": "not_found"}
    
    job_dict = {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "progress": job.progress,
        "counters": job.counters,
        "results": job.results,
        "errors": job.errors,
        "created_at": job.created_at,
        "last_accessed_at": job.last_accessed_at
    }
    
    if include_events:
        job_dict["events"] = [ev.__dict__ for ev in job.events]
    
    return {"ok": True, "job": job_dict}

@router.get("/jobs/{job_id}/events")
async def stream_job(job_id: str, since: int = Query(0)):
    job = JOBS.get(job_id)
    if not job:
        return StreamingResponse(iter(["event: error\ndata: {\"error\": \"not_found\"}\n\n"]), media_type="text/event-stream")

    async def eventgen():
        # SSE 헤더 설정
        yield "retry: 3000\n"  # 3초 재연결 지연
        yield "cache-control: no-cache\n"
        yield "connection: keep-alive\n\n"
        
        # 초기 스냅샷 (since 파라미터가 있으면 해당 시점 이후 이벤트만)
        if since > 0:
            # 재연결: since 이후 이벤트만 전송
            events_since = job.get_events_since(since)
            for ev in events_since:
                yield f"event: {ev.type}\ndata: {json.dumps(ev.__dict__)}\n\n"
        else:
            # 첫 연결: 전체 스냅샷
            job_dict = {
                "id": job.id,
                "type": job.type,
                "status": job.status,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
                "progress": job.progress,
                "counters": job.counters,
                "results": job.results,
                "errors": job.errors
            }
            yield f"event: snapshot\ndata: {json.dumps({'job': job_dict})}\n\n"
        
        # 실시간 이벤트 스트림
        last_event_id = since
        heartbeat_counter = 0
        
        while True:
            await asyncio.sleep(0.5)
            
            # Job 완료 체크
            if job.status in ("succeeded", "failed"):
                yield f"event: done\ndata: {json.dumps({'job': {'status': job.status, 'results': job.results}})}\n\n"
                break
            
            # 새로운 이벤트 체크
            new_events = job.get_events_since(last_event_id)
            for ev in new_events:
                yield f"event: {ev.type}\ndata: {json.dumps(ev.__dict__)}\n\n"
                last_event_id = ev.event_id
            
            # Heartbeat (15초마다)
            heartbeat_counter += 1
            if heartbeat_counter >= 30:  # 0.5초 * 30 = 15초
                yield f"event: ping\ndata: {json.dumps({'timestamp': time.time()})}\n\n"
                heartbeat_counter = 0

    return StreamingResponse(
        eventgen(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )
