#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프롬프트 모듈 단위 테스트
"""
import unittest
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.prompts import (
    PromptConfig, HyeanPromptBuilder, PromptTemplates,
    build_hyean_prompt, get_quality_check_prompt, get_refinement_prompt
)


class TestPromptConfig(unittest.TestCase):
    """PromptConfig 테스트"""
    
    def test_default_config(self):
        """기본 설정 테스트"""
        config = PromptConfig()
        
        self.assertEqual(config.min_chars, 1600)
        self.assertEqual(config.max_chars, 1900)
        self.assertEqual(config.min_subheadings, 3)
        self.assertTrue(config.require_checklist)
        self.assertTrue(config.require_disclaimer)
        self.assertEqual(config.law_topic, "채권추심")
        self.assertEqual(config.tone, "혜안")
    
    def test_custom_config(self):
        """사용자 정의 설정 테스트"""
        config = PromptConfig(
            min_chars=1000,
            max_chars=1500,
            min_subheadings=2,
            require_checklist=False,
            require_disclaimer=False,
            law_topic="계약",
            tone="친근"
        )
        
        self.assertEqual(config.min_chars, 1000)
        self.assertEqual(config.max_chars, 1500)
        self.assertEqual(config.min_subheadings, 2)
        self.assertFalse(config.require_checklist)
        self.assertFalse(config.require_disclaimer)
        self.assertEqual(config.law_topic, "계약")
        self.assertEqual(config.tone, "친근")


class TestHyeanPromptBuilder(unittest.TestCase):
    """HyeanPromptBuilder 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = PromptConfig(
            min_chars=1000,
            max_chars=1500,
            min_subheadings=2,
            require_checklist=True,
            require_disclaimer=True
        )
        self.builder = HyeanPromptBuilder(self.config)
    
    def test_system_prompt_generation(self):
        """시스템 프롬프트 생성 테스트"""
        system_prompt = self.builder.build_system_prompt()
        
        # 기본 검증
        self.assertIsInstance(system_prompt, str)
        self.assertGreater(len(system_prompt), 100)
        
        # 내용 검증
        self.assertIn("법무법인 혜안", system_prompt)
        self.assertIn("채권추심", system_prompt)
        self.assertIn("채권자", system_prompt)
        self.assertIn("전문 변호사", system_prompt)
    
    def test_user_prompt_generation(self):
        """사용자 프롬프트 생성 테스트"""
        query = "채권추심 절차에 대해 설명해주세요"
        context_docs = [
            {
                "text": "채권추심은 내용증명 발송부터 시작됩니다.",
                "metadata": {"source_url": "https://test.com/1"}
            },
            {
                "text": "지급명령 신청 시 필요한 서류들을 준비해야 합니다.",
                "metadata": {"source_url": "https://test.com/2"}
            }
        ]
        
        user_prompt = self.builder.build_user_prompt(query, context_docs)
        
        # 기본 검증
        self.assertIsInstance(user_prompt, str)
        self.assertGreater(len(user_prompt), 100)
        
        # 내용 검증
        self.assertIn(query, user_prompt)
        self.assertIn("1,000자 이상 1,500자 이하", user_prompt)
        self.assertIn("최소 2개", user_prompt)
        self.assertIn("체크리스트", user_prompt)
        self.assertIn("디스클레이머", user_prompt)
        self.assertIn("https://test.com/1", user_prompt)
        self.assertIn("https://test.com/2", user_prompt)
    
    def test_user_prompt_without_context(self):
        """컨텍스트 없는 사용자 프롬프트 테스트"""
        query = "채권추심 절차에 대해 설명해주세요"
        context_docs = []
        
        user_prompt = self.builder.build_user_prompt(query, context_docs)
        
        # 기본 검증
        self.assertIsInstance(user_prompt, str)
        self.assertIn("참고 자료가 없습니다", user_prompt)
        self.assertIn(query, user_prompt)
    
    def test_refinement_prompt_generation(self):
        """개선 요청 프롬프트 생성 테스트"""
        original_prompt = "원본 프롬프트 내용입니다."
        issues = ["글 길이가 부족합니다", "소제목이 부족합니다"]
        
        refinement_prompt = self.builder.build_refinement_prompt(original_prompt, issues)
        
        # 기본 검증
        self.assertIsInstance(refinement_prompt, str)
        self.assertGreater(len(refinement_prompt), 50)
        
        # 내용 검증
        self.assertIn("문제점들이 있습니다", refinement_prompt)
        self.assertIn("글 길이가 부족합니다", refinement_prompt)
        self.assertIn("소제목이 부족합니다", refinement_prompt)
        self.assertIn(original_prompt, refinement_prompt)
    
    def test_quality_check_prompt_generation(self):
        """품질 검증 프롬프트 생성 테스트"""
        quality_prompt = self.builder.get_quality_check_prompt()
        
        # 기본 검증
        self.assertIsInstance(quality_prompt, str)
        self.assertGreater(len(quality_prompt), 100)
        
        # 내용 검증
        self.assertIn("품질을 검증", quality_prompt)
        self.assertIn("1,000자 이상 1,500자 이하", quality_prompt)
        self.assertIn("2개 이상", quality_prompt)
        self.assertIn("체크리스트", quality_prompt)
        self.assertIn("디스클레이머", quality_prompt)
        self.assertIn("json", quality_prompt.lower())
    
    def test_context_docs_formatting(self):
        """컨텍스트 문서 포맷팅 테스트"""
        context_docs = [
            {
                "text": "짧은 텍스트",
                "metadata": {"source_url": "https://test.com/1"}
            },
            {
                "text": "매우 긴 텍스트입니다. " * 100,  # 500자 이상
                "metadata": {"source_url": "https://test.com/2"}
            }
        ]
        
        formatted = self.builder._format_context_docs(context_docs)
        
        # 기본 검증
        self.assertIsInstance(formatted, str)
        self.assertGreater(len(formatted), 50)
        
        # 내용 검증
        self.assertIn("참고 자료 1", formatted)
        self.assertIn("참고 자료 2", formatted)
        self.assertIn("https://test.com/1", formatted)
        self.assertIn("https://test.com/2", formatted)
        self.assertIn("짧은 텍스트", formatted)
        self.assertIn("...", formatted)  # 긴 텍스트가 잘렸는지 확인


