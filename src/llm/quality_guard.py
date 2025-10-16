#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
생성 품질검증 가드 모듈
"""
import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from .prompts import PromptConfig

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """품질 검증 결과"""
    passed: bool
    reasons: List[str]
    scores: Dict[str, str]
    retries: int = 0


class QualityGuard:
    """생성 품질검증 가드"""
    
    def __init__(self, config: Optional[PromptConfig] = None):
        self.config = config or PromptConfig()
    
    def check_content_quality(self, content: str) -> QualityResult:
        """콘텐츠 품질 검증"""
        reasons = []
        scores = {}
        
        # 1. 글 길이 검증
        length_score = self._check_length(content)
        scores["length"] = length_score
        if length_score == "실패":
            reasons.append("length")
        
        # 2. 소제목 수 검증
        subheading_score = self._check_subheadings(content)
        scores["subheadings"] = subheading_score
        if subheading_score == "실패":
            reasons.append("subheadings")
        
        # 3. 체크리스트 포함 검증
        checklist_score = self._check_checklist(content)
        scores["checklist"] = checklist_score
        if checklist_score == "실패":
            reasons.append("checklist")
        
        # 4. 디스클레이머 포함 검증
        disclaimer_score = self._check_disclaimer(content)
        scores["disclaimer"] = disclaimer_score
        if disclaimer_score == "실패":
            reasons.append("disclaimer")
        
        # 5. 구조적 완성도 검증
        structure_score = self._check_structure(content)
        scores["structure"] = structure_score
        if structure_score == "실패":
            reasons.append("structure")
        
        # 6. 톤앤매너 검증
        tone_score = self._check_tone(content)
        scores["tone"] = tone_score
        if tone_score == "실패":
            reasons.append("tone")
        
        # 전체 통과 여부
        passed = len(reasons) == 0
        
        return QualityResult(
            passed=passed,
            reasons=reasons,
            scores=scores
        )
    
    def _check_length(self, content: str) -> str:
        """글 길이 검증"""
        char_count = len(content)
        
        if self.config.min_chars <= char_count <= self.config.max_chars:
            return "통과"
        else:
            logger.warning(f"글 길이 검증 실패: {char_count}자 (요구: {self.config.min_chars}-{self.config.max_chars}자)")
            return "실패"
    
    def _check_subheadings(self, content: str) -> str:
        """소제목 수 검증"""
        # ## 소제목 개수 확인
        subheading_count = len(re.findall(r'^##\s+', content, re.MULTILINE))
        
        if subheading_count >= self.config.min_subheadings:
            return "통과"
        else:
            logger.warning(f"소제목 수 검증 실패: {subheading_count}개 (요구: {self.config.min_subheadings}개 이상)")
            return "실패"
    
    def _check_checklist(self, content: str) -> str:
        """체크리스트 포함 검증"""
        if not self.config.require_checklist:
            return "통과"
        
        # 체크리스트 관련 키워드 확인
        checklist_keywords = [
            "체크리스트", "checklist", "□", "☐", "•", "✓", "체크"
        ]
        
        has_checklist = any(keyword in content for keyword in checklist_keywords)
        
        if has_checklist:
            return "통과"
        else:
            logger.warning("체크리스트 검증 실패: 체크리스트가 포함되지 않음")
            return "실패"
    
    def _check_disclaimer(self, content: str) -> str:
        """디스클레이머 포함 검증"""
        if not self.config.require_disclaimer:
            return "통과"
        
        # 디스클레이머 관련 키워드 확인
        disclaimer_keywords = [
            "디스클레이머", "disclaimer", "법적 고지", "법적 고지사항",
            "법적 자문", "전문가 상담", "개별 사안"
        ]
        
        has_disclaimer = any(keyword in content for keyword in disclaimer_keywords)
        
        if has_disclaimer:
            return "통과"
        else:
            logger.warning("디스클레이머 검증 실패: 법적 고지사항이 포함되지 않음")
            return "실패"
    
    def _check_structure(self, content: str) -> str:
        """구조적 완성도 검증"""
        # 필수 구조 요소 확인
        required_elements = [
            r'^#\s+',  # 제목
            r'^##\s+들어가는\s+글',  # 들어가는 글
            r'^##\s+마무리',  # 마무리
        ]
        
        missing_elements = []
        for pattern in required_elements:
            if not re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                missing_elements.append(pattern)
        
        if len(missing_elements) == 0:
            return "통과"
        else:
            logger.warning(f"구조 검증 실패: 누락된 요소 {len(missing_elements)}개")
            return "실패"
    
    def _check_tone(self, content: str) -> str:
        """톤앤매너 검증"""
        # 혜안 톤 관련 키워드 확인
        hyean_keywords = [
            "법무법인 혜안", "전문 변호사", "채권자", "채권 회수",
            "실용적", "구체적", "효과적", "전문적"
        ]
        
        # 부적절한 톤 키워드 확인
        inappropriate_keywords = [
            "확실히", "절대적으로", "100%", "완벽하게", "무조건"
        ]
        
        has_hyean_tone = any(keyword in content for keyword in hyean_keywords)
        has_inappropriate_tone = any(keyword in content for keyword in inappropriate_keywords)
        
        if has_hyean_tone and not has_inappropriate_tone:
            return "통과"
        else:
            logger.warning("톤앤매너 검증 실패: 혜안 톤이 부족하거나 부적절한 표현 포함")
            return "실패"
    
    def get_improvement_suggestions(self, reasons: List[str]) -> List[str]:
        """개선 제안 생성"""
        suggestions = []
        
        for reason in reasons:
            if reason == "length":
                suggestions.append(f"글 길이를 {self.config.min_chars:,}자 이상 {self.config.max_chars:,}자 이하로 조정해주세요.")
            elif reason == "subheadings":
                suggestions.append(f"## 소제목을 {self.config.min_subheadings}개 이상 추가해주세요.")
            elif reason == "checklist":
                suggestions.append("실무 체크리스트 섹션을 추가해주세요.")
            elif reason == "disclaimer":
                suggestions.append("법적 디스클레이머 섹션을 추가해주세요.")
            elif reason == "structure":
                suggestions.append("제목, 들어가는 글, 마무리 섹션을 모두 포함해주세요.")
            elif reason == "tone":
                suggestions.append("법무법인 혜안의 전문적이면서 따뜻한 톤을 유지해주세요.")
        
        return suggestions


class QualityValidator:
    """품질 검증기 (LLM 기반)"""
    
    def __init__(self, llm_provider, config: Optional[PromptConfig] = None):
        self.llm_provider = llm_provider
        self.config = config or PromptConfig()
        self.quality_guard = QualityGuard(config)
    
    def validate_with_llm(self, content: str) -> QualityResult:
        """LLM을 사용한 품질 검증"""
        try:
            # 품질 검증 프롬프트 생성
            from .prompts import get_quality_check_prompt
            quality_prompt = get_quality_check_prompt(self.config)
            
            # LLM 호출
            response = self.llm_provider.generate(quality_prompt, max_tokens=500)
            
            # JSON 응답 파싱
            try:
                # JSON 부분만 추출
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    result_data = json.loads(json_str)
                    
                    return QualityResult(
                        passed=result_data.get("passed", False),
                        reasons=result_data.get("issues", []),
                        scores=result_data.get("scores", {})
                    )
                else:
                    logger.warning("LLM 응답에서 JSON을 찾을 수 없음")
                    return self._fallback_validation(content)
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {e}")
                return self._fallback_validation(content)
                
        except Exception as e:
            logger.error(f"LLM 검증 오류: {e}")
            return self._fallback_validation(content)
    
    def _fallback_validation(self, content: str) -> QualityResult:
        """LLM 검증 실패 시 규칙 기반 검증으로 폴백"""
        logger.info("LLM 검증 실패, 규칙 기반 검증으로 폴백")
        return self.quality_guard.check_content_quality(content)


class AutoRegenerateLoop:
    """자동 재생성 루프"""
    
    def __init__(self, 
                 llm_provider, 
                 searcher,
                 config: Optional[PromptConfig] = None,
                 max_retries: int = 2):
        self.llm_provider = llm_provider
        self.searcher = searcher
        self.config = config or PromptConfig()
        self.max_retries = max_retries
        self.quality_guard = QualityGuard(config)
        self.validator = QualityValidator(llm_provider, config)
    
    def generate_with_quality_guard(self, query: str) -> Tuple[str, QualityResult]:
        """품질 가드가 포함된 생성"""
        from .prompts import build_hyean_prompt, get_refinement_prompt
        
        # 1단계: RAG 검색
        context_docs = self.searcher.search_with_rerank(query)
        
        # 2단계: 초기 프롬프트 생성
        system_prompt, user_prompt = build_hyean_prompt(query, context_docs, self.config)
        
        retries = 0
        current_prompt = user_prompt
        
        while retries <= self.max_retries:
            try:
                # 3단계: 콘텐츠 생성
                logger.info(f"콘텐츠 생성 시도 {retries + 1}/{self.max_retries + 1}")
                content = self.llm_provider.generate(
                    current_prompt, 
                    system_prompt, 
                    max_tokens=2000
                )
                
                # 4단계: 품질 검증
                quality_result = self.quality_guard.check_content_quality(content)
                quality_result.retries = retries
                
                if quality_result.passed:
                    logger.info(f"품질 검증 통과 (시도 {retries + 1})")
                    return content, quality_result
                else:
                    logger.warning(f"품질 검증 실패 (시도 {retries + 1}): {quality_result.reasons}")
                    
                    if retries < self.max_retries:
                        # 5단계: 개선 제안 생성 및 프롬프트 수정
                        suggestions = self.quality_guard.get_improvement_suggestions(quality_result.reasons)
                        current_prompt = get_refinement_prompt(current_prompt, suggestions, self.config)
                        retries += 1
                    else:
                        logger.error(f"최대 재시도 횟수 초과: {self.max_retries}")
                        return content, quality_result
                        
            except Exception as e:
                logger.error(f"생성 오류 (시도 {retries + 1}): {e}")
                if retries < self.max_retries:
                    retries += 1
                    continue
                else:
                    raise e
        
        # 이 지점에 도달하면 안 되지만, 안전장치
        return "", QualityResult(passed=False, reasons=["생성 실패"], scores={})


# 편의 함수들
def check_content_quality(content: str, config: Optional[PromptConfig] = None) -> QualityResult:
    """간편한 콘텐츠 품질 검증"""
    guard = QualityGuard(config)
    return guard.check_content_quality(content)


def generate_with_quality_guard(query: str, 
                               llm_provider, 
                               searcher,
                               config: Optional[PromptConfig] = None,
                               max_retries: int = 2) -> Tuple[str, QualityResult]:
    """간편한 품질 가드 생성"""
    loop = AutoRegenerateLoop(llm_provider, searcher, config, max_retries)
    return loop.generate_with_quality_guard(query)


# 테스트용 함수
def test_quality_guard():
    """품질 가드 테스트"""
    config = PromptConfig(
        min_chars=100,
        max_chars=200,
        min_subheadings=2,
        require_checklist=True,
        require_disclaimer=True
    )
    
    guard = QualityGuard(config)
    
    # 테스트 콘텐츠 1: 통과하는 콘텐츠
    good_content = """# 채권추심 절차 가이드

