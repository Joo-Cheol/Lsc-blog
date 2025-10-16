#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini API 통합 테스트 (개선 버전)
"""
import os, sys, traceback
from dotenv import load_dotenv

# .env 로드 (프로젝트 루트에서 실행 가정)
load_dotenv()
sys.path.insert(0, '.')

from src.llm.clients.gemini_client import GeminiClient
from src.llm.services.generator import generate_blog

def test_gemini():
    print("🧪 Gemini API 테스트 시작...")

    try:
        # 1) 환경 점검
        api_key = os.getenv("GEMINI_API_KEY", "")
        model = os.getenv("GEMINI_MODEL", "")
        print(f"∙ MODEL={model or '(default)'} / KEY_SET={'YES' if api_key else 'NO'}")

        # 2) 클라이언트 테스트
        print("1. Gemini 클라이언트 초기화...")
        client = GeminiClient()
        print("✅ 클라이언트 초기화 성공")

        # 3) 간단 채팅
        print("2. 간단 채팅 테스트...")
        resp = client.chat(
            system="너는 한국어 법률 전문가다.",
            messages=[{"role": "user", "content": "채권추심이 무엇인지 한 문단으로 설명해줘."}],
            temperature=0.3, max_tokens=200
        )
        print(f"✅ 응답(미리보기): {resp[:120]}...")

        # 4) 블로그 생성
        print("3. 블로그 생성 테스트...")
        result = generate_blog({
            "topic": "채권추심 지급명령 절차",
            "keywords": "지급명령, 독촉, 집행권원, 소액사건"
        })
        print("✅ 생성 완료!")
        print(f"   - Provider : {result['provider']}")
        print(f"   - Topic    : {result['topic']}")
        print(f"   - QC Pass  : {result['qc']['passed']}")
        print(f"   - Length   : {len(result['text'])}자")
        if not result['qc']['passed']:
            print(f"   - Reason   : {result['qc']['reason']}")

        print("🎉 모든 테스트 성공!")
        return True

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        # 흔한 원인 힌트
        if "GEMINI_API_KEY is missing" in str(e) or os.getenv("GEMINI_API_KEY", "") == "":
            print("→ .env에 GEMINI_API_KEY가 비어 있거나 로드되지 않았습니다.")
        if "PERMISSION_DENIED" in str(e) or "not found" in str(e):
            print("→ 모델명이 권한/리전에서 미지원일 수 있습니다. 'gemini-1.5-pro' 또는 'gemini-1.5-flash'로 바꿔보세요.")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_gemini()
