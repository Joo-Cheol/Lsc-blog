from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from api.core.jobs import JOBS
import json
import asyncio

router = APIRouter()

@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "job": job.__dict__}

@router.get("/jobs/{job_id}/events")
async def stream_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return StreamingResponse(iter(["event: error\ndata: {\"error\": \"not_found\"}\n\n"]), media_type="text/event-stream")

    async def eventgen():
        cursor = 0
        yield f"event: snapshot\ndata: {json.dumps({'job': job.__dict__})}\n\n"
        while True:
            await asyncio.sleep(0.5)
            if job.status in ("succeeded", "failed"):
                yield f"event: done\ndata: {json.dumps({'job': job.__dict__})}\n\n"
                break
            # push incremental events
            while cursor < len(job.events):
                ev = job.events[cursor]
                cursor += 1
                yield f"event: {ev.type}\ndata: {json.dumps(ev.__dict__)}\n\n"

    return StreamingResponse(eventgen(), media_type="text/event-stream")
