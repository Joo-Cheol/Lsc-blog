#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
품질 가드 모듈 단위 테스트
"""
import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.quality_guard import (
    QualityResult, QualityGuard, QualityValidator, AutoRegenerateLoop,
    check_content_quality, generate_with_quality_guard
)
from src.llm.prompts import PromptConfig


class TestQualityResult(unittest.TestCase):
    """QualityResult 테스트"""
    
    def test_quality_result_creation(self):
        """품질 결과 생성 테스트"""
        result = QualityResult(
            passed=True,
            reasons=[],
            scores={"length": "통과", "subheadings": "통과"},
            retries=0
        )
        
        self.assertTrue(result.passed)
        self.assertEqual(len(result.reasons), 0)
        self.assertEqual(result.scores["length"], "통과")
        self.assertEqual(result.retries, 0)
    
    def test_quality_result_failure(self):
        """품질 결과 실패 테스트"""
        result = QualityResult(
            passed=False,
            reasons=["length", "subheadings"],
            scores={"length": "실패", "subheadings": "실패"},
            retries=2
        )
        
        self.assertFalse(result.passed)
        self.assertEqual(len(result.reasons), 2)
        self.assertIn("length", result.reasons)
        self.assertIn("subheadings", result.reasons)
        self.assertEqual(result.retries, 2)


class TestQualityGuard(unittest.TestCase):
    """QualityGuard 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = PromptConfig(
            min_chars=100,
            max_chars=200,
            min_subheadings=2,
            require_checklist=True,
            require_disclaimer=True
        )
        self.guard = QualityGuard(self.config)
    
    def test_check_length_pass(self):
        """글 길이 검증 통과 테스트"""
        content = "a" * 150  # 150자
        result = self.guard._check_length(content)
        self.assertEqual(result, "통과")
    
    def test_check_length_fail_short(self):
        """글 길이 검증 실패 (짧음) 테스트"""
        content = "a" * 50  # 50자
        result = self.guard._check_length(content)
        self.assertEqual(result, "실패")
    
    def test_check_length_fail_long(self):
        """글 길이 검증 실패 (김) 테스트"""
        content = "a" * 250  # 250자
        result = self.guard._check_length(content)
        self.assertEqual(result, "실패")
    
    def test_check_subheadings_pass(self):
        """소제목 수 검증 통과 테스트"""
        content = """# 제목
## 소제목1
내용1
## 소제목2
내용2
## 소제목3
내용3"""
        result = self.guard._check_subheadings(content)
        self.assertEqual(result, "통과")
    
    def test_check_subheadings_fail(self):
        """소제목 수 검증 실패 테스트"""
        content = """# 제목
## 소제목1
내용1"""
        result = self.guard._check_subheadings(content)
        self.assertEqual(result, "실패")
    
    def test_check_checklist_pass(self):
        """체크리스트 검증 통과 테스트"""
        content = """# 제목
## 실무 체크리스트
□ 항목1
□ 항목2"""
        result = self.guard._check_checklist(content)
        self.assertEqual(result, "통과")
    
    def test_check_checklist_fail(self):
        """체크리스트 검증 실패 테스트"""
        content = """# 제목
## 내용
일반적인 내용입니다."""
        result = self.guard._check_checklist(content)
        self.assertEqual(result, "실패")
    
    def test_check_disclaimer_pass(self):
        """디스클레이머 검증 통과 테스트"""
        content = """# 제목
## 내용
일반적인 내용입니다.

<법적 디스클레이머>
본 내용은 일반적인 정보 제공을 위한 것입니다."""
        result = self.guard._check_disclaimer(content)
        self.assertEqual(result, "통과")
    
    def test_check_disclaimer_fail(self):
        """디스클레이머 검증 실패 테스트"""
        content = """# 제목
## 내용
일반적인 내용입니다."""
        result = self.guard._check_disclaimer(content)
        self.assertEqual(result, "실패")
    
    def test_check_structure_pass(self):
        """구조 검증 통과 테스트"""
        content = """# 제목
## 들어가는 글
도입부입니다.
## 본문
본문 내용입니다.
## 마무리
마무리 내용입니다."""
        result = self.guard._check_structure(content)
        self.assertEqual(result, "통과")
    
    def test_check_structure_fail(self):
        """구조 검증 실패 테스트"""
        content = """## 소제목
내용만 있습니다."""
        result = self.guard._check_structure(content)
        self.assertEqual(result, "실패")
    
    def test_check_tone_pass(self):
        """톤앤매너 검증 통과 테스트"""
        content = """# 채권추심 절차
법무법인 혜안의 전문 변호사가 채권자에게 실용적인 조언을 제공합니다."""
        result = self.guard._check_tone(content)
        self.assertEqual(result, "통과")
    
    def test_check_tone_fail(self):
        """톤앤매너 검증 실패 테스트"""
        content = """# 일반적인 글
확실히 100% 완벽하게 무조건 성공할 것입니다."""
        result = self.guard._check_tone(content)
        self.assertEqual(result, "실패")
    
    def test_check_content_quality_pass(self):
        """전체 품질 검증 통과 테스트"""
        content = """# 채권추심 절차 가이드

## 들어가는 글
채권 회수에 어려움을 겪고 계신가요?

## 절차 설명
채권추심은 내용증명 발송부터 시작됩니다.

## 실무 체크리스트
□ 채권 발생 근거 서류 확인
□ 채무자 정보 수집

## 마무리
법무법인 혜안의 전문 변호사와 상담하시기 바랍니다.

<법적 디스클레이머>
본 내용은 일반적인 정보 제공을 위한 것입니다."""
        
        result = self.guard.check_content_quality(content)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.reasons), 0)
        self.assertEqual(result.scores["length"], "통과")
        self.assertEqual(result.scores["subheadings"], "통과")
        self.assertEqual(result.scores["checklist"], "통과")
        self.assertEqual(result.scores["disclaimer"], "통과")
        self.assertEqual(result.scores["structure"], "통과")
        self.assertEqual(result.scores["tone"], "통과")
    
    def test_check_content_quality_fail(self):
        """전체 품질 검증 실패 테스트"""
        content = """# 짧은 글
## 제목1
내용이 너무 짧습니다."""
        
        result = self.guard.check_content_quality(content)
        self.assertFalse(result.passed)
        self.assertGreater(len(result.reasons), 0)
        self.assertIn("length", result.reasons)
        self.assertIn("subheadings", result.reasons)
    
    def test_get_improvement_suggestions(self):
        """개선 제안 생성 테스트"""
        reasons = ["length", "subheadings", "checklist", "disclaimer"]
        suggestions = self.guard.get_improvement_suggestions(reasons)
        
        self.assertEqual(len(suggestions), 4)
        self.assertIn("글 길이를", suggestions[0])
        self.assertIn("소제목을", suggestions[1])
        self.assertIn("체크리스트", suggestions[2])
        self.assertIn("디스클레이머", suggestions[3])