class TestPromptTemplates(unittest.TestCase):
    """PromptTemplates 테스트"""
    
    def test_chaequan_chusim_prompts(self):
        """채권추심 프롬프트 템플릿 테스트"""
        templates = PromptTemplates.get_chaequan_chusim_prompts()
        
        # 기본 검증
        self.assertIsInstance(templates, dict)
        self.assertIn("system", templates)
        self.assertIn("user_template", templates)
        
        # 내용 검증
        system_prompt = templates["system"]
        self.assertIn("법무법인 혜안", system_prompt)
        self.assertIn("채권추심", system_prompt)
        
        user_template = templates["user_template"]
        self.assertIn("{query}", user_template)
        self.assertIn("{context}", user_template)
    
    def test_common_phrases(self):
        """공통 문구 테스트"""
        phrases = PromptTemplates.get_common_phrases()
        
        # 기본 검증
        self.assertIsInstance(phrases, dict)
        self.assertIn("hooks", phrases)
        self.assertIn("transitions", phrases)
        self.assertIn("cta", phrases)
        self.assertIn("disclaimers", phrases)
        
        # 내용 검증
        self.assertIsInstance(phrases["hooks"], list)
        self.assertGreater(len(phrases["hooks"]), 0)
        self.assertIsInstance(phrases["transitions"], list)
        self.assertGreater(len(phrases["transitions"]), 0)
        self.assertIsInstance(phrases["cta"], list)
        self.assertGreater(len(phrases["cta"]), 0)
        self.assertIsInstance(phrases["disclaimers"], list)
        self.assertGreater(len(phrases["disclaimers"]), 0)
    
    def test_checklist_templates(self):
        """체크리스트 템플릿 테스트"""
        checklists = PromptTemplates.get_checklist_templates()
        
        # 기본 검증
        self.assertIsInstance(checklists, dict)
        self.assertIn("chaequan_chusim", checklists)
        self.assertIn("jigeumyeongryeong", checklists)
        
        # 내용 검증
        chaequan_checklist = checklists["chaequan_chusim"]
        self.assertIsInstance(chaequan_checklist, list)
        self.assertGreater(len(chaequan_checklist), 0)
        self.assertTrue(all("□" in item for item in chaequan_checklist))
        
        jigeumyeongryeong_checklist = checklists["jigeumyeongryeong"]
        self.assertIsInstance(jigeumyeongryeong_checklist, list)
        self.assertGreater(len(jigeumyeongryeong_checklist), 0)
        self.assertTrue(all("□" in item for item in jigeumyeongryeong_checklist))


