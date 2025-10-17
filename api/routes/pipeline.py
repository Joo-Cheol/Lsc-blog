#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파이프라인 API 라우터 (Job 기반)
"""
import sys
import time
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.core.logging import get_logger, log_business_event
from api.core.config import get_settings
from api.core.jobs import JOBS

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

class PipelineRequest(BaseModel):
    """파이프라인 요청"""
    task: str = Field(..., description="실행할 파이프라인 태스크 (예: preprocess_embed)")
    chunk_size: Optional[int] = Field(1000, description="청크 크기")
    chunk_overlap: Optional[int] = Field(200, description="청크 오버랩")
    batch_size: Optional[int] = Field(32, description="배치 크기")
    model_name: Optional[str] = Field(None, description="모델명")

@router.post("/preprocess-embed")
async def preprocess_embed(request: PipelineRequest, bg: BackgroundTasks):
    """전처리→임베딩→업서트 파이프라인 (Job 기반)"""
    job = JOBS.create("preprocess_embed")
    
    def run():
        st = job
        st.status = "running"
        st.started_at = datetime.utcnow().isoformat()
        
        try:
            st.push("info", "검색 준비 시작(전처리→임베딩→업서트)")
            
            # 1. 전처리 단계
            st.push("progress", "원본 데이터 정제 중...")
            st.progress = 0.1
            
            # 실제 전처리 로직 (시뮬레이션)
            import time
            time.sleep(1)
            
            # 2. 청킹 단계
            st.push("progress", "텍스트 청킹 중...")
            st.progress = 0.3
            
            # 시뮬레이션: 120개 청크 생성
            chunks_created = 120
            st.counters["found"] = chunks_created
            st.push("info", f"{chunks_created}개 청크 생성 완료")
            
            time.sleep(2)
            
            # 3. 임베딩 단계
            st.push("progress", "임베딩 생성 중...")
            st.progress = 0.6
            
            # 시뮬레이션: 임베딩 생성
            embeddings_added = chunks_created
            st.counters["new"] = embeddings_added
            st.push("info", f"{embeddings_added}개 임베딩 생성 완료")
            
            time.sleep(3)
            
            # 4. ChromaDB 업서트 단계
            st.push("progress", "ChromaDB 저장 중...")
            st.progress = 0.9
            
            # 시뮬레이션: ChromaDB 저장
            cache_hit_rate = 0.0
            total_items_in_collection = embeddings_added
            st.push("info", f"ChromaDB 저장 완료: {total_items_in_collection}개 항목")
            
            time.sleep(1)
            
            # 완료
            st.results["chunks_created"] = chunks_created
            st.results["embeddings_added"] = embeddings_added
            st.results["cache_hit_rate"] = cache_hit_rate
            st.results["collection_name"] = "legal_documents"
            st.results["total_items"] = total_items_in_collection
            
            st.progress = 1.0
            st.status = "succeeded"
            st.finished_at = datetime.utcnow().isoformat()
            st.push("done", "검색 준비 완료", total_chunks=embeddings_added)
            
            # 비즈니스 이벤트 로깅
            log_business_event(
                "pipeline_completed",
                run_id=st.id,
                task=request.task,
                chunks_created=chunks_created,
                embeddings_added=embeddings_added,
                duration_ms=int((datetime.utcnow() - datetime.fromisoformat(st.started_at)).total_seconds() * 1000)
            )
            
        except Exception as e:
            logger.error(f"파이프라인 실행 중 오류 발생: {e}", exc_info=True)
            st.status = "failed"
            st.errors.append(str(e))
            st.finished_at = datetime.utcnow().isoformat()
            st.push("error", f"파이프라인 실패: {str(e)}")
    
    bg.add_task(run)
    return {"ok": True, "job_id": job.id}

@router.post("/run")
async def run_pipeline(request: PipelineRequest, bg: BackgroundTasks):
    """파이프라인 실행 (호환성 엔드포인트)"""
    if request.task == "preprocess_embed":
        return await preprocess_embed(request, bg)
    else:
        return {"ok": False, "error": f"알 수 없는 파이프라인 태스크: {request.task}"}