#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트 설정 관리
"""
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

class Settings(BaseModel):
    """애플리케이션 설정"""
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    BRAND_TONE: str = os.getenv(
        "BRAND_TONE", "법무법인 혜안 톤, 채권자 관점, 합법·절차 중심, 한국어"
    )
    
    # 비용/레이트 가드 (선언만 해두고 추후 사용)
    DAILY_TOKEN_LIMIT: int = int(os.getenv("DAILY_TOKEN_LIMIT", "0"))  # 0=off
    REQUEST_TIMEOUT_S: float = float(os.getenv("REQUEST_TIMEOUT_S", "20"))
    
    # 데이터 경로
    DATA_DIR: str = os.getenv("DATA_DIR", "artifacts")
    PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # RAG 설정
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-base")
    CHROMA_DIR: str = os.getenv("CHROMA_DIR", "./artifacts/chroma")
    CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "law_blog")
    RETRIEVAL_K: int = int(os.getenv("RETRIEVAL_K", "8"))
    CAND_MULTIPLIER: int = int(os.getenv("CAND_MULTIPLIER", "3"))
    USE_BM25: bool = os.getenv("USE_BM25", "false").lower() == "true"
    
    # 하이브리드 검색 설정
    RETRIEVAL_ALPHA: float = float(os.getenv("RETRIEVAL_ALPHA", "0.2"))  # BM25 가중치
    MMR_LAMBDA: float = float(os.getenv("MMR_LAMBDA", "0.7"))  # MMR 다양화 가중치

# 전역 설정 인스턴스
settings = Settings()
