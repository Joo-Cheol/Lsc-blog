#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 스키마 정의
"""
from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class ProviderType(str, Enum):
    """LLM Provider 타입"""
    GEMINI = "gemini"
    OLLAMA = "ollama"


class CrawlRequest(BaseModel):
    """크롤링 요청 스키마"""
    blog_url: Optional[HttpUrl] = Field(None, description="네이버 블로그 URL (새 UX)")
    blog_id: Optional[str] = Field(None, description="네이버 블로그 ID (구버전 호환)")
    category_no: Optional[int] = Field(None, description="카테고리 번호 (미지정 시 전체)")
    max_pages: Optional[int] = Field(None, description="최대 페이지 수 (미지정 시 끝까지)")
    
    @validator('blog_id')
    def validate_blog_id(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('blog_id는 비어있을 수 없습니다')
        return v.strip() if v else v
    
    @validator('category_no')
    def validate_category_no(cls, v):
        if v is not None and v < 0:
            raise ValueError('category_no는 0 이상이어야 합니다')
        return v
    
    @validator('max_pages')
    def validate_max_pages(cls, v):
        if v is not None and (v < 1 or v > 50):
            raise ValueError('max_pages는 1 이상 50 이하여야 합니다')
        return v


class CrawlResponse(BaseModel):
    """크롤링 응답 스키마"""
    success: bool = Field(..., description="성공 여부")
    run_id: str = Field(..., description="실행 ID")
    crawled_count: int = Field(..., description="크롤링된 포스트 수")
    skipped_count: int = Field(..., description="스킵된 포스트 수")
    failed_count: int = Field(..., description="실패한 포스트 수")
    last_logno_updated: Optional[str] = Field(None, description="마지막 logno")
    duration_ms: int = Field(..., description="실행 시간 (밀리초)")
    message: Optional[str] = Field(None, description="추가 메시지")
    blog_id: Optional[str] = Field(None, description="블로그 ID")
    collected_posts: Optional[List[Dict[str, Any]]] = Field(None, description="수집된 글 목록")


class IndexRequest(BaseModel):
    """인덱싱 요청 스키마"""
    run_id: str = Field(..., description="실행 ID")
    force_reindex: Optional[bool] = Field(False, description="강제 재인덱싱 여부")
    
    @validator('run_id')
    def validate_run_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('run_id는 비어있을 수 없습니다')
        return v.strip()


class IndexResponse(BaseModel):
    """인덱싱 응답 스키마"""
    success: bool = Field(..., description="성공 여부")
    run_id: str = Field(..., description="실행 ID")
    added_count: int = Field(..., description="추가된 청크 수")
    skipped_count: int = Field(..., description="스킵된 청크 수")
    total_chunks: int = Field(..., description="전체 청크 수")
    duration_ms: int = Field(..., description="실행 시간 (밀리초)")
    message: Optional[str] = Field(None, description="추가 메시지")


class SearchRequest(BaseModel):
    """검색 요청 스키마"""
    query: str = Field(..., description="검색 쿼리", min_length=1, max_length=500)
    top_k: Optional[int] = Field(6, description="반환할 결과 수", ge=1, le=20)
    with_rerank: Optional[bool] = Field(True, description="리랭킹 사용 여부")
    law_topic: Optional[str] = Field("채권추심", description="법률 주제 필터")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('query는 비어있을 수 없습니다')
        return v.strip()


class SearchResult(BaseModel):
    """검색 결과 스키마"""
    text: str = Field(..., description="청크 텍스트")
    score: float = Field(..., description="유사도 점수")
    metadata: Dict[str, Any] = Field(..., description="메타데이터")
    source_url: Optional[str] = Field(None, description="원본 URL")
    published_at: Optional[str] = Field(None, description="발행일")


class SearchResponse(BaseModel):
    """검색 응답 스키마"""
    success: bool = Field(..., description="성공 여부")
    query: str = Field(..., description="검색 쿼리")
    results: List[SearchResult] = Field(..., description="검색 결과")
    total_results: int = Field(..., description="전체 결과 수")
    with_rerank: bool = Field(..., description="리랭킹 사용 여부")
    duration_ms: int = Field(..., description="실행 시간 (밀리초)")
    suggestions: Optional[List[str]] = Field(None, description="검색 제안")


class GenerateRequest(BaseModel):
    """생성 요청 스키마"""
    query: str = Field(..., description="생성 쿼리", min_length=1, max_length=500)
    with_rag: Optional[bool] = Field(True, description="RAG 사용 여부")
    provider: Optional[ProviderType] = Field(None, description="LLM Provider")
    max_tokens: Optional[int] = Field(2000, description="최대 토큰 수", ge=100, le=4000)
    temperature: Optional[float] = Field(0.7, description="생성 온도", ge=0.0, le=2.0)
    max_retries: Optional[int] = Field(2, description="최대 재시도 횟수", ge=0, le=5)
    
    @validator('query')
    def validate_query(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('query는 비어있을 수 없습니다')
        return v.strip()


class QualityResult(BaseModel):
    """품질 검증 결과 스키마"""
    passed: bool = Field(..., description="통과 여부")
    reasons: List[str] = Field(..., description="실패 이유")
    scores: Dict[str, str] = Field(..., description="점수 상세")
    retries: int = Field(..., description="재시도 횟수")


class GenerateResponse(BaseModel):
    """생성 응답 스키마"""
    success: bool = Field(..., description="성공 여부")
    content: str = Field(..., description="생성된 콘텐츠")
    quality_result: QualityResult = Field(..., description="품질 검증 결과")
    provider_used: str = Field(..., description="사용된 Provider")
    context_docs_count: int = Field(..., description="사용된 컨텍스트 문서 수")
    duration_ms: int = Field(..., description="실행 시간 (밀리초)")
    message: Optional[str] = Field(None, description="추가 메시지")


class UploadRequest(BaseModel):
    """업로드 요청 스키마"""
    title: str = Field(..., description="포스트 제목", min_length=1, max_length=200)
    content: str = Field(..., description="포스트 내용", min_length=100)
    tags: Optional[List[str]] = Field([], description="태그 목록", max_items=10)
    auto_upload: Optional[bool] = Field(False, description="자동 업로드 여부")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('title은 비어있을 수 없습니다')
        return v.strip()
    
    @validator('content')
    def validate_content(cls, v):
        if not v or len(v.strip()) < 100:
            raise ValueError('content는 최소 100자 이상이어야 합니다')
        return v.strip()
    
    @validator('tags')
    def validate_tags(cls, v):
        if v is None:
            return []
        # 태그 길이 제한
        validated_tags = []
        for tag in v:
            if tag and len(tag.strip()) > 0:
                validated_tags.append(tag.strip()[:20])  # 최대 20자
        return validated_tags


class UploadResponse(BaseModel):
    """업로드 응답 스키마"""
    success: bool = Field(..., description="성공 여부")
    post_url: Optional[str] = Field(None, description="업로드된 포스트 URL")
    upload_id: Optional[str] = Field(None, description="업로드 ID")
    duration_ms: int = Field(..., description="실행 시간 (밀리초)")
    message: Optional[str] = Field(None, description="추가 메시지")


class HealthResponse(BaseModel):
    """헬스 체크 응답 스키마"""
    status: str = Field(..., description="서비스 상태")
    timestamp: datetime = Field(..., description="체크 시간")
    version: str = Field(..., description="서비스 버전")
    providers: Dict[str, Dict[str, Any]] = Field(..., description="Provider 상태")
    database: Dict[str, Any] = Field(..., description="데이터베이스 상태")
    uptime_seconds: int = Field(..., description="가동 시간 (초)")


class ErrorResponse(BaseModel):
    """오류 응답 스키마"""
    success: bool = Field(False, description="성공 여부")
    error: str = Field(..., description="오류 메시지")
    error_code: Optional[str] = Field(None, description="오류 코드")
    details: Optional[Dict[str, Any]] = Field(None, description="오류 상세")
    timestamp: datetime = Field(default_factory=datetime.now, description="오류 발생 시간")


class StatsResponse(BaseModel):
    """통계 응답 스키마"""
    success: bool = Field(..., description="성공 여부")
    total_posts: int = Field(..., description="전체 포스트 수")
    total_chunks: int = Field(..., description="전체 청크 수")
    total_searches: int = Field(..., description="전체 검색 수")
    total_generations: int = Field(..., description="전체 생성 수")
    last_crawl: Optional[datetime] = Field(None, description="마지막 크롤링 시간")
    last_index: Optional[datetime] = Field(None, description="마지막 인덱싱 시간")
    provider_stats: Dict[str, Dict[str, Any]] = Field(..., description="Provider 통계")


class ConfigResponse(BaseModel):
    """설정 응답 스키마"""
    success: bool = Field(..., description="성공 여부")
    llm_provider: str = Field(..., description="현재 LLM Provider")
    available_providers: List[str] = Field(..., description="사용 가능한 Provider 목록")
    embed_model: str = Field(..., description="임베딩 모델")
    rerank_model: str = Field(..., description="리랭킹 모델")
    upload_enabled: bool = Field(..., description="업로드 활성화 여부")
    max_pages_per_crawl: int = Field(..., description="크롤링 최대 페이지 수")
    quality_guard_enabled: bool = Field(..., description="품질 가드 활성화 여부")


# 요청/응답 예시
class ExampleResponses:
    """API 응답 예시"""
    
    CRAWL_SUCCESS = {
        "success": True,
        "run_id": "20250114_143022",
        "crawled_count": 5,
        "skipped_count": 2,
        "failed_count": 0,
        "last_logno_updated": "12345",
        "duration_ms": 1500,
        "message": "크롤링이 성공적으로 완료되었습니다."
    }
    
    SEARCH_SUCCESS = {
        "success": True,
        "query": "채권추심 절차",
        "results": [
            {
                "text": "채권추심은 내용증명 발송부터 시작됩니다...",
                "score": 0.95,
                "metadata": {
                    "source_url": "https://blog.naver.com/post/123",
                    "published_at": "2024.01.01",
                    "law_topic": "채권추심"
                },
                "source_url": "https://blog.naver.com/post/123",
                "published_at": "2024.01.01"
            }
        ],
        "total_results": 1,
        "with_rerank": True,
        "duration_ms": 250,
        "suggestions": ["채권추심 비용", "지급명령 신청"]
    }
    
    GENERATE_SUCCESS = {
        "success": True,
        "content": "# 채권추심 절차 가이드\n\n## 들어가는 글\n채권 회수에 어려움을 겪고 계신가요?...",
        "quality_result": {
            "passed": True,
            "reasons": [],
            "scores": {
                "length": "통과",
                "subheadings": "통과",
                "checklist": "통과",
                "disclaimer": "통과",
                "structure": "통과",
                "tone": "통과"
            },
            "retries": 0
        },
        "provider_used": "ollama",
        "context_docs_count": 3,
        "duration_ms": 3500,
        "message": "품질 검증을 통과한 콘텐츠가 생성되었습니다."
    }
    
    ERROR_RESPONSE = {
        "success": False,
        "error": "Provider를 사용할 수 없습니다",
        "error_code": "PROVIDER_UNAVAILABLE",
        "details": {
            "provider": "ollama",
            "reason": "서버 연결 실패"
        },
        "timestamp": "2025-01-14T14:30:22Z"
    }
