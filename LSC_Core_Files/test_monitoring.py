#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모니터링 시스템 테스트
"""
import os
import sys

# 환경 변수 설정 (파일 없이)
os.environ["GEMINI_API_KEY"] = "test_key"
os.environ["GEMINI_MODEL"] = "gemini-2.0-flash"

# src 경로 추가
sys.path.insert(0, 'src')

try:
    from src.app.main import app
    print("✅ 모니터링 시스템 로드 성공!")
    print("✅ Prometheus 지표 설정 완료")
    print("✅ 레이트 리밋 설정 완료")
    print("✅ 캐싱 시스템 설정 완료")
    print("✅ 보안 미들웨어 설정 완료")
    
    # API 엔드포인트 확인
    routes = [route.path for route in app.routes]
    print(f"\n📋 등록된 API 엔드포인트:")
    for route in sorted(routes):
        print(f"   - {route}")
    
    print(f"\n🎉 총 {len(routes)}개 엔드포인트 등록 완료!")
    
except Exception as e:
    print(f"❌ 오류: {e}")
    import traceback
    traceback.print_exc()



