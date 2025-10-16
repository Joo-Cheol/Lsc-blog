#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Provider 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM 응답 데이터 클래스"""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """LLM Provider 기본 클래스"""
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.config = kwargs
    
    @abstractmethod
    def generate(self, 
                 prompt: str, 
                 system: Optional[str] = None, 
                 max_tokens: int = 1024,
                 temperature: float = 0.7,
                 **kwargs) -> LLMResponse:
        """텍스트 생성"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Provider 사용 가능 여부 확인"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 조회"""
        pass
    
    def validate_config(self) -> bool:
        """설정 검증"""
        return True
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name})"
    
    def __repr__(self) -> str:
        return self.__str__()


class LLMProviderError(Exception):
    """LLM Provider 오류"""
    pass


class LLMProviderTimeoutError(LLMProviderError):
    """LLM Provider 타임아웃 오류"""
    pass


class LLMProviderRateLimitError(LLMProviderError):
    """LLM Provider 속도 제한 오류"""
    pass


class LLMProviderAuthError(LLMProviderError):
    """LLM Provider 인증 오류"""
    pass
