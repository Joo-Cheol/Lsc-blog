"""
콘텐츠 검증 모듈
- 품질 게이트 검증
- 스타일 검증
- 구조 검증
"""
import re
from typing import Dict, List, Any
from collections import Counter


class ContentValidator:
    """콘텐츠 검증기"""
    
    def __init__(self):
        self.validation_rules = {
            'min_length': 1600,
            'max_length': 1900,
            'min_sentences': 20,
            'max_sentences': 50,
            'min_paragraphs': 5,
            'max_paragraphs': 15,
            'min_subheadings': 3,
            'max_sentences_per_paragraph': 4,
            'forbidden_words': ['또한', '더불어', '무료상담', '즉시연락', '100%'],
            'required_elements': ['h1', 'h3', 'ul', 'ol'],
            'ngram8_threshold': 0.18
        }
    
    def validate(self, content: str, sources: List[Dict] = None) -> Dict[str, Any]:
        """
        콘텐츠 종합 검증
        
        Args:
            content: 검증할 콘텐츠
            sources: 원본 소스
            
        Returns:
            검증 결과
        """
        if not content:
            return {
                "passed": False,
                "errors": ["빈 콘텐츠"],
                "warnings": [],
                "score": 0.0
            }
        
        # HTML 태그 제거하여 순수 텍스트 추출
        text_content = self._extract_text_content(content)
        
        # 각종 검증 수행
        length_validation = self._validate_length(text_content)
        structure_validation = self._validate_structure(content)
        style_validation = self._validate_style(text_content)
        quality_validation = self._validate_quality(text_content)
        forbidden_validation = self._validate_forbidden_words(text_content)
        
        # 검증 결과 통합
        all_errors = []
        all_warnings = []
        
        all_errors.extend(length_validation.get('errors', []))
        all_errors.extend(structure_validation.get('errors', []))
        all_errors.extend(style_validation.get('errors', []))
        all_errors.extend(quality_validation.get('errors', []))
        all_errors.extend(forbidden_validation.get('errors', []))
        
        all_warnings.extend(length_validation.get('warnings', []))
        all_warnings.extend(structure_validation.get('warnings', []))
        all_warnings.extend(style_validation.get('warnings', []))
        all_warnings.extend(quality_validation.get('warnings', []))
        all_warnings.extend(forbidden_validation.get('warnings', []))
        
        # 종합 점수 계산
        total_score = self._calculate_total_score([
            length_validation, structure_validation, style_validation,
            quality_validation, forbidden_validation
        ])
        
        return {
            "passed": len(all_errors) == 0,
            "errors": all_errors,
            "warnings": all_warnings,
            "score": total_score,
            "details": {
                "length": length_validation,
                "structure": structure_validation,
                "style": style_validation,
                "quality": quality_validation,
                "forbidden": forbidden_validation
            }
        }
    
    def _extract_text_content(self, html_content: str) -> str:
        """HTML에서 순수 텍스트 추출"""
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # 특수문자 정리
        text = re.sub(r'[^\w\s가-힣.,!?]', ' ', text)
        
        # 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _validate_length(self, content: str) -> Dict[str, Any]:
        """길이 검증"""
        length = len(content)
        errors = []
        warnings = []
        
        if length < self.validation_rules['min_length']:
            errors.append(f"콘텐츠가 너무 짧습니다 ({length}자, 최소 {self.validation_rules['min_length']}자 필요)")
        elif length > self.validation_rules['max_length']:
            warnings.append(f"콘텐츠가 너무 깁니다 ({length}자, 최대 {self.validation_rules['max_length']}자 권장)")
        
        return {
            "length": length,
            "errors": errors,
            "warnings": warnings,
            "passed": len(errors) == 0
        }
    
    def _validate_structure(self, content: str) -> Dict[str, Any]:
        """구조 검증"""
        errors = []
        warnings = []
        
        # 헤딩 검증
        h1_count = len(re.findall(r'<h1[^>]*>', content))
        h3_count = len(re.findall(r'<h3[^>]*>', content))
        
        if h1_count == 0:
            errors.append("H1 제목이 없습니다")
        elif h1_count > 1:
            warnings.append("H1 제목이 여러 개입니다")
        
        if h3_count < self.validation_rules['min_subheadings']:
            errors.append(f"부제목이 부족합니다 ({h3_count}개, 최소 {self.validation_rules['min_subheadings']}개 필요)")
        
        # 리스트 검증
        ul_count = len(re.findall(r'<ul[^>]*>', content))
        ol_count = len(re.findall(r'<ol[^>]*>', content))
        
        if ul_count == 0 and ol_count == 0:
            warnings.append("리스트가 없습니다")
        
        # 문단 검증
        paragraphs = re.split(r'</p>|<br>', content)
        paragraph_count = len([p for p in paragraphs if p.strip()])
        
        if paragraph_count < self.validation_rules['min_paragraphs']:
            errors.append(f"문단이 부족합니다 ({paragraph_count}개, 최소 {self.validation_rules['min_paragraphs']}개 필요)")
        
        return {
            "h1_count": h1_count,
            "h3_count": h3_count,
            "ul_count": ul_count,
            "ol_count": ol_count,
            "paragraph_count": paragraph_count,
            "errors": errors,
            "warnings": warnings,
            "passed": len(errors) == 0
        }
    
    def _validate_style(self, content: str) -> Dict[str, Any]:
        """스타일 검증"""
        errors = []
        warnings = []
        
        # 문장 분석
        sentences = re.split(r'[.!?]\s*', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) < self.validation_rules['min_sentences']:
            errors.append(f"문장이 부족합니다 ({len(sentences)}개, 최소 {self.validation_rules['min_sentences']}개 필요)")
        elif len(sentences) > self.validation_rules['max_sentences']:
            warnings.append(f"문장이 너무 많습니다 ({len(sentences)}개, 최대 {self.validation_rules['max_sentences']}개 권장)")
        
        # 문장 길이 분석
        sentence_lengths = [len(s) for s in sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
        
        if avg_length < 20:
            warnings.append("문장이 너무 짧습니다")
        elif avg_length > 100:
            warnings.append("문장이 너무 깁니다")
        
        # 종결형 일관성 검증
        endings = []
        for sentence in sentences:
            for ending in ['합니다', '습니다', '입니다', '됩니다']:
                if sentence.endswith(ending):
                    endings.append(ending)
                    break
        
        if endings:
            ending_counts = Counter(endings)
            dominant_ending = ending_counts.most_common(1)[0][0]
            consistency = max(ending_counts.values()) / len(endings)
            
            if consistency < 0.8:
                warnings.append("문장 종결형이 일관되지 않습니다")
        
        return {
            "sentence_count": len(sentences),
            "avg_sentence_length": avg_length,
            "ending_consistency": consistency if endings else 0,
            "errors": errors,
            "warnings": warnings,
            "passed": len(errors) == 0
        }
    
    def _validate_quality(self, content: str) -> Dict[str, Any]:
        """품질 검증"""
        errors = []
        warnings = []
        
        # n-gram 중복 검사
        ngram8_similarity = self._calculate_ngram_similarity(content, 8)
        if ngram8_similarity > self.validation_rules['ngram8_threshold']:
            errors.append(f"내용 중복이 감지되었습니다 (유사도: {ngram8_similarity:.3f})")
        
        # 키워드 밀도 검증
        words = content.split()
        word_count = len(words)
        
        if word_count > 0:
            # 주요 키워드 빈도 계산
            word_counts = Counter(words)
            total_words = sum(word_counts.values())
            
            # 키워드 밀도가 너무 높으면 경고
            for word, count in word_counts.most_common(5):
                density = count / total_words
                if density > 0.05:  # 5% 이상
                    warnings.append(f"'{word}' 키워드 밀도가 높습니다 ({density:.1%})")
        
        return {
            "ngram8_similarity": ngram8_similarity,
            "word_count": word_count,
            "errors": errors,
            "warnings": warnings,
            "passed": len(errors) == 0
        }
    
    def _validate_forbidden_words(self, content: str) -> Dict[str, Any]:
        """금지어 검증"""
        errors = []
        warnings = []
        
        forbidden_words = self.validation_rules['forbidden_words']
        found_forbidden = []
        
        for word in forbidden_words:
            if word in content:
                found_forbidden.append(word)
        
        if found_forbidden:
            errors.append(f"금지어가 발견되었습니다: {', '.join(found_forbidden)}")
        
        return {
            "found_forbidden": found_forbidden,
            "errors": errors,
            "warnings": warnings,
            "passed": len(errors) == 0
        }
    
    def _calculate_ngram_similarity(self, content: str, n: int) -> float:
        """n-gram 유사도 계산"""
        words = content.split()
        if len(words) < n:
            return 0.0
        
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            ngrams.append(ngram)
        
        if not ngrams:
            return 0.0
        
        # n-gram 빈도 계산
        ngram_counts = Counter(ngrams)
        
        # 중복도 계산
        total_ngrams = len(ngrams)
        unique_ngrams = len(ngram_counts)
        
        if total_ngrams == 0:
            return 0.0
        
        # 중복도 = 1 - (고유 n-gram 수 / 전체 n-gram 수)
        duplication_ratio = 1 - (unique_ngrams / total_ngrams)
        
        return duplication_ratio
    
    def _calculate_total_score(self, validation_results: List[Dict[str, Any]]) -> float:
        """종합 점수 계산"""
        if not validation_results:
            return 0.0
        
        # 각 검증의 통과 여부로 점수 계산
        passed_count = sum(1 for result in validation_results if result.get('passed', False))
        total_count = len(validation_results)
        
        base_score = passed_count / total_count if total_count > 0 else 0.0
        
        # 경고 감점
        total_warnings = sum(len(result.get('warnings', [])) for result in validation_results)
        warning_penalty = min(0.2, total_warnings * 0.02)  # 최대 0.2 감점
        
        final_score = max(0.0, base_score - warning_penalty)
        
        return final_score