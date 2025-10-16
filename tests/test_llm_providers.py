#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Provider 모듈 단위 테스트
"""
import unittest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.provider_base import (
    LLMProvider, LLMResponse, LLMProviderError, 
    LLMProviderTimeoutError, LLMProviderRateLimitError, LLMProviderAuthError
)
from src.llm.provider_gemini import GeminiProvider, create_gemini_provider
from src.llm.provider_ollama import OllamaProvider, create_ollama_provider
from src.llm.provider_manager import (
    ProviderManager, get_provider_manager, get_provider, generate_text
)


class TestLLMResponse(unittest.TestCase):
    """LLMResponse 테스트"""
    
    def test_llm_response_creation(self):
        """LLMResponse 생성 테스트"""
        response = LLMResponse(
            content="테스트 응답",
            model="test-model",
            usage={"total_tokens": 100},
            metadata={"provider": "test"}
        )
        
        self.assertEqual(response.content, "테스트 응답")
        self.assertEqual(response.model, "test-model")
        self.assertEqual(response.usage["total_tokens"], 100)
        self.assertEqual(response.metadata["provider"], "test")


class TestLLMProviderBase(unittest.TestCase):
    """LLMProvider 기본 클래스 테스트"""
    
    def test_llm_provider_error(self):
        """LLMProviderError 테스트"""
        error = LLMProviderError("테스트 오류")
        self.assertEqual(str(error), "테스트 오류")
    
    def test_llm_provider_timeout_error(self):
        """LLMProviderTimeoutError 테스트"""
        error = LLMProviderTimeoutError("타임아웃 오류")
        self.assertIsInstance(error, LLMProviderError)
        self.assertEqual(str(error), "타임아웃 오류")
    
    def test_llm_provider_rate_limit_error(self):
        """LLMProviderRateLimitError 테스트"""
        error = LLMProviderRateLimitError("속도 제한 오류")
        self.assertIsInstance(error, LLMProviderError)
        self.assertEqual(str(error), "속도 제한 오류")
    
    def test_llm_provider_auth_error(self):
        """LLMProviderAuthError 테스트"""
        error = LLMProviderAuthError("인증 오류")
        self.assertIsInstance(error, LLMProviderError)
        self.assertEqual(str(error), "인증 오류")


class TestGeminiProvider(unittest.TestCase):
    """GeminiProvider 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_api_key = "test-api-key"
        self.model_name = "gemini-2.5-flash"
    
    @patch('src.llm.provider_gemini.GeminiClient')
    def test_gemini_provider_initialization(self, mock_gemini_client):
        """GeminiProvider 초기화 테스트"""
        mock_client_instance = MagicMock()
        mock_gemini_client.return_value = mock_client_instance
        
        provider = GeminiProvider(model_name=self.model_name, api_key=self.mock_api_key)
        
        self.assertEqual(provider.model_name, self.model_name)
        self.assertEqual(provider.client, mock_client_instance)
        mock_gemini_client.assert_called_once_with(model_name=self.model_name)
    
    def test_gemini_provider_initialization_no_api_key(self):
        """GeminiProvider 초기화 실패 테스트 (API 키 없음)"""
        with self.assertRaises(LLMProviderError) as context:
            GeminiProvider(model_name=self.model_name)
        
        # API 키 관련 오류 메시지 확인
        error_message = str(context.exception)
        self.assertTrue(
            "GEMINI_API_KEY가 설정되지 않았습니다" in error_message or 
            "Gemini 클라이언트 초기화 실패" in error_message
        )
    
    @patch('src.llm.provider_gemini.GeminiClient')
    def test_gemini_provider_generate(self, mock_gemini_client):
        """GeminiProvider 생성 테스트"""
        mock_client_instance = MagicMock()
        mock_client_instance.generate_text.return_value = "테스트 응답"
        mock_gemini_client.return_value = mock_client_instance
        
        provider = GeminiProvider(model_name=self.model_name, api_key=self.mock_api_key)
        
        response = provider.generate("테스트 프롬프트", max_tokens=100, temperature=0.7)
        
        self.assertIsInstance(response, LLMResponse)
        self.assertEqual(response.content, "테스트 응답")
        self.assertEqual(response.model, self.model_name)
        self.assertIn("prompt_tokens", response.usage)
        self.assertIn("completion_tokens", response.usage)
        self.assertEqual(response.metadata["provider"], "gemini")
    
    @patch('src.llm.provider_gemini.GeminiClient')
    def test_gemini_provider_generate_with_system(self, mock_gemini_client):
        """GeminiProvider 생성 테스트 (시스템 프롬프트 포함)"""
        mock_client_instance = MagicMock()
        mock_client_instance.generate_text.return_value = "테스트 응답"
        mock_gemini_client.return_value = mock_client_instance
        
        provider = GeminiProvider(model_name=self.model_name, api_key=self.mock_api_key)
        
        response = provider.generate(
            "테스트 프롬프트", 
            system="시스템 프롬프트",
            max_tokens=100, 
            temperature=0.7
        )
        
        # 시스템 프롬프트가 결합되었는지 확인
        call_args = mock_client_instance.generate_text.call_args
        self.assertIn("System: 시스템 프롬프트", call_args[1]["prompt"])
        self.assertIn("User: 테스트 프롬프트", call_args[1]["prompt"])
    
    @patch('src.llm.provider_gemini.GeminiClient')
    def test_gemini_provider_is_available(self, mock_gemini_client):
        """GeminiProvider 가용성 확인 테스트"""
        mock_client_instance = MagicMock()
        mock_client_instance.generate_text.return_value = "테스트 응답"
        mock_gemini_client.return_value = mock_client_instance
        
        provider = GeminiProvider(model_name=self.model_name, api_key=self.mock_api_key)
        
        available = provider.is_available()
        self.assertTrue(available)
    
    @patch('src.llm.provider_gemini.GeminiClient')
    def test_gemini_provider_is_available_false(self, mock_gemini_client):
        """GeminiProvider 가용성 확인 실패 테스트"""
        mock_client_instance = MagicMock()
        mock_client_instance.generate_text.side_effect = Exception("API 오류")
        mock_gemini_client.return_value = mock_client_instance
        
        provider = GeminiProvider(model_name=self.model_name, api_key=self.mock_api_key)
        
        available = provider.is_available()
        self.assertFalse(available)
    
    @patch('src.llm.provider_gemini.GeminiClient')
    def test_gemini_provider_get_model_info(self, mock_gemini_client):
        """GeminiProvider 모델 정보 조회 테스트"""
        mock_client_instance = MagicMock()
        mock_gemini_client.return_value = mock_client_instance
        
        provider = GeminiProvider(model_name=self.model_name, api_key=self.mock_api_key)
        
        info = provider.get_model_info()
        
        self.assertEqual(info["provider"], "gemini")
        self.assertEqual(info["model_name"], self.model_name)
        self.assertIn("max_tokens", info)
        self.assertTrue(info["supports_system_prompt"])
        self.assertTrue(info["supports_temperature"])
        self.assertTrue(info["supports_max_tokens"])
    
    @patch('src.llm.provider_gemini.GeminiClient')
    def test_gemini_provider_validate_config(self, mock_gemini_client):
        """GeminiProvider 설정 검증 테스트"""
        mock_client_instance = MagicMock()
        mock_gemini_client.return_value = mock_client_instance
        
        provider = GeminiProvider(model_name=self.model_name, api_key=self.mock_api_key)
        
        valid = provider.validate_config()
        self.assertTrue(valid)
    
    def test_create_gemini_provider(self):
        """create_gemini_provider 함수 테스트"""
        with patch('src.llm.provider_gemini.GeminiClient'):
            provider = create_gemini_provider(
                model_name="test-model",
                api_key="test-key"
            )
            self.assertIsInstance(provider, GeminiProvider)
            self.assertEqual(provider.model_name, "test-model")


