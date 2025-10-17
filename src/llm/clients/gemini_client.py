from typing import List, Dict
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError
import time
import random
from src.config.settings import settings

class GeminiClient:
    def __init__(self, model_name: str = None):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is missing (.env에 설정 필요)")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model_name = model_name or settings.GEMINI_MODEL or "gemini-1.5-pro"

    def chat(self, system: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        messages: [{"role":"user","content":"..."}, {"role":"model","content":"..."} ...]
        """
        # system instruction을 첫 번째 메시지에 포함
        user_concat = f"[시스템 지시사항]\n{system}\n\n"
        user_concat += "\n\n".join([m["content"] for m in messages if m["role"] == "user"])
        
        model = genai.GenerativeModel(
            model_name=self._model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=kwargs.get("temperature", 0.3),
                max_output_tokens=kwargs.get("max_tokens", 2200),
            )
        )
        
        # 재시도 로직 (최대 2회, 지수 백오프)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                resp = model.generate_content(
                    user_concat,
                    safety_settings=[
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    ],
                )
                # 응답 텍스트 추출 (안전한 방식)
                try:
                    # 먼저 candidates를 통해 접근
                    if resp.candidates and len(resp.candidates) > 0:
                        candidate = resp.candidates[0]
                        if candidate.content and candidate.content.parts:
                            text_parts = []
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    text_parts.append(part.text)
                            if text_parts:
                                return ''.join(text_parts).strip()
                    
                    # 대안: parts 직접 접근
                    if hasattr(resp, 'parts') and resp.parts:
                        text_parts = []
                        for part in resp.parts:
                            if hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)
                        if text_parts:
                            return ''.join(text_parts).strip()
                    
                    return ""
                except Exception as e:
                    print(f"응답 파싱 오류: {e}")
                    return ""
                
            except GoogleAPIError as e:
                if attempt < max_retries:
                    # 지수 백오프: 1초, 2초, 4초...
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f"   ⚠️  API 오류, {delay:.1f}초 후 재시도... ({attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    raise RuntimeError(f"Gemini API error: {e.message}") from e
            except Exception as e:
                if attempt < max_retries:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f"   ⚠️  호출 오류, {delay:.1f}초 후 재시도... ({attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    raise RuntimeError(f"Gemini call failed: {e}") from e

    def generate_text(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7, **kwargs) -> str:
        """단일 프롬프트로 텍스트 생성"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat("", messages, max_tokens=max_tokens, temperature=temperature, **kwargs)