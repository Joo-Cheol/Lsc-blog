#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
운영 체크 - 5건 연속 생성 테스트
"""
import sys
import re
sys.path.insert(0, '.')

from src.llm.services.generator import generate_blog

def main():
    print("🚀 운영 체크: 5건 연속 생성 테스트 시작...")
    
    test_cases = [
        {"topic": "채권추심 지급명령 절차", "keywords": "지급명령, 독촉, 집행권원"},
        {"topic": "독촉장 발송과 법적 효과", "keywords": "독촉장, 내용증명, 채권보전"},
        {"topic": "집행권원의 요건과 효력", "keywords": "집행권원, 강제집행, 판결서"},
        {"topic": "소액사건심판법의 주요 내용", "keywords": "소액사건, 간이절차, 신속처리"},
        {"topic": "채권추심의 전체 절차", "keywords": "채권추심, 법적절차, 전문가도움"}
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 테스트 {i}/5: {test_case['topic']}")
        
        try:
            result = generate_blog(test_case)
            results.append(result)
            
            print(f"✅ 생성 완료!")
            print(f"   - Success: {result.get('success')}")
            print(f"   - QC Passed: {result.get('qc', {}).get('passed')}")
            print(f"   - Length: {len(result.get('text', ''))}자")
            print(f"   - Formal OK: {result.get('qc', {}).get('formal_ok')}")
            print(f"   - Plag Score: {result.get('plag_score', 0)}")
            print(f"   - H2 Count: {result['text'].count('## ')}")
            print(f"   - Checklist Count: {len(re.findall(r'^\s*(?:[-*]|\d+\.)\s+', result['text'], re.M))}")
            print(f"   - Forbidden OK: {result.get('qc',{}).get('forbidden_ok')}")
            
            if not result.get('success'):
                print(f"   - 실패 사유: {result.get('qc', {}).get('reason')}")
                
        except Exception as e:
            print(f"❌ 생성 실패: {e}")
            results.append(None)
    
    # 통계 분석
    print(f"\n📊 운영 체크 결과 분석:")
    print(f"=" * 50)
    
    successful_results = [r for r in results if r is not None]
    success_count = len([r for r in successful_results if r.get('success')])
    qc_passed_count = len([r for r in successful_results if r.get('qc', {}).get('passed')])
    formal_ok_count = len([r for r in successful_results if r.get('qc', {}).get('formal_ok')])
    
    print(f"📈 전체 성공률: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")
    print(f"📈 QC 통과율: {qc_passed_count}/{len(successful_results)} ({qc_passed_count/len(successful_results)*100:.1f}%)")
    print(f"📈 격식형 통과율: {formal_ok_count}/{len(successful_results)} ({formal_ok_count/len(successful_results)*100:.1f}%)")
    
    # 길이 통계
    lengths = [len(r.get('text', '')) for r in successful_results if r]
    if lengths:
        avg_length = sum(lengths) / len(lengths)
        min_length = min(lengths)
        max_length = max(lengths)
        print(f"📏 평균 길이: {avg_length:.0f}자 (범위: {min_length}-{max_length}자)")
        
        # 목표 범위(1650-1850자) 내 비율
        target_range_count = len([l for l in lengths if 1650 <= l <= 1850])
        print(f"📏 목표 범위(1650-1850자) 내 비율: {target_range_count}/{len(lengths)} ({target_range_count/len(lengths)*100:.1f}%)")
    
    # 표절 점수 통계
    plag_scores = [r.get('plag_score', 0) for r in successful_results if r]
    if plag_scores:
        avg_plag = sum(plag_scores) / len(plag_scores)
        max_plag = max(plag_scores)
        print(f"🔍 평균 표절 점수: {avg_plag:.4f} (최대: {max_plag:.4f})")
    
    # 최종 판정
    print(f"\n🎯 최종 운영 준비도:")
    if success_count == len(test_cases) and formal_ok_count >= len(successful_results) * 0.95:
        print("✅ 완벽한 운영 준비 완료! 🚀")
    elif success_count >= len(test_cases) * 0.8 and formal_ok_count >= len(successful_results) * 0.9:
        print("✅ 양호한 운영 준비 완료! 👍")
    else:
        print("⚠️ 추가 튜닝 필요")
    
    return results

if __name__ == "__main__":
    main()
