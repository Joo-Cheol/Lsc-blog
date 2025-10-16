#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 설정 관리
"""
import os
from typing import Optional, List
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """애플리케이션 설정"""
    
    # 기본 설정
    app_name: str = Field(default="LSC Blog Automation API")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # 서버 설정
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    reload: bool = Field(default=False)
    
    # CORS 설정
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # 크롤링 설정
    naver_blog_id: str = Field(default="tjwlswlsdl")
    naver_category_no: int = Field(default=6)
    crawl_delay_min: int = Field(default=600)
    crawl_delay_max: int = Field(default=1400)
    max_pages_per_crawl: int = Field(default=5)
    
    # 데이터 경로 설정
    data_dir: str = Field(default="./src/data/processed")
    chroma_dir: str = Field(default="./src/data/indexes/default/chroma")
    seen_db: str = Field(default="./src/data/meta/seen.sqlite")
    
    # 임베딩 설정
    embed_model: str = Field(default="intfloat/multilingual-e5-base")
    embed_device: str = Field(default="cuda")
    rerank_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    topk_first: int = Field(default=20)
    topk_final: int = Field(default=6)
    
    # LLM Provider 설정
    llm_provider: str = Field(default="ollama")
    ollama_endpoint: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5:7b-instruct")
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash")
    
    # 생성 품질 가드 설정
    gen_min_chars: int = Field(default=1600)
    gen_max_chars: int = Field(default=1900)
    gen_min_subheadings: int = Field(default=3)
    gen_require_checklist: bool = Field(default=True)
    gen_require_disclaimer: bool = Field(default=True)
    gen_max_retry: int = Field(default=2)
    
    # 업로드 설정
    upload_enabled: bool = Field(default=False)
    upload_rate_limit_sec: int = Field(default=15)
    
    # 로깅 설정
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    
    # 보안 설정
    secret_key: str = Field(default="your-secret-key-here")
    access_token_expire_minutes: int = Field(default=30)
    
    # 성능 설정
    max_workers: int = Field(default=4)
    request_timeout: int = Field(default=30)
    
    @classmethod
    def from_env(cls):
        """환경 변수에서 설정 로드"""
        return cls(
            app_name=os.getenv("APP_NAME", "LSC Blog Automation API"),
            app_version=os.getenv("APP_VERSION", "1.0.0"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            reload=os.getenv("RELOAD", "false").lower() == "true",
            cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
            naver_blog_id=os.getenv("NAVER_BLOG_ID", "tjwlswlsdl"),
            naver_category_no=int(os.getenv("NAVER_CATEGORY_NO", "6")),
            crawl_delay_min=int(os.getenv("CRAWL_DELAY_MS_MIN", "600")),
            crawl_delay_max=int(os.getenv("CRAWL_DELAY_MS_MAX", "1400")),
            max_pages_per_crawl=int(os.getenv("MAX_PAGES_PER_CRAWL", "5")),
            data_dir=os.getenv("DATA_DIR", "./src/data/processed"),
            chroma_dir=os.getenv("CHROMA_DIR", "./src/data/indexes/default/chroma"),
            seen_db=os.getenv("SEEN_DB", "./src/data/meta/seen.sqlite"),
            embed_model=os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-base"),
            embed_device=os.getenv("EMBED_DEVICE", "cuda"),
            rerank_model=os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            topk_first=int(os.getenv("TOPK_FIRST", "20")),
            topk_final=int(os.getenv("TOPK_FINAL", "6")),
            llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
            ollama_endpoint=os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            gen_min_chars=int(os.getenv("GEN_MIN_CHARS", "1600")),
            gen_max_chars=int(os.getenv("GEN_MAX_CHARS", "1900")),
            gen_min_subheadings=int(os.getenv("GEN_MIN_SUBHEADINGS", "3")),
            gen_require_checklist=os.getenv("GEN_REQUIRE_CHECKLIST", "true").lower() == "true",
            gen_require_disclaimer=os.getenv("GEN_REQUIRE_DISCLAIMER", "true").lower() == "true",
            gen_max_retry=int(os.getenv("GEN_MAX_RETRY", "2")),
            upload_enabled=os.getenv("UPLOAD_ENABLED", "false").lower() == "true",
            upload_rate_limit_sec=int(os.getenv("UPLOAD_RATE_LIMIT_SEC", "15")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "json"),
            secret_key=os.getenv("SECRET_KEY", "your-secret-key-here"),
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            max_workers=int(os.getenv("MAX_WORKERS", "4")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30"))
        )


# 전역 설정 인스턴스
settings = Settings.from_env()


def get_settings() -> Settings:
    """설정 인스턴스 조회"""
    return settings


def validate_settings() -> List[str]:
    """설정 검증"""
    errors = []
    
    # 필수 설정 검증
    if not settings.naver_blog_id:
        errors.append("NAVER_BLOG_ID가 설정되지 않았습니다")
    
    if settings.naver_category_no < 0:
        errors.append("NAVER_CATEGORY_NO는 0 이상이어야 합니다")
    
    if settings.crawl_delay_min >= settings.crawl_delay_max:
        errors.append("CRAWL_DELAY_MS_MIN은 CRAWL_DELAY_MS_MAX보다 작아야 합니다")
    
    if settings.max_pages_per_crawl <= 0:
        errors.append("MAX_PAGES_PER_CRAWL은 1 이상이어야 합니다")
    
    # LLM Provider 설정 검증
    if settings.llm_provider == "gemini" and not settings.gemini_api_key:
        errors.append("Gemini Provider 사용 시 GEMINI_API_KEY가 필요합니다")
    
    if settings.llm_provider not in ["gemini", "ollama"]:
        errors.append("LLM_PROVIDER는 'gemini' 또는 'ollama'여야 합니다")
    
    # 품질 가드 설정 검증
    if settings.gen_min_chars >= settings.gen_max_chars:
        errors.append("GEN_MIN_CHARS는 GEN_MAX_CHARS보다 작아야 합니다")
    
    if settings.gen_min_subheadings <= 0:
        errors.append("GEN_MIN_SUBHEADINGS는 1 이상이어야 합니다")
    
    if settings.gen_max_retry < 0:
        errors.append("GEN_MAX_RETRY는 0 이상이어야 합니다")
    
    # 업로드 설정 검증
    if settings.upload_enabled and settings.upload_rate_limit_sec <= 0:
        errors.append("UPLOAD_ENABLED가 True일 때 UPLOAD_RATE_LIMIT_SEC는 1 이상이어야 합니다")
    
    return errors


def get_cors_origins() -> List[str]:
    """CORS Origins 조회"""
    if isinstance(settings.cors_origins, str):
        return [origin.strip() for origin in settings.cors_origins.split(",")]
    return settings.cors_origins


def is_development() -> bool:
    """개발 환경 여부 확인"""
    return settings.debug or os.getenv("ENVIRONMENT", "").lower() in ["dev", "development"]


def is_production() -> bool:
    """프로덕션 환경 여부 확인"""
    return os.getenv("ENVIRONMENT", "").lower() in ["prod", "production"]


# 설정 검증 실행
config_errors = validate_settings()
if config_errors:
    print("⚠️ 설정 오류:")
    for error in config_errors:
        print(f"  - {error}")
    print("환경 변수를 확인하고 .env 파일을 업데이트하세요.")
else:
    print("✅ 설정 검증 완료")