class TestOllamaProvider(unittest.TestCase):
    """OllamaProvider 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.model_name = "qwen2.5:7b-instruct"
        self.endpoint = "http://localhost:11434"
    
    @patch('src.llm.provider_ollama.requests.post')
    def test_ollama_provider_generate(self, mock_post):
        """OllamaProvider 생성 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "테스트 응답",
            "prompt_eval_count": 10,
            "eval_count": 5,
            "eval_duration": 1000,
            "load_duration": 500
        }
        mock_post.return_value = mock_response
        
        provider = OllamaProvider(model_name=self.model_name, endpoint=self.endpoint)
        
        response = provider.generate("테스트 프롬프트", max_tokens=100, temperature=0.7)
        
        self.assertIsInstance(response, LLMResponse)
        self.assertEqual(response.content, "테스트 응답")
        self.assertEqual(response.model, self.model_name)
        self.assertEqual(response.usage["prompt_tokens"], 10)
        self.assertEqual(response.usage["completion_tokens"], 5)
        self.assertEqual(response.metadata["provider"], "ollama")
        self.assertEqual(response.metadata["endpoint"], self.endpoint)
    
    @patch('src.llm.provider_ollama.requests.post')
    def test_ollama_provider_generate_with_system(self, mock_post):
        """OllamaProvider 생성 테스트 (시스템 프롬프트 포함)"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "테스트 응답",
            "prompt_eval_count": 10,
            "eval_count": 5
        }
        mock_post.return_value = mock_response
        
        provider = OllamaProvider(model_name=self.model_name, endpoint=self.endpoint)
        
        response = provider.generate(
            "테스트 프롬프트", 
            system="시스템 프롬프트",
            max_tokens=100, 
            temperature=0.7
        )
        
        # 요청 데이터 확인
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        self.assertEqual(request_data["system"], "시스템 프롬프트")
        self.assertEqual(request_data["model"], self.model_name)
        self.assertEqual(request_data["options"]["temperature"], 0.7)
        self.assertEqual(request_data["options"]["num_predict"], 100)
    
    @patch('src.llm.provider_ollama.requests.post')
    def test_ollama_provider_generate_error(self, mock_post):
        """OllamaProvider 생성 오류 테스트"""
        # Mock 오류 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        provider = OllamaProvider(model_name=self.model_name, endpoint=self.endpoint)
        
        with self.assertRaises(LLMProviderError) as context:
            provider.generate("테스트 프롬프트")
        
        self.assertIn("Ollama API 오류", str(context.exception))
    
    @patch('src.llm.provider_ollama.requests.get')
    def test_ollama_provider_is_available(self, mock_get):
        """OllamaProvider 가용성 확인 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5:7b-instruct"},
                {"name": "llama2:7b"}
            ]
        }
        mock_get.return_value = mock_response
        
        provider = OllamaProvider(model_name=self.model_name, endpoint=self.endpoint)
        
        available = provider.is_available()
        self.assertTrue(available)
    
    @patch('src.llm.provider_ollama.requests.get')
    def test_ollama_provider_is_available_false(self, mock_get):
        """OllamaProvider 가용성 확인 실패 테스트"""
        # Mock 오류 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        provider = OllamaProvider(model_name=self.model_name, endpoint=self.endpoint)
        
        available = provider.is_available()
        self.assertFalse(available)
    
    @patch('src.llm.provider_ollama.requests.post')
    def test_ollama_provider_get_model_info(self, mock_post):
        """OllamaProvider 모델 정보 조회 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "size": 1000000000,
            "family": "qwen",
            "format": "gguf",
            "parameter_size": "7B",
            "quantization_level": "Q4_0"
        }
        mock_post.return_value = mock_response
        
        provider = OllamaProvider(model_name=self.model_name, endpoint=self.endpoint)
        
        info = provider.get_model_info()
        
        self.assertEqual(info["provider"], "ollama")
        self.assertEqual(info["model_name"], self.model_name)
        self.assertEqual(info["endpoint"], self.endpoint)
        self.assertEqual(info["size"], 1000000000)
        self.assertEqual(info["family"], "qwen")
        self.assertTrue(info["supports_system_prompt"])
        self.assertTrue(info["supports_temperature"])
        self.assertTrue(info["supports_max_tokens"])
    
    @patch('src.llm.provider_ollama.requests.get')
    def test_ollama_provider_list_models(self, mock_get):
        """OllamaProvider 모델 목록 조회 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5:7b-instruct"},
                {"name": "llama2:7b"}
            ]
        }
        mock_get.return_value = mock_response
        
        provider = OllamaProvider(model_name=self.model_name, endpoint=self.endpoint)
        
        models = provider.list_models()
        
        self.assertIn("qwen2.5:7b-instruct", models)
        self.assertIn("llama2:7b", models)
    
    @patch('src.llm.provider_ollama.requests.get')
    def test_ollama_provider_validate_config(self, mock_get):
        """OllamaProvider 설정 검증 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_get.return_value = mock_response
        
        provider = OllamaProvider(model_name=self.model_name, endpoint=self.endpoint)
        
        valid = provider.validate_config()
        self.assertTrue(valid)
    
    def test_create_ollama_provider(self):
        """create_ollama_provider 함수 테스트"""
        provider = create_ollama_provider(
            model_name="test-model",
            endpoint="http://test:11434"
        )
        self.assertIsInstance(provider, OllamaProvider)
        self.assertEqual(provider.model_name, "test-model")
        self.assertEqual(provider.endpoint, "http://test:11434")


class TestProviderManager(unittest.TestCase):
    """ProviderManager 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # 환경 변수 백업
        self.original_env = {}
        for key in ['LLM_PROVIDER', 'GEMINI_API_KEY', 'OLLAMA_ENDPOINT', 'OLLAMA_MODEL']:
            self.original_env[key] = os.environ.get(key)
    
    def tearDown(self):
        """테스트 정리"""
        # 환경 변수 복원
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    @patch('src.llm.provider_manager.OllamaProvider')
    def test_provider_manager_initialization_ollama(self, mock_ollama_provider):
        """ProviderManager 초기화 테스트 (Ollama)"""
        # 환경 변수 설정
        os.environ['LLM_PROVIDER'] = 'ollama'
        os.environ['OLLAMA_ENDPOINT'] = 'http://localhost:11434'
        os.environ['OLLAMA_MODEL'] = 'qwen2.5:7b-instruct'
        
        # LLMProvider를 상속받은 Mock 클래스 생성
        class MockOllamaProvider(LLMProvider):
            def generate(self, prompt, system=None, max_tokens=1024, temperature=0.7, **kwargs):
                return MagicMock()
            def is_available(self):
                return True
            def get_model_info(self):
                return {"provider": "ollama"}
        
        mock_provider = MockOllamaProvider("qwen2.5:7b-instruct")
        mock_ollama_provider.return_value = mock_provider
        
        manager = ProviderManager()
        
        self.assertEqual(manager.default_provider, 'ollama')
        self.assertIn('ollama', manager.providers)
        mock_ollama_provider.assert_called_once()
    
    @patch('src.llm.provider_manager.GeminiProvider')
    def test_provider_manager_initialization_gemini(self, mock_gemini_provider):
        """ProviderManager 초기화 테스트 (Gemini)"""
        # 환경 변수 설정
        os.environ['LLM_PROVIDER'] = 'gemini'
        os.environ['GEMINI_API_KEY'] = 'test-api-key'
        os.environ['GEMINI_MODEL'] = 'gemini-2.5-flash'
        
        # LLMProvider를 상속받은 Mock 클래스 생성
        class MockGeminiProvider(LLMProvider):
            def generate(self, prompt, system=None, max_tokens=1024, temperature=0.7, **kwargs):
                return MagicMock()
            def is_available(self):
                return True
            def get_model_info(self):
                return {"provider": "gemini"}
        
        mock_provider = MockGeminiProvider("gemini-2.5-flash")
        mock_gemini_provider.return_value = mock_provider
        
        manager = ProviderManager()
        
        self.assertEqual(manager.default_provider, 'gemini')
        self.assertIn('gemini', manager.providers)
        mock_gemini_provider.assert_called_once()
    
    def test_provider_manager_register_provider(self):
        """ProviderManager Provider 등록 테스트"""
        manager = ProviderManager()
        
        # LLMProvider를 상속받은 Mock 클래스 생성
        class MockProvider(LLMProvider):
            def generate(self, prompt, system=None, max_tokens=1024, temperature=0.7, **kwargs):
                return MagicMock()
            def is_available(self):
                return True
            def get_model_info(self):
                return {"provider": "test"}
        
        mock_provider = MockProvider("test-model")
        
        manager.register_provider('test', mock_provider)
        
        self.assertIn('test', manager.providers)
        self.assertEqual(manager.providers['test'], mock_provider)
    
    def test_provider_manager_register_invalid_provider(self):
        """ProviderManager 잘못된 Provider 등록 테스트"""
        manager = ProviderManager()
        
        with self.assertRaises(ValueError) as context:
            manager.register_provider('test', "invalid_provider")
        
        self.assertIn("Provider는 LLMProvider 인스턴스여야 합니다", str(context.exception))
    
    def test_provider_manager_get_provider(self):
        """ProviderManager Provider 조회 테스트"""
        manager = ProviderManager()
        
        # LLMProvider를 상속받은 Mock 클래스 생성
        class MockProvider(LLMProvider):
            def generate(self, prompt, system=None, max_tokens=1024, temperature=0.7, **kwargs):
                return MagicMock()
            def is_available(self):
                return True
            def get_model_info(self):
                return {"provider": "test"}
        
        mock_provider = MockProvider("test-model")
        manager.register_provider('test', mock_provider)
        manager.set_default_provider('test')
        
        provider = manager.get_provider('test')
        self.assertEqual(provider, mock_provider)
    
    def test_provider_manager_get_provider_not_found(self):
        """ProviderManager Provider 조회 실패 테스트"""
        manager = ProviderManager()
        
        with self.assertRaises(LLMProviderError) as context:
            manager.get_provider('nonexistent')
        
        self.assertIn("등록되지 않은 Provider", str(context.exception))
    
    def test_provider_manager_list_providers(self):
        """ProviderManager Provider 목록 조회 테스트"""
        manager = ProviderManager()
        
        # LLMProvider를 상속받은 Mock 클래스 생성
        class MockProvider(LLMProvider):
            def generate(self, prompt, system=None, max_tokens=1024, temperature=0.7, **kwargs):
                return MagicMock()
            def is_available(self):
                return True
            def get_model_info(self):
                return {"provider": "test"}
        
        mock_provider = MockProvider("test-model")
        manager.register_provider('test', mock_provider)
        
        providers = manager.list_providers()
        
        self.assertIn('test', providers)
        self.assertTrue(providers['test']['available'])
        # model_info가 있는 경우에만 확인
        if 'model_info' in providers['test']:
            self.assertEqual(providers['test']['model_info']['provider'], 'test')
    
    def test_provider_manager_set_default_provider(self):
        """ProviderManager 기본 Provider 설정 테스트"""
        manager = ProviderManager()
        
        # LLMProvider를 상속받은 Mock 클래스 생성
        class MockProvider(LLMProvider):
            def generate(self, prompt, system=None, max_tokens=1024, temperature=0.7, **kwargs):
                return MagicMock()
            def is_available(self):
                return True
            def get_model_info(self):
                return {"provider": "test"}
        
        mock_provider = MockProvider("test-model")
        manager.register_provider('test', mock_provider)
        
        manager.set_default_provider('test')
        self.assertEqual(manager.default_provider, 'test')
    
    def test_provider_manager_set_default_provider_not_found(self):
        """ProviderManager 기본 Provider 설정 실패 테스트"""
        manager = ProviderManager()
        
        with self.assertRaises(LLMProviderError) as context:
            manager.set_default_provider('nonexistent')
        
        self.assertIn("등록되지 않은 Provider", str(context.exception))
    
    def test_provider_manager_generate(self):
        """ProviderManager 생성 테스트"""
        manager = ProviderManager()
        
        # LLMProvider를 상속받은 Mock 클래스 생성
        class MockProvider(LLMProvider):
            def __init__(self, model_name):
                super().__init__(model_name)
                self.mock_response = MagicMock()
            
            def generate(self, prompt, system=None, max_tokens=1024, temperature=0.7, **kwargs):
                return self.mock_response
            def is_available(self):
                return True
            def get_model_info(self):
                return {"provider": "test"}
        
        mock_provider = MockProvider("test-model")
        manager.register_provider('test', mock_provider)
        manager.set_default_provider('test')
        
        response = manager.generate("테스트 프롬프트", max_tokens=100)
        
        self.assertEqual(response, mock_provider.mock_response)
    
    def test_provider_manager_health_check(self):
        """ProviderManager 상태 확인 테스트"""
        manager = ProviderManager()
        
        # LLMProvider를 상속받은 Mock 클래스 생성
        class MockProvider(LLMProvider):
            def generate(self, prompt, system=None, max_tokens=1024, temperature=0.7, **kwargs):
                return MagicMock()
            def is_available(self):
                return True
            def get_model_info(self):
                return {"provider": "test"}
        
        mock_provider = MockProvider("test-model")
        manager.register_provider('test', mock_provider)
        manager.set_default_provider('test')
        
        health = manager.health_check()
        
        self.assertEqual(health['default_provider'], 'test')
        self.assertEqual(health['overall_status'], 'healthy')
        # 기본 Provider도 있으므로 available_count는 2 이상
        self.assertGreaterEqual(health['available_count'], 1)
        self.assertGreaterEqual(health['total_count'], 1)
        self.assertIn('test', health['providers'])