## 들어가는 글
채권 회수에 어려움을 겪고 계신가요?

## 절차 설명
채권추심은 내용증명 발송부터 시작됩니다.

## 비용 안내
지급명령 신청 비용은 채권액의 1/100입니다.

## 실무 체크리스트
□ 채권 발생 근거 서류 확인
□ 채무자 정보 수집

## 마무리
법무법인 혜안의 전문 변호사와 상담하시기 바랍니다.

<법적 디스클레이머>
본 내용은 일반적인 정보 제공을 위한 것입니다."""
    
    result1 = guard.check_content_quality(good_content)
    print(f"✅ 좋은 콘텐츠 테스트: {result1.passed} (이유: {result1.reasons})")
    
    # 테스트 콘텐츠 2: 실패하는 콘텐츠
    bad_content = """# 짧은 글
## 제목1
내용이 너무 짧습니다."""
    
    result2 = guard.check_content_quality(bad_content)
    print(f"✅ 나쁜 콘텐츠 테스트: {result2.passed} (이유: {result2.reasons})")
    
    # 개선 제안 테스트
    suggestions = guard.get_improvement_suggestions(result2.reasons)
    print(f"✅ 개선 제안 테스트: {len(suggestions)}개 제안")
    
    print("✅ QualityGuard 테스트 완료")


if __name__ == "__main__":
    test_quality_guard()
