#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini LLM Provider
"""
import os
import time
import logging
from typing import Optional, Dict, Any
from .provider_base import LLMProvider, LLMResponse, LLMProviderError
from .clients.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini LLM Provider"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash", **kwargs):
        super().__init__(model_name, **kwargs)
        
        # API 키 확인
        api_key = kwargs.get('api_key') or os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise LLMProviderError("GEMINI_API_KEY가 설정되지 않았습니다.")
        
        # Gemini 클라이언트 초기화
        try:
            self.client = GeminiClient(model_name=model_name)
            logger.info(f"Gemini Provider 초기화 완료: {model_name}")
        except Exception as e:
            raise LLMProviderError(f"Gemini 클라이언트 초기화 실패: {e}")
    
    def generate(self, 
                 prompt: str, 
                 system: Optional[str] = None, 
                 max_tokens: int = 1024,
                 temperature: float = 0.7,
                 **kwargs) -> LLMResponse:
        """텍스트 생성"""
        try:
            # 시스템 프롬프트와 사용자 프롬프트 결합
            full_prompt = self._combine_prompts(system, prompt)
            
            # Gemini API 호출
            response_text = self.client.generate_text(
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # 사용량 정보 (Gemini는 정확한 토큰 수를 제공하지 않으므로 추정)
            estimated_tokens = len(response_text.split()) * 1.3  # 대략적인 추정
            usage = {
                "prompt_tokens": len(full_prompt.split()) * 1.3,
                "completion_tokens": estimated_tokens,
                "total_tokens": len(full_prompt.split()) * 1.3 + estimated_tokens
            }
            
            return LLMResponse(
                content=response_text,
                model=self.model_name,
                usage=usage,
                metadata={
                    "provider": "gemini",
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            
        except Exception as e:
            logger.error(f"Gemini 생성 오류: {e}")
            raise LLMProviderError(f"Gemini 생성 실패: {e}")
    
    def is_available(self) -> bool:
        """Provider 사용 가능 여부 확인"""
        try:
            # API 키와 클라이언트가 존재하는지만 확인
            return hasattr(self, 'client') and self.client is not None
        except Exception as e:
            logger.warning(f"Gemini 가용성 확인 실패: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 조회"""
        return {
            "provider": "gemini",
            "model_name": self.model_name,
            "available": self.is_available(),
            "max_tokens": 8192,  # Gemini 2.5 Flash의 대략적인 토큰 제한
            "supports_system_prompt": True,
            "supports_temperature": True,
            "supports_max_tokens": True
        }
    
    def _combine_prompts(self, system: Optional[str], prompt: str) -> str:
        """시스템 프롬프트와 사용자 프롬프트 결합"""
        if system:
            return f"System: {system}\n\nUser: {prompt}"
        return prompt
    
    def validate_config(self) -> bool:
        """설정 검증"""
        try:
            # API 키 확인
            if not hasattr(self, 'client') or not self.client:
                return False
            
            # 모델명 확인
            if not self.model_name:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Gemini 설정 검증 실패: {e}")
            return False


# 편의 함수
def create_gemini_provider(model_name: str = "gemini-2.5-flash", 
                          api_key: Optional[str] = None,
                          **kwargs) -> GeminiProvider:
    """Gemini Provider 생성"""
    return GeminiProvider(model_name=model_name, api_key=api_key, **kwargs)


# 테스트용 함수
def test_gemini_provider():
    """Gemini Provider 테스트"""
    try:
        # Provider 생성
        provider = create_gemini_provider()
        
        # 모델 정보 확인
        info = provider.get_model_info()
        print(f"✅ 모델 정보: {info}")
        
        # 가용성 확인
        available = provider.is_available()
        print(f"✅ 가용성: {available}")
        
        if available:
            # 간단한 생성 테스트
            response = provider.generate(
                "안녕하세요. 간단한 인사말을 해주세요.",
                max_tokens=50,
                temperature=0.7
            )
            print(f"✅ 생성 테스트: {response.content[:100]}...")
            print(f"✅ 사용량: {response.usage}")
        
        print("✅ Gemini Provider 테스트 완료")
        
    except Exception as e:
        print(f"❌ Gemini Provider 테스트 실패: {e}")


if __name__ == "__main__":
    test_gemini_provider()
