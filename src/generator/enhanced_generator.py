"""
향상된 생성기 모듈
- 품질 가드 통합
- 자동 재시도 (최대 2회)
- 실패 사유를 프롬프트에 역주입
"""

import logging
from typing import Dict, Any, Optional, List
import time
from datetime import datetime

from .quality_guard import quality_guard, QualityResult
from .guide_based_generator import GuideBasedGenerator

logger = logging.getLogger(__name__)


class EnhancedGenerator:
    """품질 가드가 통합된 향상된 생성기"""
    
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.base_generator = GuideBasedGenerator()
    
    def generate_with_quality_guard(self, 
                                  query: str,
                                  search_results: List[Dict[str, Any]],
                                  additional_context: Optional[str] = None) -> Dict[str, Any]:
        """
        품질 가드가 적용된 콘텐츠 생성
        
        Args:
            query: 생성 쿼리
            search_results: 검색 결과
            additional_context: 추가 컨텍스트
            
        Returns:
            생성 결과와 품질 정보
        """
        start_time = time.time()
        
        # 초기 프롬프트 생성
        original_prompt = self._build_prompt(query, search_results, additional_context)
        
        retry_count = 0
        best_result = None
        best_quality = None
        all_attempts = []
        
        while retry_count <= self.max_retries:
            attempt_start = time.time()
            
            try:
                # 콘텐츠 생성
                if retry_count == 0:
                    current_prompt = original_prompt
                else:
                    # 재시도 시 개선된 프롬프트 사용
                    current_prompt = quality_guard.generate_retry_prompt(
                        original_prompt, best_quality
                    )
                
                generated_content = self.base_generator.generate(
                    prompt=current_prompt,
                    query=query,
                    search_results=search_results
                )
                
                # 품질 검사
                quality_result = quality_guard.evaluate_quality(generated_content)
                
                attempt_info = {
                    "attempt": retry_count + 1,
                    "prompt_length": len(current_prompt),
                    "content_length": len(generated_content),
                    "quality_score": quality_result.score,
                    "passed": quality_result.passed,
                    "failed_checks": [check.value for check in quality_result.failed_checks],
                    "generation_time": time.time() - attempt_start
                }
                all_attempts.append(attempt_info)
                
                # 최고 결과 업데이트
                if best_result is None or quality_result.score > best_quality.score:
                    best_result = generated_content
                    best_quality = quality_result
                
                # 품질 통과 시 조기 종료
                if quality_result.passed:
                    logger.info(f"Quality check passed on attempt {retry_count + 1}")
                    break
                
                # 재시도 필요
                retry_count += 1
                if retry_count <= self.max_retries:
                    logger.warning(f"Quality check failed on attempt {retry_count}, retrying...")
                    logger.warning(f"Failed checks: {[check.value for check in quality_result.failed_checks]}")
                
            except Exception as e:
                logger.error(f"Generation attempt {retry_count + 1} failed: {e}")
                retry_count += 1
                if retry_count > self.max_retries:
                    raise
        
        # 최종 결과 구성
        total_time = time.time() - start_time
        
        result = {
            "content": best_result,
            "quality": {
                "passed": best_quality.passed if best_quality else False,
                "score": best_quality.score if best_quality else 0.0,
                "failed_checks": [check.value for check in best_quality.failed_checks] if best_quality else [],
                "details": best_quality.details if best_quality else {},
                "suggestions": best_quality.suggestions if best_quality else []
            },
            "generation": {
                "total_attempts": len(all_attempts),
                "total_time": total_time,
                "attempts": all_attempts,
                "retry_reasons": [attempt["failed_checks"] for attempt in all_attempts if not attempt["passed"]]
            },
            "metadata": {
                "query": query,
                "search_results_count": len(search_results),
                "generated_at": datetime.now().isoformat(),
                "generator_version": "enhanced_v1.0"
            }
        }
        
        # 로깅
        if best_quality and best_quality.passed:
            logger.info(f"Successfully generated content with quality score {best_quality.score:.2f} in {total_time:.2f}s")
        else:
            logger.warning(f"Generated content with quality score {best_quality.score if best_quality else 0:.2f} after {len(all_attempts)} attempts")
        
        return result
    
    def _build_prompt(self, query: str, search_results: List[Dict[str, Any]], 
                     additional_context: Optional[str] = None) -> str:
        """기본 프롬프트 구성"""
        # 검색 결과를 컨텍스트로 변환
        context_parts = []
        for i, result in enumerate(search_results[:5]):  # 상위 5개만 사용
            context_parts.append(f"[참고자료 {i+1}]\n{result.get('document', '')}\n")
        
        context = "\n".join(context_parts)
        
        base_prompt = f"""
당신은 법무 전문가입니다. 아래 참고자료를 바탕으로 고품질의 법률 블로그 포스트를 작성해주세요.

[요청 주제]
{query}

[참고자료]
{context}

[추가 컨텍스트]
{additional_context or "없음"}

[작성 요구사항]
1. 길이: 1,600-1,900자
2. 구조: 공감형 도입 → 사례/절차 → 체크리스트 → 디스클레이머
3. 소제목: 최소 3개 이상 (## 또는 ###)
4. 키워드: 채권추심, 법무법인, 변호사 등 관련 키워드 포함
5. 톤앤매너: 전문적이면서도 이해하기 쉬운 혜안 톤
6. SEO: 검색 최적화된 제목과 구조

[품질 기준]
- 고객의 고민에 공감하는 도입부
- 구체적인 사례나 절차 설명
- 실용적인 체크리스트나 요약
- 법적 디스클레이머 포함
- 전문적이면서 접근하기 쉬운 내용

위 요구사항을 모두 만족하는 고품질 콘텐츠를 작성해주세요.
"""
        
        return base_prompt
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """생성 통계 반환"""
        return {
            "max_retries": self.max_retries,
            "quality_guard_config": {
                "min_chars": quality_guard.min_chars,
                "max_chars": quality_guard.max_chars,
                "min_subheadings": quality_guard.min_subheadings,
                "require_checklist": quality_guard.require_checklist,
                "require_disclaimer": quality_guard.require_disclaimer
            },
            "generator_type": "enhanced_with_quality_guard"
        }


# 전역 인스턴스
enhanced_generator = EnhancedGenerator()
