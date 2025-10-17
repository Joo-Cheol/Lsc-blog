#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파이프라인 API 라우터
"""
import sys
import time
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.core.logging import get_logger, log_business_event
from api.core.config import get_settings

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

# 파이프라인 상태 저장 (실제로는 Redis나 DB 사용 권장)
pipeline_status = {}

class PipelineRequest(BaseModel):
    """파이프라인 요청"""
    task: str
    chunk_size: Optional[int] = 1000
    chunk_overlap: Optional[int] = 200
    batch_size: Optional[int] = 32
    model_name: Optional[str] = None

class PipelineResponse(BaseModel):
    """파이프라인 응답"""
    success: bool
    task: str
    task_id: str
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None

class PipelineStatusResponse(BaseModel):
    """파이프라인 상태 응답"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: int  # 0-100
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

async def run_preprocess_embed_task(task_id: str, request: PipelineRequest):
    """전처리 + 임베딩 백그라운드 태스크"""
    try:
        pipeline_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "전처리 시작...",
            "result": None,
            "error": None
        }
        
        # 1. 전처리 단계
        pipeline_status[task_id].update({
            "progress": 25,
            "message": "원본 데이터 정제 중..."
        })
        
        # 실제 전처리 로직 (시뮬레이션)
        await asyncio.sleep(2)  # 실제로는 파일 읽기, 정규화, 청킹
        
        chunks_created = 120  # 시뮬레이션
        
        pipeline_status[task_id].update({
            "progress": 50,
            "message": f"청크 {chunks_created}개 생성 완료"
        })
        
        # 2. 임베딩 단계
        pipeline_status[task_id].update({
            "progress": 75,
            "message": "벡터 임베딩 생성 중..."
        })
        
        # 실제 임베딩 로직 (시뮬레이션)
        await asyncio.sleep(3)  # 실제로는 임베딩 모델 실행
        
        embeddings_added = chunks_created
        cache_hit_rate = 0.0  # 시뮬레이션
        
        # 완료
        pipeline_status[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": "전처리 및 임베딩 완료",
            "result": {
                "chunks_created": chunks_created,
                "embeddings_added": embeddings_added,
                "cache_hit_rate": cache_hit_rate,
                "collection_name": "legal_documents",
                "total_items": embeddings_added
            }
        })
        
        logger.info(f"파이프라인 완료: {task_id}")
        
    except Exception as e:
        pipeline_status[task_id] = {
            "status": "failed",
            "progress": 0,
            "message": "파이프라인 실행 실패",
            "result": None,
            "error": str(e)
        }
        logger.error(f"파이프라인 실패: {task_id} - {e}", exc_info=True)

@router.post("/pipeline/preprocess-embed", response_model=PipelineResponse)
async def run_preprocess_embed(request: PipelineRequest, background_tasks: BackgroundTasks):
    """전처리 + 임베딩 파이프라인 실행"""
    start_time = time.time()
    task_id = f"preprocess_embed_{int(time.time())}"
    
    try:
        logger.info(f"파이프라인 시작: {request.task} - {task_id}")
        
        # 백그라운드 태스크 시작
        background_tasks.add_task(run_preprocess_embed_task, task_id, request)
        
        # 초기 상태 설정
        pipeline_status[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "파이프라인 대기 중...",
            "result": None,
            "error": None
        }
        
        # 실행 시간 계산
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "pipeline_started",
            run_id=task_id,
            task=request.task,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            batch_size=request.batch_size,
            duration_ms=duration_ms
        )
        
        return PipelineResponse(
            success=True,
            task=request.task,
            task_id=task_id,
            status="pending",
            message="파이프라인이 시작되었습니다. 상태를 확인해주세요."
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"파이프라인 시작 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"파이프라인 시작 실패: {str(e)}"
        )

@router.get("/pipeline/status/{task_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(task_id: str):
    """파이프라인 상태 조회"""
    try:
        if task_id not in pipeline_status:
            raise HTTPException(
                status_code=404,
                detail=f"태스크 ID를 찾을 수 없습니다: {task_id}"
            )
        
        status_data = pipeline_status[task_id]
        
        return PipelineStatusResponse(
            task_id=task_id,
            status=status_data["status"],
            progress=status_data["progress"],
            message=status_data["message"],
            result=status_data["result"],
            error=status_data["error"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상태 조회 실패: {task_id} - {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"상태 조회 실패: {str(e)}"
        )

@router.post("/pipeline/run", response_model=PipelineResponse)
async def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """범용 파이프라인 실행"""
    if request.task == "preprocess_embed":
        return await run_preprocess_embed(request, background_tasks)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 태스크: {request.task}"
        )
