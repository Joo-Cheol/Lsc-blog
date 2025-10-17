#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
생성 API 라우터
"""
import sys
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.schemas import GenerateRequest, GenerateResponse, QualityResult
from api.core.logging import get_logger, log_business_event
from api.core.config import get_settings

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/generate", response_model=GenerateResponse)
async def generate_content(request: GenerateRequest):
    """콘텐츠 생성"""
    start_time = time.time()
    
    try:
        logger.info(f"콘텐츠 생성 시작: {request.query}")
        
        # LLM Provider 초기화
        from src.llm.provider_manager import get_provider_manager
        
        provider_manager = get_provider_manager()
        
        # Provider 선택
        if request.provider:
            provider = provider_manager.get_provider(request.provider.value)
        else:
            provider = provider_manager.get_provider()
        
        # 검색 서비스 초기화 (RAG 사용 시)
        context_docs = []
        if request.with_rag:
            from src.search.search_service import SearchService
            from src.vector.simple_index import SimpleVectorIndex
            from src.vector.embedder import EmbeddingCache
            from src.vector.reranker import CrossEncoderReranker
            
            embedder = EmbeddingCache(
                model_name=settings.embed_model
            )
            
            index = SimpleVectorIndex(
                persist_directory=settings.chroma_dir,
                embedding_service=embedder
            )
            
            reranker = CrossEncoderReranker(
                model_name=settings.rerank_model
            )
            
            search_service = SearchService(
                index_name="naver_blog_debt_collection",
                index_directory=settings.chroma_dir,
                top_k_first=settings.topk_first,
                top_k_final=settings.topk_final
            )
            
            # 컨텍스트 문서 검색
            context_docs = search_service.search(
                query=request.query,
                top_k=3,
                law_topic="채권추심",
                use_rerank=True
            )
        
        # 품질 가드 초기화
        from src.llm.quality_guard import AutoRegenerateLoop
        from src.llm.prompts import PromptConfig
        
        prompt_config = PromptConfig(
            min_chars=settings.gen_min_chars,
            max_chars=settings.gen_max_chars,
            min_subheadings=settings.gen_min_subheadings,
            require_checklist=settings.gen_require_checklist,
            require_disclaimer=settings.gen_require_disclaimer
        )
        
        # 자동 재생성 루프 초기화
        regenerate_loop = AutoRegenerateLoop(
            llm_provider=provider,
            searcher=search_service if request.with_rag else None,
            config=prompt_config,
            max_retries=request.max_retries
        )
        
        # 콘텐츠 생성
        if request.with_rag and context_docs:
            content, quality_result = regenerate_loop.generate_with_quality_guard(request.query)
        else:
            # RAG 없이 직접 생성
            from src.llm.prompts import build_hyean_prompt
            
            system_prompt, user_prompt = build_hyean_prompt(
                query=request.query,
                context_docs=context_docs,
                config=prompt_config
            )
            
            response = provider.generate(
                prompt=user_prompt,
                system=system_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            content = response.content
            
            # 품질 검증
            from src.llm.quality_guard import QualityGuard
            quality_guard = QualityGuard(prompt_config)
            quality_result = quality_guard.check_content_quality(content)
        
        # 실행 시간 계산
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "generate_completed",
            query=request.query,
            with_rag=request.with_rag,
            provider_used=provider.model_name,
            quality_passed=quality_result.passed,
            retries=quality_result.retries,
            context_docs_count=len(context_docs),
            duration_ms=duration_ms
        )
        
        logger.info(f"콘텐츠 생성 완료: 품질 통과={quality_result.passed}, 재시도={quality_result.retries}")
        
        return GenerateResponse(
            success=True,
            content=content,
            quality_result=QualityResult(
                passed=quality_result.passed,
                reasons=quality_result.reasons,
                scores=quality_result.scores,
                retries=quality_result.retries
            ),
            provider_used=provider.model_name,
            context_docs_count=len(context_docs),
            duration_ms=duration_ms,
            message="콘텐츠가 성공적으로 생성되었습니다." if quality_result.passed else "콘텐츠가 생성되었지만 품질 검증을 통과하지 못했습니다."
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"콘텐츠 생성 실패: {e}", exc_info=True)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "generate_failed",
            query=request.query,
            error=str(e),
            duration_ms=duration_ms
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"콘텐츠 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/generate/validate")
async def validate_content(content: str):
    """콘텐츠 품질 검증"""
    try:
        from src.llm.quality_guard import QualityGuard
        from src.llm.prompts import PromptConfig
        
        prompt_config = PromptConfig(
            min_chars=settings.gen_min_chars,
            max_chars=settings.gen_max_chars,
            min_subheadings=settings.gen_min_subheadings,
            require_checklist=settings.gen_require_checklist,
            require_disclaimer=settings.gen_require_disclaimer
        )
        
        quality_guard = QualityGuard(prompt_config)
        quality_result = quality_guard.check_content_quality(content)
        
        return {
            "success": True,
            "quality_result": QualityResult(
                passed=quality_result.passed,
                reasons=quality_result.reasons,
                scores=quality_result.scores,
                retries=quality_result.retries
            ),
            "message": "품질 검증이 완료되었습니다"
        }
        
    except Exception as e:
        logger.error(f"품질 검증 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"품질 검증 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/generate/templates")
async def get_generation_templates():
    """생성 템플릿 조회"""
    try:
        from src.llm.prompts import PromptTemplates
        
        templates = PromptTemplates.get_chaequan_chusim_prompts()
        phrases = PromptTemplates.get_common_phrases()
        checklists = PromptTemplates.get_checklist_templates()
        
        return {
            "success": True,
            "templates": {
                "system_prompt": templates["system"],
                "user_template": templates["user_template"],
                "common_phrases": phrases,
                "checklists": checklists
            },
            "message": "생성 템플릿을 성공적으로 조회했습니다"
        }
        
    except Exception as e:
        logger.error(f"생성 템플릿 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"생성 템플릿 조회 중 오류가 발생했습니다: {str(e)}"
        )