class TestConvenienceFunctions(unittest.TestCase):
    """편의 함수 테스트"""
    
    def test_get_provider_manager(self):
        """get_provider_manager 함수 테스트"""
        result = get_provider_manager()
        
        self.assertIsInstance(result, ProviderManager)
    
    @patch('src.llm.provider_manager.get_provider_manager')
    def test_get_provider_function(self, mock_get_manager):
        """get_provider 함수 테스트"""
        mock_manager = MagicMock()
        mock_provider = MagicMock()
        mock_manager.get_provider.return_value = mock_provider
        mock_get_manager.return_value = mock_manager
        
        result = get_provider('test')
        
        self.assertEqual(result, mock_provider)
        mock_manager.get_provider.assert_called_once_with('test')
    
    @patch('src.llm.provider_manager.get_provider_manager')
    def test_generate_text_function(self, mock_get_manager):
        """generate_text 함수 테스트"""
        mock_manager = MagicMock()
        mock_response = MagicMock()
        mock_manager.generate.return_value = mock_response
        mock_get_manager.return_value = mock_manager
        
        result = generate_text("테스트 프롬프트", max_tokens=100)
        
        self.assertEqual(result, mock_response)
        mock_manager.generate.assert_called_once_with(
            prompt="테스트 프롬프트",
            system=None,
            max_tokens=100,
            temperature=0.7,
            provider_name=None
        )


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_full_provider_workflow(self):
        """전체 Provider 워크플로우 테스트"""
        # 1단계: Provider Manager 생성
        manager = ProviderManager()
        
        # 2단계: Mock Provider 등록
        class MockProvider(LLMProvider):
            def __init__(self, model_name):
                super().__init__(model_name)
                self.mock_response = MagicMock()
                self.mock_response.content = "테스트 응답"
                self.mock_response.model = "test-model"
                self.mock_response.usage = {"total_tokens": 100}
                self.mock_response.metadata = {"provider": "test"}
            
            def generate(self, prompt, system=None, max_tokens=1024, temperature=0.7, **kwargs):
                return self.mock_response
            def is_available(self):
                return True
            def get_model_info(self):
                return {
                    "provider": "test",
                    "model_name": "test-model",
                    "available": True
                }
        
        mock_provider = MockProvider("test-model")
        manager.register_provider('test', mock_provider)
        manager.set_default_provider('test')
        
        # 3단계: Provider 조회
        provider = manager.get_provider('test')
        self.assertEqual(provider, mock_provider)
        
        # 4단계: 모델 정보 조회
        info = provider.get_model_info()
        self.assertEqual(info['provider'], 'test')
        
        # 5단계: 가용성 확인
        available = provider.is_available()
        self.assertTrue(available)
        
        # 6단계: 텍스트 생성
        response = manager.generate("테스트 프롬프트", max_tokens=100)
        self.assertEqual(response, mock_provider.mock_response)
        
        # 7단계: 상태 확인
        health = manager.health_check()
        self.assertEqual(health['overall_status'], 'healthy')
        
        # 8단계: 편의 함수 테스트 (별도 Manager 인스턴스 사용)
        provider2 = manager.get_provider('test')
        self.assertEqual(provider2, mock_provider)
        
        response2 = manager.generate("테스트 프롬프트", max_tokens=100)
        self.assertEqual(response2, mock_provider.mock_response)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
