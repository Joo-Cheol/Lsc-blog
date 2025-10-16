"""
생성 파이프라인 설정
"""
import os
from typing import Dict, Any

class Config:
    """생성 파이프라인 설정"""
    
    # 검색 설정
    TOP_K = 8
    CANDIDATE_MULTIPLIER = 3  # 최종 k의 3배
    MIN_SCORE = 0.78
    MMR_LAMBDA = 0.7
    
    # 길이 설정
    DRAFT_MIN_LENGTH = 900
    DRAFT_MAX_LENGTH = 1100
    REWRITE_MIN_LENGTH = 1600
    REWRITE_MAX_LENGTH = 1900
    
    # 표절 검증 임계값
    NGRAM8_THRESHOLD = 0.18
    COSINE_THRESHOLD = 0.85
    SIMHASH_THRESHOLD = 16
    
    # 스타일 검증 임계값
    MIN_SUBHEADINGS = 3
    MIN_TABLES = 1
    MAX_SENTENCES_PER_PARAGRAPH = 4
    TARGET_SENTENCE_LENGTH = (25, 35)
    FORMAL_RATIO_THRESHOLD = 0.7
    
    # 금칙어
    FORBIDDEN_WORDS = ["또한", "더불어", "무료상담", "즉시연락", "100%"]
    
    # 사례 다양성 범위
    AMOUNT_RANGE = (1500000, 6200000)  # 150만원 ~ 620만원
    PERIOD_RANGE = (2, 8)  # 2주 ~ 8주
    REGIONS = ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산"]
    DEBTOR_TYPES = ["개인", "법인", "프리랜서", "소상공인"]
    REACTIONS = ["분할상환", "연락회피", "주소불명", "협조적", "거부적"]
    
    # 표 제목 로테이션
    TABLE_TITLES = [
        "필수 서류", "체크포인트", "유의사항", "준비물", 
        "진행 순서", "점검표", "체크리스트", "준비사항"
    ]
    
    # 타임아웃 설정
    LLM_TIMEOUT = 30
    SEARCH_TIMEOUT = 10
    
    # 폴백 설정
    ENABLE_FALLBACK = True
    MAX_RETRIES = 2
    
    @classmethod
    def get_diversity_config(cls) -> Dict[str, Any]:
        """다양성 설정 반환"""
        return {
            "amount_range": cls.AMOUNT_RANGE,
            "period_range": cls.PERIOD_RANGE,
            "regions": cls.REGIONS,
            "debtor_types": cls.DEBTOR_TYPES,
            "reactions": cls.REACTIONS,
            "table_titles": cls.TABLE_TITLES
        }
    
    @classmethod
    def get_validation_thresholds(cls) -> Dict[str, Any]:
        """검증 임계값 반환"""
        return {
            "ngram8_threshold": cls.NGRAM8_THRESHOLD,
            "cosine_threshold": cls.COSINE_THRESHOLD,
            "simhash_threshold": cls.SIMHASH_THRESHOLD,
            "min_subheadings": cls.MIN_SUBHEADINGS,
            "min_tables": cls.MIN_TABLES,
            "max_sentences_per_paragraph": cls.MAX_SENTENCES_PER_PARAGRAPH,
            "target_sentence_length": cls.TARGET_SENTENCE_LENGTH,
            "formal_ratio_threshold": cls.FORMAL_RATIO_THRESHOLD
        }
    
    @classmethod
    def get_length_limits(cls) -> Dict[str, tuple]:
        """길이 제한 반환"""
        return {
            "draft": (cls.DRAFT_MIN_LENGTH, cls.DRAFT_MAX_LENGTH),
            "rewrite": (cls.REWRITE_MIN_LENGTH, cls.REWRITE_MAX_LENGTH)
        }