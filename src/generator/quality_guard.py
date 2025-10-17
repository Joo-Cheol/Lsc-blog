"""
생성 품질 가드 모듈
- 길이, 소제목, 체크리스트, 디스클레이머 검증
- 자동 재시도 (최대 2회)
- 실패 사유를 프롬프트에 역주입
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QualityCheck(Enum):
    """품질 검사 항목"""
    LENGTH = "length"
    SUBHEADINGS = "subheadings"
    CHECKLIST = "checklist"
    DISCLAIMER = "disclaimer"
    SEO_KEYWORDS = "seo_keywords"
    EMPATHY_INTRO = "empathy_intro"
    CASE_STUDY = "case_study"
    PROCEDURE = "procedure"


@dataclass
class QualityResult:
    """품질 검사 결과"""
    passed: bool
    score: float  # 0.0 ~ 1.0
    failed_checks: List[QualityCheck]
    details: Dict[str, Any]
    suggestions: List[str]


class QualityGuard:
    """생성 품질 가드"""
    
    def __init__(self, 
                 min_chars: int = 1600,
                 max_chars: int = 1900,
                 min_subheadings: int = 3,
                 require_checklist: bool = True,
                 require_disclaimer: bool = True):
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.min_subheadings = min_subheadings
        self.require_checklist = require_checklist
        self.require_disclaimer = require_disclaimer
        
        # 패턴 정의
        self.subheading_pattern = re.compile(r'^#{1,3}\s+.+', re.MULTILINE)
        self.checklist_pattern = re.compile(r'체크리스트|✓|•|-\s*\[', re.IGNORECASE)
        self.disclaimer_pattern = re.compile(r'디스클레이머|면책|주의사항|법적.*고지', re.IGNORECASE)
        self.seo_keyword_pattern = re.compile(r'채권추심|법무법인|변호사|법률상담', re.IGNORECASE)
        self.empathy_pattern = re.compile(r'고민|어려움|힘들|걱정|불안', re.IGNORECASE)
        self.case_pattern = re.compile(r'사례|예시|경우|실제.*경험', re.IGNORECASE)
        self.procedure_pattern = re.compile(r'절차|단계|방법|과정|순서', re.IGNORECASE)
    
    def check_length(self, content: str) -> Tuple[bool, Dict[str, Any]]:
        """길이 검사"""
        char_count = len(content)
        word_count = len(content.split())
        
        passed = self.min_chars <= char_count <= self.max_chars
        
        details = {
            "char_count": char_count,
            "word_count": word_count,
            "min_required": self.min_chars,
            "max_allowed": self.max_chars,
            "within_range": passed
        }
        
        return passed, details
    
    def check_subheadings(self, content: str) -> Tuple[bool, Dict[str, Any]]:
        """소제목 검사"""
        subheadings = self.subheading_pattern.findall(content)
        subheading_count = len(subheadings)
        
        passed = subheading_count >= self.min_subheadings
        
        details = {
            "count": subheading_count,
            "min_required": self.min_subheadings,
            "subheadings": subheadings[:5],  # 처음 5개만
            "sufficient": passed
        }
        
        return passed, details
    
    def check_checklist(self, content: str) -> Tuple[bool, Dict[str, Any]]:
        """체크리스트 검사"""
        if not self.require_checklist:
            return True, {"required": False}
        
        checklist_found = bool(self.checklist_pattern.search(content))
        
        details = {
            "found": checklist_found,
            "required": self.require_checklist,
            "pattern_matches": len(self.checklist_pattern.findall(content))
        }
        
        return checklist_found, details
    
    def check_disclaimer(self, content: str) -> Tuple[bool, Dict[str, Any]]:
        """디스클레이머 검사"""
        if not self.require_disclaimer:
            return True, {"required": False}
        
        disclaimer_found = bool(self.disclaimer_pattern.search(content))
        
        details = {
            "found": disclaimer_found,
            "required": self.require_disclaimer,
            "pattern_matches": len(self.disclaimer_pattern.findall(content))
        }
        
        return disclaimer_found, details
    
    def check_seo_keywords(self, content: str) -> Tuple[bool, Dict[str, Any]]:
        """SEO 키워드 검사"""
        keywords_found = self.seo_keyword_pattern.findall(content)
        keyword_count = len(keywords_found)
        
        passed = keyword_count >= 2  # 최소 2개 키워드
        
        details = {
            "count": keyword_count,
            "keywords": list(set(keywords_found)),
            "min_required": 2,
            "sufficient": passed
        }
        
        return passed, details
    
    def check_empathy_intro(self, content: str) -> Tuple[bool, Dict[str, Any]]:
        """공감형 도입부 검사"""
        # 첫 200자에서 공감 표현 확인
        intro = content[:200]
        empathy_found = bool(self.empathy_pattern.search(intro))
        
        details = {
            "found": empathy_found,
            "intro_text": intro,
            "pattern_matches": len(self.empathy_pattern.findall(intro))
        }
        
        return empathy_found, details
    
    def check_case_study(self, content: str) -> Tuple[bool, Dict[str, Any]]:
        """사례 연구 검사"""
        case_found = bool(self.case_pattern.search(content))
        
        details = {
            "found": case_found,
            "pattern_matches": len(self.case_pattern.findall(content))
        }
        
        return case_found, details
    
    def check_procedure(self, content: str) -> Tuple[bool, Dict[str, Any]]:
        """절차 설명 검사"""
        procedure_found = bool(self.procedure_pattern.search(content))
        
        details = {
            "found": procedure_found,
            "pattern_matches": len(self.procedure_pattern.findall(content))
        }
        
        return procedure_found, details
    
    def evaluate_quality(self, content: str) -> QualityResult:
        """전체 품질 평가"""
        failed_checks = []
        all_details = {}
        suggestions = []
        
        # 각 검사 실행
        checks = [
            (QualityCheck.LENGTH, self.check_length),
            (QualityCheck.SUBHEADINGS, self.check_subheadings),
            (QualityCheck.CHECKLIST, self.check_checklist),
            (QualityCheck.DISCLAIMER, self.check_disclaimer),
            (QualityCheck.SEO_KEYWORDS, self.check_seo_keywords),
            (QualityCheck.EMPATHY_INTRO, self.check_empathy_intro),
            (QualityCheck.CASE_STUDY, self.check_case_study),
            (QualityCheck.PROCEDURE, self.check_procedure)
        ]
        
        for check_type, check_func in checks:
            passed, details = check_func(content)
            all_details[check_type.value] = details
            
            if not passed:
                failed_checks.append(check_type)
                
                # 구체적인 제안 생성
                if check_type == QualityCheck.LENGTH:
                    char_count = details["char_count"]
                    if char_count < self.min_chars:
                        suggestions.append(f"내용이 {char_count}자로 부족합니다. 최소 {self.min_chars}자 이상 작성해주세요.")
                    elif char_count > self.max_chars:
                        suggestions.append(f"내용이 {char_count}자로 너무 깁니다. {self.max_chars}자 이하로 줄여주세요.")
                
                elif check_type == QualityCheck.SUBHEADINGS:
                    suggestions.append(f"소제목이 {details['count']}개로 부족합니다. 최소 {self.min_subheadings}개 이상 추가해주세요.")
                
                elif check_type == QualityCheck.CHECKLIST:
                    suggestions.append("체크리스트나 요약 포인트를 포함해주세요.")
                
                elif check_type == QualityCheck.DISCLAIMER:
                    suggestions.append("법적 디스클레이머나 주의사항을 포함해주세요.")
                
                elif check_type == QualityCheck.SEO_KEYWORDS:
                    suggestions.append("채권추심, 법무법인, 변호사 등 관련 키워드를 더 포함해주세요.")
                
                elif check_type == QualityCheck.EMPATHY_INTRO:
                    suggestions.append("도입부에 고객의 고민이나 어려움에 대한 공감 표현을 포함해주세요.")
        
        # 전체 점수 계산
        total_checks = len(checks)
        passed_checks = total_checks - len(failed_checks)
        score = passed_checks / total_checks
        
        return QualityResult(
            passed=len(failed_checks) == 0,
            score=score,
            failed_checks=failed_checks,
            details=all_details,
            suggestions=suggestions
        )
    
    def generate_retry_prompt(self, original_prompt: str, quality_result: QualityResult) -> str:
        """재시도용 프롬프트 생성"""
        if quality_result.passed:
            return original_prompt
        
        retry_instructions = []
        
        for check in quality_result.failed_checks:
            if check == QualityCheck.LENGTH:
                retry_instructions.append("내용 길이를 1,600-1,900자 범위로 조정해주세요.")
            elif check == QualityCheck.SUBHEADINGS:
                retry_instructions.append("최소 3개 이상의 소제목(## 또는 ###)을 포함해주세요.")
            elif check == QualityCheck.CHECKLIST:
                retry_instructions.append("체크리스트나 요약 포인트를 반드시 포함해주세요.")
            elif check == QualityCheck.DISCLAIMER:
                retry_instructions.append("법적 디스클레이머나 주의사항을 반드시 포함해주세요.")
            elif check == QualityCheck.SEO_KEYWORDS:
                retry_instructions.append("채권추심, 법무법인, 변호사 등 관련 키워드를 충분히 포함해주세요.")
            elif check == QualityCheck.EMPATHY_INTRO:
                retry_instructions.append("도입부에 고객의 고민에 대한 공감 표현을 포함해주세요.")
        
        retry_prompt = f"""
{original_prompt}

[품질 검사 결과]
다음 요구사항을 반드시 충족해주세요:
{chr(10).join(f"- {instruction}" for instruction in retry_instructions)}

실패한 검사 항목: {', '.join([check.value for check in quality_result.failed_checks])}
현재 점수: {quality_result.score:.1%}

위 요구사항을 모두 만족하는 고품질 콘텐츠로 다시 작성해주세요.
"""
        
        return retry_prompt


# 전역 인스턴스
quality_guard = QualityGuard()