class TestQualityValidator(unittest.TestCase):
    """QualityValidator 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_llm = MagicMock()
        self.config = PromptConfig()
        self.validator = QualityValidator(self.mock_llm, self.config)
    
    def test_validate_with_llm_success(self):
        """LLM 검증 성공 테스트"""
        # Mock LLM 응답
        mock_response = '''
        {
            "passed": true,
            "issues": [],
            "scores": {
                "length": "통과",
                "subheadings": "통과",
                "checklist": "통과",
                "disclaimer": "통과",
                "structure": "통과",
                "tone": "통과"
            }
        }
        '''
        self.mock_llm.generate.return_value = mock_response
        
        content = "테스트 콘텐츠"
        result = self.validator.validate_with_llm(content)
        
        self.assertTrue(result.passed)
        self.assertEqual(len(result.reasons), 0)
        self.assertEqual(result.scores["length"], "통과")
    
    def test_validate_with_llm_failure(self):
        """LLM 검증 실패 테스트"""
        # Mock LLM 응답
        mock_response = '''
        {
            "passed": false,
            "issues": ["length", "subheadings"],
            "scores": {
                "length": "실패",
                "subheadings": "실패",
                "checklist": "통과",
                "disclaimer": "통과",
                "structure": "통과",
                "tone": "통과"
            }
        }
        '''
        self.mock_llm.generate.return_value = mock_response
        
        content = "짧은 글"
        result = self.validator.validate_with_llm(content)
        
        self.assertFalse(result.passed)
        self.assertEqual(len(result.reasons), 2)
        self.assertIn("length", result.reasons)
        self.assertIn("subheadings", result.reasons)
    
    def test_validate_with_llm_json_error(self):
        """LLM 검증 JSON 오류 테스트"""
        # 잘못된 JSON 응답
        self.mock_llm.generate.return_value = "잘못된 응답"
        
        content = "테스트 콘텐츠"
        result = self.validator.validate_with_llm(content)
        
        # 폴백 검증이 실행되어야 함
        self.assertIsInstance(result, QualityResult)
    
    def test_validate_with_llm_exception(self):
        """LLM 검증 예외 테스트"""
        # LLM 호출 예외
        self.mock_llm.generate.side_effect = Exception("LLM 오류")
        
        content = "테스트 콘텐츠"
        result = self.validator.validate_with_llm(content)
        
        # 폴백 검증이 실행되어야 함
        self.assertIsInstance(result, QualityResult)


class TestAutoRegenerateLoop(unittest.TestCase):
    """AutoRegenerateLoop 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_llm = MagicMock()
        self.mock_searcher = MagicMock()
        self.config = PromptConfig(
            min_chars=100,
            max_chars=200,
            min_subheadings=2,
            require_checklist=True,
            require_disclaimer=True
        )
        self.loop = AutoRegenerateLoop(
            self.mock_llm, 
            self.mock_searcher, 
            self.config, 
            max_retries=1
        )
    
    def test_generate_with_quality_guard_success_first_try(self):
        """품질 가드 생성 성공 (첫 시도) 테스트"""
        # Mock 검색 결과
        self.mock_searcher.search_with_rerank.return_value = [
            {"text": "테스트 컨텍스트", "metadata": {"source_url": "https://test.com"}}
        ]
        
        # Mock LLM 응답 (품질 통과)
        good_content = """# 채권추심 절차 가이드

## 들어가는 글
채권 회수에 어려움을 겪고 계신가요?

## 절차 설명
채권추심은 내용증명 발송부터 시작됩니다.

## 실무 체크리스트
□ 채권 발생 근거 서류 확인
□ 채무자 정보 수집

## 마무리
법무법인 혜안의 전문 변호사와 상담하시기 바랍니다.

<법적 디스클레이머>
본 내용은 일반적인 정보 제공을 위한 것입니다."""
        
        self.mock_llm.generate.return_value = good_content
        
        query = "채권추심 절차"
        content, result = self.loop.generate_with_quality_guard(query)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.retries, 0)
        self.assertIn("채권추심 절차 가이드", content)
    
    def test_generate_with_quality_guard_retry_success(self):
        """품질 가드 생성 재시도 성공 테스트"""
        # Mock 검색 결과
        self.mock_searcher.search_with_rerank.return_value = [
            {"text": "테스트 컨텍스트", "metadata": {"source_url": "https://test.com"}}
        ]
        
        # Mock LLM 응답 (첫 시도: 실패, 두 번째 시도: 성공)
        bad_content = "짧은 글"
        good_content = """# 채권추심 절차 가이드

## 들어가는 글
채권 회수에 어려움을 겪고 계신가요?

## 절차 설명
채권추심은 내용증명 발송부터 시작됩니다.

## 실무 체크리스트
□ 채권 발생 근거 서류 확인
□ 채무자 정보 수집

## 마무리
법무법인 혜안의 전문 변호사와 상담하시기 바랍니다.

<법적 디스클레이머>
본 내용은 일반적인 정보 제공을 위한 것입니다."""
        
        self.mock_llm.generate.side_effect = [bad_content, good_content]
        
        query = "채권추심 절차"
        content, result = self.loop.generate_with_quality_guard(query)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.retries, 1)
        self.assertIn("채권추심 절차 가이드", content)
    
    def test_generate_with_quality_guard_max_retries_exceeded(self):
        """품질 가드 생성 최대 재시도 초과 테스트"""
        # Mock 검색 결과
        self.mock_searcher.search_with_rerank.return_value = [
            {"text": "테스트 컨텍스트", "metadata": {"source_url": "https://test.com"}}
        ]
        
        # Mock LLM 응답 (모두 실패)
        bad_content = "짧은 글"
        self.mock_llm.generate.return_value = bad_content
        
        query = "채권추심 절차"
        content, result = self.loop.generate_with_quality_guard(query)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.retries, 1)  # max_retries = 1
        self.assertEqual(content, bad_content)


