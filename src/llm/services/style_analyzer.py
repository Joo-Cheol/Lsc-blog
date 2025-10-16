#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
원본 데이터의 스타일 분석 및 보존 시스템
"""
import re
from typing import Dict, List, Any
from collections import Counter

class StyleAnalyzer:
    def __init__(self):
        self.style_patterns = {}
    
    def analyze_style(self, texts: List[str]) -> Dict[str, Any]:
        """원본 텍스트들의 스타일 패턴 분석"""
        if not texts:
            return {}
        
        # 1) 문장 길이 패턴
        sentence_lengths = []
        for text in texts:
            sentences = re.split(r'[.!?]', text)
            sentence_lengths.extend([len(s.strip()) for s in sentences if s.strip()])
        
        # 2) 문단 구조 패턴
        paragraph_patterns = []
        for text in texts:
            paragraphs = text.split('\n\n')
            paragraph_patterns.extend([len(p.split('.')) for p in paragraphs if p.strip()])
        
        # 3) 종결형 패턴
        ending_patterns = Counter()
        for text in texts:
            endings = re.findall(r'([^.!?]*[.!?])', text)
            for ending in endings:
                if ending.strip():
                    if ending.strip().endswith('습니다'):
                        ending_patterns['습니다'] += 1
                    elif ending.strip().endswith('합니다'):
                        ending_patterns['합니다'] += 1
                    elif ending.strip().endswith('다'):
                        ending_patterns['다'] += 1
                    elif ending.strip().endswith('요'):
                        ending_patterns['요'] += 1
        
        # 4) 연결어 패턴
        connector_patterns = Counter()
        connectors = ['또한', '더불어', '그리고', '또', '그러나', '하지만', '따라서', '그러므로', '즉', '예를 들어']
        for text in texts:
            for connector in connectors:
                connector_patterns[connector] += text.count(connector)
        
        # 5) 전문용어 사용 빈도
        legal_terms = ['지급명령', '채권', '채무', '법원', '소송', '집행', '독촉', '변제', '이행']
        term_frequency = Counter()
        for text in texts:
            for term in legal_terms:
                term_frequency[term] += text.count(term)
        
        return {
            'sentence_length': {
                'avg': sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0,
                'min': min(sentence_lengths) if sentence_lengths else 0,
                'max': max(sentence_lengths) if sentence_lengths else 0
            },
            'paragraph_structure': {
                'avg_sentences_per_paragraph': sum(paragraph_patterns) / len(paragraph_patterns) if paragraph_patterns else 0,
                'typical_range': (min(paragraph_patterns), max(paragraph_patterns)) if paragraph_patterns else (0, 0)
            },
            'ending_style': dict(ending_patterns),
            'connector_usage': dict(connector_patterns),
            'legal_term_frequency': dict(term_frequency),
            'total_texts': len(texts)
        }
    
    def generate_style_guidance(self, style_data: Dict[str, Any]) -> str:
        """분석된 스타일 데이터를 바탕으로 생성 가이드 생성"""
        if not style_data:
            return "표준 법률 문서 스타일을 사용하세요."
        
        guidance = []
        
        # 문장 길이 가이드
        avg_length = style_data.get('sentence_length', {}).get('avg', 0)
        if avg_length > 0:
            guidance.append(f"- 문장 길이: 평균 {avg_length:.0f}자 수준 유지")
        
        # 문단 구조 가이드
        avg_sentences = style_data.get('paragraph_structure', {}).get('avg_sentences_per_paragraph', 0)
        if avg_sentences > 0:
            guidance.append(f"- 문단당 문장 수: 평균 {avg_sentences:.1f}개 수준")
        
        # 종결형 스타일
        endings = style_data.get('ending_style', {})
        if endings:
            dominant_ending = max(endings.items(), key=lambda x: x[1])
            guidance.append(f"- 종결형: '{dominant_ending[0]}' 스타일 우선 사용")
        
        # 연결어 사용 패턴
        connectors = style_data.get('connector_usage', {})
        if connectors:
            used_connectors = [k for k, v in connectors.items() if v > 0]
            if used_connectors:
                guidance.append(f"- 연결어: {', '.join(used_connectors)} 등 자연스럽게 활용")
        
        # 전문용어 사용
        terms = style_data.get('legal_term_frequency', {})
        if terms:
            frequent_terms = [k for k, v in terms.items() if v > 0]
            if frequent_terms:
                guidance.append(f"- 전문용어: {', '.join(frequent_terms)} 등 적절히 포함")
        
        return "\n".join(guidance) if guidance else "표준 법률 문서 스타일을 사용하세요."

def extract_style_from_sources(top_sources: List[Dict]) -> str:
    """검색된 소스들에서 스타일 패턴 추출"""
    if not top_sources:
        return "표준 법률 문서 스타일을 사용하세요."
    
    # 소스 텍스트들 수집 (실제로는 검색 결과에서 가져와야 함)
    # 여기서는 간단한 예시
    sample_texts = [
        "지급명령은 채권자가 채무자에게 일정한 금액의 지급을 명하는 법원의 결정입니다.",
        "독촉장 발송 후 2주 이내에 채무자가 이행하지 않으면 법적 절차를 진행할 수 있습니다.",
        "집행권원이 있어야만 법원에 강제집행 신청을 할 수 있습니다."
    ]
    
    analyzer = StyleAnalyzer()
    style_data = analyzer.analyze_style(sample_texts)
    return analyzer.generate_style_guidance(style_data)





