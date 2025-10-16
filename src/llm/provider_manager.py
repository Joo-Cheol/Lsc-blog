#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Provider 관리자
"""
import os
import logging
from typing import Dict, Any, Optional, Type
from .provider_base import LLMProvider, LLMProviderError
from .provider_gemini import GeminiProvider
from .provider_ollama import OllamaProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """LLM Provider 관리자"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider: Optional[str] = None
        self._register_default_providers()
    
    def _register_default_providers(self):
        """기본 Provider 등록"""
        # 환경 변수에서 기본 Provider 확인
        default_provider = os.getenv('LLM_PROVIDER', 'ollama').lower()
        
        try:
            if default_provider == 'gemini':
                self.register_provider('gemini', self._create_gemini_provider())
                self.default_provider = 'gemini'
            elif default_provider == 'ollama':
                self.register_provider('ollama', self._create_ollama_provider())
                self.default_provider = 'ollama'
            else:
                # 기본값으로 ollama 사용
                self.register_provider('ollama', self._create_ollama_provider())
                self.default_provider = 'ollama'
                
            logger.info(f"기본 Provider 설정: {self.default_provider}")
            
        except Exception as e:
            logger.error(f"기본 Provider 설정 실패: {e}")
            # 폴백으로 ollama 시도
            try:
                self.register_provider('ollama', self._create_ollama_provider())
                self.default_provider = 'ollama'
                logger.info("폴백 Provider 설정: ollama")
            except Exception as fallback_error:
                logger.error(f"폴백 Provider 설정도 실패: {fallback_error}")
    
    def _create_gemini_provider(self) -> GeminiProvider:
        """Gemini Provider 생성"""
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise LLMProviderError("GEMINI_API_KEY가 설정되지 않았습니다.")
        
        return GeminiProvider(model_name=model_name, api_key=api_key)
    
    def _create_ollama_provider(self) -> OllamaProvider:
        """Ollama Provider 생성"""
        model_name = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b-instruct')
        endpoint = os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434')
        
        return OllamaProvider(model_name=model_name, endpoint=endpoint)
    
    def register_provider(self, name: str, provider: LLMProvider):
        """Provider 등록"""
        if not isinstance(provider, LLMProvider):
            raise ValueError(f"Provider는 LLMProvider 인스턴스여야 합니다: {type(provider)}")
        
        self.providers[name] = provider
        logger.info(f"Provider 등록: {name} -> {provider}")
    
    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        """Provider 조회"""
        if name is None:
            name = self.default_provider
        
        if not name:
            raise LLMProviderError("기본 Provider가 설정되지 않았습니다.")
        
        if name not in self.providers:
            raise LLMProviderError(f"등록되지 않은 Provider: {name}")
        
        provider = self.providers[name]
        
        # Provider 가용성 확인
        if not provider.is_available():
            logger.warning(f"Provider {name}이 사용 불가능합니다.")
            # 다른 사용 가능한 Provider 찾기
            available_provider = self._find_available_provider()
            if available_provider:
                logger.info(f"대체 Provider 사용: {available_provider}")
                return self.providers[available_provider]
            else:
                raise LLMProviderError(f"사용 가능한 Provider가 없습니다.")
        
        return provider
    
    def _find_available_provider(self) -> Optional[str]:
        """사용 가능한 Provider 찾기"""
        for name, provider in self.providers.items():
            try:
                if provider.is_available():
                    return name
            except Exception as e:
                logger.warning(f"Provider {name} 가용성 확인 실패: {e}")
        return None
    
    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """등록된 Provider 목록 조회"""
        result = {}
        for name, provider in self.providers.items():
            try:
                info = provider.get_model_info()
                info['registered'] = True
                info['available'] = provider.is_available()
                result[name] = info
            except Exception as e:
                result[name] = {
                    'registered': True,
                    'available': False,
                    'error': str(e)
                }
        return result
    
    def get_default_provider_name(self) -> Optional[str]:
        """기본 Provider 이름 조회"""
        return self.default_provider
    
    def set_default_provider(self, name: str):
        """기본 Provider 설정"""
        if name not in self.providers:
            raise LLMProviderError(f"등록되지 않은 Provider: {name}")
        
        self.default_provider = name
        logger.info(f"기본 Provider 변경: {name}")
    
    def generate(self, 
                 prompt: str, 
                 system: Optional[str] = None, 
                 max_tokens: int = 1024,
                 temperature: float = 0.7,
                 provider_name: Optional[str] = None,
                 **kwargs):
        """텍스트 생성 (기본 Provider 사용)"""
        provider = self.get_provider(provider_name)
        return provider.generate(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
    
    def health_check(self) -> Dict[str, Any]:
        """전체 Provider 상태 확인"""
        result = {
            "default_provider": self.default_provider,
            "providers": {},
            "overall_status": "healthy"
        }
        
        available_count = 0
        total_count = len(self.providers)
        
        for name, provider in self.providers.items():
            try:
                is_available = provider.is_available()
                if is_available:
                    available_count += 1
                
                result["providers"][name] = {
                    "available": is_available,
                    "model_info": provider.get_model_info() if is_available else None
                }
            except Exception as e:
                result["providers"][name] = {
                    "available": False,
                    "error": str(e)
                }
        
        # 전체 상태 결정
        if available_count == 0:
            result["overall_status"] = "unhealthy"
        elif available_count < total_count:
            result["overall_status"] = "degraded"
        
        result["available_count"] = available_count
        result["total_count"] = total_count
        
        return result


# 전역 Provider Manager 인스턴스
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """전역 Provider Manager 인스턴스 조회"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def get_provider(name: Optional[str] = None) -> LLMProvider:
    """Provider 조회 (편의 함수)"""
    return get_provider_manager().get_provider(name)


def generate_text(prompt: str, 
                  system: Optional[str] = None, 
                  max_tokens: int = 1024,
                  temperature: float = 0.7,
                  provider_name: Optional[str] = None,
                  **kwargs):
    """텍스트 생성 (편의 함수)"""
    return get_provider_manager().generate(
        prompt=prompt,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
        provider_name=provider_name,
        **kwargs
    )


# 테스트용 함수
def test_provider_manager():
    """Provider Manager 테스트"""
    try:
        # Manager 생성
        manager = ProviderManager()
        
        # Provider 목록 확인
        providers = manager.list_providers()
        print(f"✅ 등록된 Provider: {list(providers.keys())}")
        
        # 기본 Provider 확인
        default_name = manager.get_default_provider_name()
        print(f"✅ 기본 Provider: {default_name}")
        
        # Provider 조회
        provider = manager.get_provider()
        print(f"✅ 현재 Provider: {provider}")
        
        # 모델 정보 확인
        info = provider.get_model_info()
        print(f"✅ 모델 정보: {info}")
        
        # 가용성 확인
        available = provider.is_available()
        print(f"✅ 가용성: {available}")
        
        if available:
            # 간단한 생성 테스트
            response = manager.generate(
                "안녕하세요. 간단한 인사말을 해주세요.",
                max_tokens=50,
                temperature=0.7
            )
            print(f"✅ 생성 테스트: {response.content[:100]}...")
        
        # 상태 확인
        health = manager.health_check()
        print(f"✅ 전체 상태: {health['overall_status']}")
        
        print("✅ Provider Manager 테스트 완료")
        
    except Exception as e:
        print(f"❌ Provider Manager 테스트 실패: {e}")


if __name__ == "__main__":
    test_provider_manager()
