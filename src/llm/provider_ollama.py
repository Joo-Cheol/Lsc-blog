#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama LLM Provider
"""
import os
import time
import logging
import requests
from typing import Optional, Dict, Any
from .provider_base import LLMProvider, LLMResponse, LLMProviderError, LLMProviderTimeoutError

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama LLM Provider"""
    
    def __init__(self, model_name: str = "qwen2.5:7b-instruct", **kwargs):
        super().__init__(model_name, **kwargs)
        
        # Ollama 엔드포인트 설정
        self.endpoint = kwargs.get('endpoint') or os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434')
        self.timeout = kwargs.get('timeout', 120)  # 2분 타임아웃
        
        # 엔드포인트 정규화
        if not self.endpoint.startswith('http'):
            self.endpoint = f"http://{self.endpoint}"
        
        logger.info(f"Ollama Provider 초기화: {self.endpoint}/{model_name}")
    
    def generate(self, 
                 prompt: str, 
                 system: Optional[str] = None, 
                 max_tokens: int = 1024,
                 temperature: float = 0.7,
                 **kwargs) -> LLMResponse:
        """텍스트 생성"""
        try:
            # 요청 데이터 구성
            request_data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "stop": kwargs.get('stop', [])
                }
            }
            
            # 시스템 프롬프트가 있으면 추가
            if system:
                request_data["system"] = system
            
            # Ollama API 호출
            response = requests.post(
                f"{self.endpoint}/api/generate",
                json=request_data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise LLMProviderError(f"Ollama API 오류: {response.status_code} - {response.text}")
            
            response_data = response.json()
            
            # 응답 텍스트 추출
            content = response_data.get("response", "")
            if not content:
                raise LLMProviderError("Ollama에서 빈 응답을 받았습니다.")
            
            # 사용량 정보
            usage = {
                "prompt_tokens": response_data.get("prompt_eval_count", 0),
                "completion_tokens": response_data.get("eval_count", 0),
                "total_tokens": response_data.get("prompt_eval_count", 0) + response_data.get("eval_count", 0)
            }
            
            # 메타데이터
            metadata = {
                "provider": "ollama",
                "model_name": self.model_name,
                "endpoint": self.endpoint,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "eval_duration": response_data.get("eval_duration", 0),
                "load_duration": response_data.get("load_duration", 0)
            }
            
            return LLMResponse(
                content=content,
                model=self.model_name,
                usage=usage,
                metadata=metadata
            )
            
        except requests.exceptions.Timeout:
            raise LLMProviderTimeoutError(f"Ollama 요청 타임아웃: {self.timeout}초")
        except requests.exceptions.ConnectionError:
            raise LLMProviderError(f"Ollama 서버 연결 실패: {self.endpoint}")
        except Exception as e:
            logger.error(f"Ollama 생성 오류: {e}")
            raise LLMProviderError(f"Ollama 생성 실패: {e}")
    
    def is_available(self) -> bool:
        """Provider 사용 가능 여부 확인"""
        try:
            # Ollama 서버 상태 확인
            response = requests.get(f"{self.endpoint}/api/tags", timeout=10)
            if response.status_code != 200:
                return False
            
            # 모델 존재 여부 확인
            models_data = response.json()
            available_models = [model["name"] for model in models_data.get("models", [])]
            
            return self.model_name in available_models
            
        except Exception as e:
            logger.warning(f"Ollama 가용성 확인 실패: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 조회"""
        try:
            # 모델 상세 정보 조회
            response = requests.post(
                f"{self.endpoint}/api/show",
                json={"name": self.model_name},
                timeout=10
            )
            
            if response.status_code == 200:
                model_data = response.json()
                return {
                    "provider": "ollama",
                    "model_name": self.model_name,
                    "available": self.is_available(),
                    "endpoint": self.endpoint,
                    "size": model_data.get("size", 0),
                    "family": model_data.get("family", "unknown"),
                    "format": model_data.get("format", "unknown"),
                    "parameter_size": model_data.get("parameter_size", "unknown"),
                    "quantization_level": model_data.get("quantization_level", "unknown"),
                    "supports_system_prompt": True,
                    "supports_temperature": True,
                    "supports_max_tokens": True
                }
            else:
                return {
                    "provider": "ollama",
                    "model_name": self.model_name,
                    "available": False,
                    "endpoint": self.endpoint,
                    "error": f"모델 정보 조회 실패: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Ollama 모델 정보 조회 실패: {e}")
            return {
                "provider": "ollama",
                "model_name": self.model_name,
                "available": False,
                "endpoint": self.endpoint,
                "error": str(e)
            }
    
    def list_models(self) -> list:
        """사용 가능한 모델 목록 조회"""
        try:
            response = requests.get(f"{self.endpoint}/api/tags", timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                return [model["name"] for model in models_data.get("models", [])]
            else:
                return []
        except Exception as e:
            logger.error(f"Ollama 모델 목록 조회 실패: {e}")
            return []
    
    def pull_model(self, model_name: Optional[str] = None) -> bool:
        """모델 다운로드"""
        try:
            target_model = model_name or self.model_name
            response = requests.post(
                f"{self.endpoint}/api/pull",
                json={"name": target_model},
                timeout=300  # 5분 타임아웃 (모델 다운로드는 시간이 오래 걸릴 수 있음)
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama 모델 다운로드 실패: {e}")
            return False
    
    def validate_config(self) -> bool:
        """설정 검증"""
        try:
            # 엔드포인트 확인
            if not self.endpoint:
                return False
            
            # 모델명 확인
            if not self.model_name:
                return False
            
            # 서버 연결 확인
            response = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Ollama 설정 검증 실패: {e}")
            return False


# 편의 함수
def create_ollama_provider(model_name: str = "qwen2.5:7b-instruct",
                          endpoint: Optional[str] = None,
                          **kwargs) -> OllamaProvider:
    """Ollama Provider 생성"""
    return OllamaProvider(model_name=model_name, endpoint=endpoint, **kwargs)


# 테스트용 함수
def test_ollama_provider():
    """Ollama Provider 테스트"""
    try:
        # Provider 생성
        provider = create_ollama_provider()
        
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
        
        # 모델 목록 확인
        models = provider.list_models()
        print(f"✅ 사용 가능한 모델: {models}")
        
        print("✅ Ollama Provider 테스트 완료")
        
    except Exception as e:
        print(f"❌ Ollama Provider 테스트 실패: {e}")


if __name__ == "__main__":
    test_ollama_provider()
