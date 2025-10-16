"""
스타일 프로파일 관리자
- 원본 문서 스타일 분석
- 스타일 가이드 생성
- 일관성 유지
"""
import re
from typing import Dict, List, Any
from collections import Counter


class StyleProfileManager:
    """스타일 프로파일 관리자"""
    
    def __init__(self):
        self.style_patterns = {
            'sentence_endings': ['합니다', '습니다', '입니다', '됩니다', '됩니다'],
            'connectors': ['그리고', '또한', '더불어', '그러나', '하지만', '그런데'],
            'emphasis_words': ['중요한', '핵심적인', '필수적인', '꼭', '반드시'],
            'legal_terms': ['법률', '법령', '조항', '절차', '근거', '권리', '의무']
        }
    
    def analyze_style(self, results: List[Dict]) -> Dict[str, Any]:
        """
        검색 결과에서 스타일 분석
        
        Args:
            results: 검색 결과 리스트
            
        Returns:
            스타일 프로파일
        """
        if not results:
            return self._get_default_style()
        
        # 모든 텍스트 수집
        all_text = ' '.join([r.get('content', '') for r in results])
        
        # 문장 분석
        sentences = self._extract_sentences(all_text)
        
        # 스타일 특성 분석
        style_analysis = {
            'sentence_length': self._analyze_sentence_length(sentences),
            'sentence_endings': self._analyze_sentence_endings(sentences),
            'connectors': self._analyze_connectors(sentences),
            'legal_terms': self._analyze_legal_terms(sentences),
            'paragraph_structure': self._analyze_paragraph_structure(sentences),
            'tone': self._analyze_tone(sentences)
        }
        
        # 스타일 점수 계산
        style_score = self._calculate_style_score(style_analysis)
        
        return {
            'analysis': style_analysis,
            'score': style_score,
            'recommendations': self._generate_recommendations(style_analysis)
        }
    
    def _extract_sentences(self, text: str) -> List[str]:
        """텍스트에서 문장 추출"""
        # 문장 분리
        sentences = re.split(r'[.!?]\s*', text)
        
        # 빈 문장 제거 및 정리
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        return sentences
    
    def _analyze_sentence_length(self, sentences: List[str]) -> Dict[str, Any]:
        """문장 길이 분석"""
        if not sentences:
            return {'avg_length': 0, 'distribution': []}
        
        lengths = [len(s) for s in sentences]
        
        return {
            'avg_length': sum(lengths) / len(lengths),
            'min_length': min(lengths),
            'max_length': max(lengths),
            'distribution': self._get_length_distribution(lengths)
        }
    
    def _analyze_sentence_endings(self, sentences: List[str]) -> Dict[str, Any]:
        """문장 종결형 분석"""
        endings = []
        for sentence in sentences:
            # 문장 끝에서 종결형 추출
            for ending in self.style_patterns['sentence_endings']:
                if sentence.endswith(ending):
                    endings.append(ending)
                    break
        
        ending_counts = Counter(endings)
        total_endings = sum(ending_counts.values())
        
        return {
            'distribution': dict(ending_counts),
            'dominant_ending': ending_counts.most_common(1)[0][0] if ending_counts else '합니다',
            'consistency': max(ending_counts.values()) / total_endings if total_endings > 0 else 0
        }
    
    def _analyze_connectors(self, sentences: List[str]) -> Dict[str, Any]:
        """연결어 분석"""
        connector_counts = Counter()
        
        for sentence in sentences:
            for connector in self.style_patterns['connectors']:
                if connector in sentence:
                    connector_counts[connector] += 1
        
        return {
            'usage': dict(connector_counts),
            'most_used': connector_counts.most_common(1)[0][0] if connector_counts else '그리고'
        }
    
    def _analyze_legal_terms(self, sentences: List[str]) -> Dict[str, Any]:
        """법률 용어 분석"""
        legal_term_counts = Counter()
        
        for sentence in sentences:
            for term in self.style_patterns['legal_terms']:
                if term in sentence:
                    legal_term_counts[term] += 1
        
        return {
            'usage': dict(legal_term_counts),
            'density': sum(legal_term_counts.values()) / len(sentences) if sentences else 0
        }
    
    def _analyze_paragraph_structure(self, sentences: List[str]) -> Dict[str, Any]:
        """문단 구조 분석"""
        # 문단당 문장 수 추정 (빈 줄 기준)
        paragraphs = []
        current_paragraph = []
        
        for sentence in sentences:
            if sentence.strip():
                current_paragraph.append(sentence)
            else:
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                    current_paragraph = []
        
        if current_paragraph:
            paragraphs.append(current_paragraph)
        
        paragraph_lengths = [len(p) for p in paragraphs]
        
        return {
            'avg_sentences_per_paragraph': sum(paragraph_lengths) / len(paragraphs) if paragraphs else 0,
            'paragraph_count': len(paragraphs),
            'structure_consistency': self._calculate_structure_consistency(paragraph_lengths)
        }
    
    def _analyze_tone(self, sentences: List[str]) -> Dict[str, Any]:
        """톤 분석"""
        formal_indicators = ['합니다', '습니다', '입니다', '됩니다']
        informal_indicators = ['해요', '예요', '돼요', '어요']
        
        formal_count = sum(1 for s in sentences for indicator in formal_indicators if indicator in s)
        informal_count = sum(1 for s in sentences for indicator in informal_indicators if indicator in s)
        
        total_indicators = formal_count + informal_count
        
        return {
            'formality_score': formal_count / total_indicators if total_indicators > 0 else 0.5,
            'tone': 'formal' if formal_count > informal_count else 'informal'
        }
    
    def _calculate_style_score(self, analysis: Dict[str, Any]) -> float:
        """스타일 점수 계산 (0-1)"""
        score = 0.0
        
        # 문장 길이 일관성 (20%)
        length_consistency = 1 - abs(analysis['sentence_length']['avg_length'] - 50) / 50
        score += 0.2 * max(0, length_consistency)
        
        # 종결형 일관성 (30%)
        ending_consistency = analysis['sentence_endings']['consistency']
        score += 0.3 * ending_consistency
        
        # 법률 용어 밀도 (25%)
        legal_density = min(analysis['legal_terms']['density'] / 0.1, 1.0)  # 0.1을 이상적 밀도로 가정
        score += 0.25 * legal_density
        
        # 톤 일관성 (25%)
        tone_consistency = analysis['tone']['formality_score']
        score += 0.25 * tone_consistency
        
        return min(1.0, score)
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """스타일 개선 권장사항 생성"""
        recommendations = []
        
        # 문장 길이 권장
        avg_length = analysis['sentence_length']['avg_length']
        if avg_length < 30:
            recommendations.append("문장을 더 길게 작성하여 정보를 풍부하게 하세요")
        elif avg_length > 80:
            recommendations.append("문장을 더 짧게 나누어 가독성을 높이세요")
        
        # 종결형 일관성 권장
        if analysis['sentence_endings']['consistency'] < 0.8:
            recommendations.append("문장 종결형을 일관되게 사용하세요 (예: ~합니다)")
        
        # 법률 용어 밀도 권장
        if analysis['legal_terms']['density'] < 0.05:
            recommendations.append("법률 용어를 더 많이 사용하여 전문성을 높이세요")
        
        # 톤 권장
        if analysis['tone']['formality_score'] < 0.7:
            recommendations.append("더 격식있는 톤을 사용하세요")
        
        return recommendations
    
    def _get_length_distribution(self, lengths: List[int]) -> Dict[str, int]:
        """길이 분포 계산"""
        distribution = {
            'short': len([l for l in lengths if l < 30]),
            'medium': len([l for l in lengths if 30 <= l < 60]),
            'long': len([l for l in lengths if l >= 60])
        }
        return distribution
    
    def _calculate_structure_consistency(self, paragraph_lengths: List[int]) -> float:
        """문단 구조 일관성 계산"""
        if not paragraph_lengths:
            return 0.0
        
        avg_length = sum(paragraph_lengths) / len(paragraph_lengths)
        variance = sum((length - avg_length) ** 2 for length in paragraph_lengths) / len(paragraph_lengths)
        
        # 분산이 작을수록 일관성 높음
        consistency = 1 / (1 + variance)
        return min(1.0, consistency)
    
    def _get_default_style(self) -> Dict[str, Any]:
        """기본 스타일 프로파일"""
        return {
            'analysis': {
                'sentence_length': {'avg_length': 50, 'distribution': {'medium': 1}},
                'sentence_endings': {'dominant_ending': '합니다', 'consistency': 1.0},
                'connectors': {'most_used': '그리고'},
                'legal_terms': {'density': 0.1},
                'paragraph_structure': {'avg_sentences_per_paragraph': 3},
                'tone': {'formality_score': 0.8, 'tone': 'formal'}
            },
            'score': 0.8,
            'recommendations': []
        }