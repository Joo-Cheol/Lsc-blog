#!/usr/bin/env python3
"""
네이버 블로그 생성기 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_naver_generator():
    """네이버 블로그 생성기 테스트"""
    try:
        from src.generator.generator_no_llm import generate_no_llm
        
        # 테스트 데이터
        topic = "채권추심 방법"
        results = [
            {
                "title": "채권추심 절차 가이드",
                "content": "채권추심은 다음과 같은 절차로 진행됩니다. 먼저 독촉장을 발송하고, 지급명령을 신청합니다.",
                "similarity": 0.95
            },
            {
                "title": "지급명령 신청 방법",
                "content": "지급명령은 민사소송법에 따라 신청할 수 있습니다. 소액사건심판법이 적용됩니다.",
                "similarity": 0.88
            }
        ]
        
        print("🚀 네이버 블로그 생성기 테스트 시작...")
        print(f"주제: {topic}")
        print(f"검색 결과: {len(results)}개")
        
        # 생성기 테스트
        result = generate_no_llm(topic, results, None, "채권추심", 10)
        
        print("\n✅ 생성 결과:")
        print(f"제목: {result.get('title', 'N/A')}")
        print(f"HTML 길이: {len(result.get('html', ''))}")
        print(f"생성 시간: {result.get('stats', {}).get('generation_time', 0):.2f}초")
        print(f"모드: {result.get('stats', {}).get('mode', 'N/A')}")
        
        if result.get('html'):
            print("\n📝 생성된 HTML 미리보기:")
            html_preview = result['html'][:500] + "..." if len(result['html']) > 500 else result['html']
            print(html_preview)
        
        print("\n🎉 테스트 완료!")
        return True
        
    except ImportError as e:
        print(f"❌ 모듈 임포트 오류: {e}")
        print("필요한 의존성을 설치해주세요:")
        print("pip install scikit-learn")
        return False
        
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        return False

if __name__ == "__main__":
    success = test_naver_generator()
    sys.exit(0 if success else 1)

