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
from monitoring.job_metrics import job_metrics

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
            
            # 실제 전처리 로직
            from src.preprocess.text_normalizer import TextNormalizer
            from src.preprocess.semantic_chunker import SemanticChunker
            
            normalizer = TextNormalizer()
            chunker = SemanticChunker(
                chunk_size=request.chunk_size or 1000,
                chunk_overlap=request.chunk_overlap or 200
            )
            
            # 크롤링된 포스트 데이터 로드
            from src.crawler.storage import CrawlerStorage
            storage = CrawlerStorage()
            posts = storage.get_recent_posts(limit=1000)  # 최근 1000개 포스트
            
            if not posts:
                st.add_error("NO_DATA", "처리할 데이터가 없습니다.", "먼저 블로그를 크롤링해주세요.")
                st.status = "failed"
                st.finished_at = datetime.utcnow().isoformat()
                return
            
            st.push("info", f"{len(posts)}개 포스트 로드 완료")
            
            # 2. 청킹 단계
            st.push("progress", "텍스트 청킹 중...")
            st.progress = 0.3
            
            chunks_created = 0
            processed_posts = 0
            
            for post in posts:
                # 텍스트 정규화
                normalized_text = normalizer.normalize(post.get('content', ''))
                if not normalized_text or len(normalized_text) < 100:
                    continue
                
                # 청킹
                chunks = chunker.chunk(normalized_text)
                chunks_created += len(chunks)
                processed_posts += 1
                
                # 진행률 업데이트
                if processed_posts % 10 == 0:
                    progress = 0.3 + (processed_posts / len(posts)) * 0.3
                    st.progress = min(progress, 0.6)
                    st.push("info", f"청킹 진행: {processed_posts}/{len(posts)} 포스트, {chunks_created}개 청크")
            
            st.counters["found"] = chunks_created
            st.push("info", f"{chunks_created}개 청크 생성 완료 ({processed_posts}개 포스트 처리)")
            
            # 3. 임베딩 단계
            st.push("progress", "임베딩 생성 중...")
            st.progress = 0.6
            
            # 실제 임베딩 생성
            from src.vector.embedder import EmbeddingService
            from src.vector.chroma_index import ChromaIndex
            
            embedder = EmbeddingService(
                model_name=request.model_name or "sentence-transformers/all-MiniLM-L6-v2",
                batch_size=request.batch_size or 32
            )
            
            chroma_index = ChromaIndex(collection_name="legal_documents")
            
            embeddings_added = 0
            cache_hits = 0
            
            # 배치 단위로 임베딩 생성 및 저장
            batch_size = request.batch_size or 32
            for i in range(0, chunks_created, batch_size):
                batch_chunks = list(range(i, min(i + batch_size, chunks_created)))
                
                # 임베딩 생성 (캐시 활용)
                embeddings = embedder.get_or_compute_batch(batch_chunks)
                embeddings_added += len(embeddings)
                
                # ChromaDB 업서트
                upsert_result = chroma_index.upsert_chunks(embeddings)
                
                # 진행률 업데이트
                progress = 0.6 + (i / chunks_created) * 0.3
                st.progress = min(progress, 0.9)
                st.push("info", f"임베딩 진행: {embeddings_added}/{chunks_created}개")
            
            st.counters["new"] = embeddings_added
            
            # 4. ChromaDB 업서트 완료
            st.push("progress", "ChromaDB 저장 완료")
            st.progress = 0.9
            
            # 캐시 히트율 계산
            cache_stats = embedder.get_cache_stats()
            cache_hit_rate = cache_stats.get("hit_rate", 0.0)
            
            # 컬렉션 정보 조회
            collection_info = chroma_index.get_collection_info()
            total_items_in_collection = collection_info.get("total_items", embeddings_added)
            
            st.push("info", f"ChromaDB 저장 완료: {total_items_in_collection}개 항목")
            
            # 완료 - 상세 결과 저장
            st.results.update({
                "chunks_created": chunks_created,
                "embeddings_added": embeddings_added,
                "cache_hit_rate": cache_hit_rate,
                "collection_name": "legal_documents",
                "total_items": total_items_in_collection,
                "processed_posts": processed_posts,
                "posts_loaded": len(posts),
                "upsert_result": upsert_result if 'upsert_result' in locals() else {},
                "embedding_model": request.model_name or "sentence-transformers/all-MiniLM-L6-v2",
                "chunk_size": request.chunk_size or 1000,
                "batch_size": request.batch_size or 32
            })
            
            st.progress = 1.0
            st.status = "succeeded"
            st.finished_at = datetime.utcnow().isoformat()
            st.push("done", "검색 준비 완료", total_chunks=embeddings_added)
            
            # 비즈니스 이벤트 로깅
            duration_ms = int((datetime.utcnow() - datetime.fromisoformat(st.started_at)).total_seconds() * 1000)
            log_business_event(
                "pipeline_completed",
                run_id=st.id,
                task=request.task,
                chunks_created=chunks_created,
                embeddings_added=embeddings_added,
                duration_ms=duration_ms
            )
            
            # 메트릭 기록
            job_metrics.record_operation("preprocess_embed", duration_ms, success=True)
            job_metrics.record_job_completion("preprocess_embed", duration_ms, success=True)
            
        except Exception as e:
            logger.error(f"파이프라인 실행 중 오류 발생: {e}", exc_info=True)
            st.status = "failed"
            st.add_error("PIPELINE_FAILED", str(e), "데이터 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            st.finished_at = datetime.utcnow().isoformat()
            st.push("error", f"파이프라인 실패: {str(e)}")
            
            # 실패 메트릭 기록
            if st.started_at:
                duration_ms = int((datetime.utcnow() - datetime.fromisoformat(st.started_at)).total_seconds() * 1000)
                job_metrics.record_operation("preprocess_embed", duration_ms, success=False)
                job_metrics.record_job_completion("preprocess_embed", duration_ms, success=False)
    
    bg.add_task(run)
    return {"ok": True, "job_id": job.id}

@router.post("/run")
async def run_pipeline(request: PipelineRequest, bg: BackgroundTasks):
    """파이프라인 실행 (호환성 엔드포인트)"""
    if request.task == "preprocess_embed":
        return await preprocess_embed(request, bg)
    else:
        return {"ok": False, "error": f"알 수 없는 파이프라인 태스크: {request.task}"}