class TestConvenienceFunctions(unittest.TestCase):
    """편의 함수 테스트"""
    
    def test_build_hyean_prompt(self):
        """혜안 톤 프롬프트 생성 함수 테스트"""
        query = "채권추심 절차"
        context_docs = [
            {
                "text": "테스트 컨텍스트",
                "metadata": {"source_url": "https://test.com"}
            }
        ]
        
        system_prompt, user_prompt = build_hyean_prompt(query, context_docs)
        
        # 기본 검증
        self.assertIsInstance(system_prompt, str)
        self.assertIsInstance(user_prompt, str)
        self.assertGreater(len(system_prompt), 100)
        self.assertGreater(len(user_prompt), 100)
        
        # 내용 검증
        self.assertIn("법무법인 혜안", system_prompt)
        self.assertIn(query, user_prompt)
    
    def test_get_quality_check_prompt(self):
        """품질 검증 프롬프트 생성 함수 테스트"""
        quality_prompt = get_quality_check_prompt()
        
        # 기본 검증
        self.assertIsInstance(quality_prompt, str)
        self.assertGreater(len(quality_prompt), 100)
        
        # 내용 검증
        self.assertIn("품질을 검증", quality_prompt)
        self.assertIn("json", quality_prompt.lower())
    
    def test_get_refinement_prompt(self):
        """개선 요청 프롬프트 생성 함수 테스트"""
        original_prompt = "원본 프롬프트"
        issues = ["문제점1", "문제점2"]
        
        refinement_prompt = get_refinement_prompt(original_prompt, issues)
        
        # 기본 검증
        self.assertIsInstance(refinement_prompt, str)
        self.assertGreater(len(refinement_prompt), 50)
        
        # 내용 검증
        self.assertIn("문제점1", refinement_prompt)
        self.assertIn("문제점2", refinement_prompt)
        self.assertIn(original_prompt, refinement_prompt)


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_full_prompt_generation_flow(self):
        """전체 프롬프트 생성 플로우 테스트"""
        # 1단계: 설정 생성
        config = PromptConfig(
            min_chars=1200,
            max_chars=1800,
            min_subheadings=3,
            require_checklist=True,
            require_disclaimer=True
        )
        
        # 2단계: 프롬프트 빌더 생성
        builder = HyeanPromptBuilder(config)
        
        # 3단계: 시스템 프롬프트 생성
        system_prompt = builder.build_system_prompt()
        self.assertIn("법무법인 혜안", system_prompt)
        
        # 4단계: 사용자 프롬프트 생성
        query = "채권추심 절차와 비용에 대해 설명해주세요"
        context_docs = [
            {
                "text": "채권추심 절차는 내용증명 발송부터 시작됩니다.",
                "metadata": {"source_url": "https://test.com/1"}
            },
            {
                "text": "지급명령 신청 비용은 채권액의 1/100입니다.",
                "metadata": {"source_url": "https://test.com/2"}
            }
        ]
        
        user_prompt = builder.build_user_prompt(query, context_docs)
        self.assertIn(query, user_prompt)
        self.assertIn("1,200자 이상 1,800자 이하", user_prompt)
        
        # 5단계: 품질 검증 프롬프트 생성
        quality_prompt = builder.get_quality_check_prompt()
        self.assertIn("1,200자 이상 1,800자 이하", quality_prompt)
        
        # 6단계: 개선 요청 프롬프트 생성
        issues = ["글 길이가 부족합니다"]
        refinement_prompt = builder.build_refinement_prompt(user_prompt, issues)
        self.assertIn("글 길이가 부족합니다", refinement_prompt)
        
        # 7단계: 편의 함수 테스트
        system_prompt2, user_prompt2 = build_hyean_prompt(query, context_docs, config)
        self.assertEqual(system_prompt, system_prompt2)
        self.assertEqual(user_prompt, user_prompt2)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