class TestConvenienceFunctions(unittest.TestCase):
    """편의 함수 테스트"""
    
    def test_check_content_quality_function(self):
        """check_content_quality 함수 테스트"""
        content = """# 채권추심 절차 가이드

## 들어가는 글
채권 회수에 어려움을 겪고 계신가요?

## 절차 설명
채권추심은 내용증명 발송부터 시작됩니다.

## 실무 체크리스트
□ 채권 발생 근거 서류 확인
□ 채무자 정보 수집

## 마무리
법무법인 혜안의 전문 변호사와 상담하시기 바랍니다.

<법적 디스클레이머>
본 내용은 일반적인 정보 제공을 위한 것입니다."""
        
        config = PromptConfig(
            min_chars=100,
            max_chars=200,
            min_subheadings=2,
            require_checklist=True,
            require_disclaimer=True
        )
        
        result = check_content_quality(content, config)
        self.assertTrue(result.passed)
    
    @patch('src.llm.quality_guard.AutoRegenerateLoop')
    def test_generate_with_quality_guard_function(self, mock_loop_class):
        """generate_with_quality_guard 함수 테스트"""
        # Mock 설정
        mock_loop = MagicMock()
        mock_loop_class.return_value = mock_loop
        mock_loop.generate_with_quality_guard.return_value = ("생성된 콘텐츠", QualityResult(passed=True, reasons=[], scores={}))
        
        # 함수 호출
        mock_llm = MagicMock()
        mock_searcher = MagicMock()
        config = PromptConfig()
        
        content, result = generate_with_quality_guard(
            "테스트 쿼리", 
            mock_llm, 
            mock_searcher, 
            config, 
            max_retries=2
        )
        
        # 검증
        self.assertEqual(content, "생성된 콘텐츠")
        self.assertTrue(result.passed)
        mock_loop_class.assert_called_once_with(mock_llm, mock_searcher, config, 2)
        mock_loop.generate_with_quality_guard.assert_called_once_with("테스트 쿼리")


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_full_quality_guard_flow(self):
        """전체 품질 가드 플로우 테스트"""
        # 1단계: 설정 생성
        config = PromptConfig(
            min_chars=100,
            max_chars=200,
            min_subheadings=2,
            require_checklist=True,
            require_disclaimer=True
        )
        
        # 2단계: 품질 가드 생성
        guard = QualityGuard(config)
        
        # 3단계: 좋은 콘텐츠 검증
        good_content = """# 채권추심 절차 가이드

## 들어가는 글
채권 회수에 어려움을 겪고 계신가요?

## 절차 설명
채권추심은 내용증명 발송부터 시작됩니다.

## 실무 체크리스트
□ 채권 발생 근거 서류 확인
□ 채무자 정보 수집

## 마무리
법무법인 혜안의 전문 변호사와 상담하시기 바랍니다.

<법적 디스클레이머>
본 내용은 일반적인 정보 제공을 위한 것입니다."""
        
        result = guard.check_content_quality(good_content)
        self.assertTrue(result.passed)
        
        # 4단계: 나쁜 콘텐츠 검증
        bad_content = "짧은 글"
        result = guard.check_content_quality(bad_content)
        self.assertFalse(result.passed)
        
        # 5단계: 개선 제안 생성
        suggestions = guard.get_improvement_suggestions(result.reasons)
        self.assertGreater(len(suggestions), 0)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
