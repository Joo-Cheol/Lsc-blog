"""
가이드 기반 2단계 생성 파이프라인
- Draft (사실 초안) → Rewrite (스타일 적용)
- 품질 게이트 통합
- 가이드 프롬프트 코어 적용
"""
import time
import json
import re
import hashlib
from typing import Dict, Any, List, Optional
from collections import Counter
import numpy as np

class GuideBasedGenerator:
    """가이드 기반 2단계 생성 파이프라인"""
    
    def __init__(self):
        self.config = {
            # 길이 설정
            "draft_min_length": 900,
            "draft_max_length": 1100,
            "rewrite_min_length": 1600,
            "rewrite_max_length": 1900,
            
            # 품질 게이트 임계값
            "ngram8_threshold": 0.18,
            "min_subheadings": 3,
            "min_checklists": 1,
            "max_sentences_per_paragraph": 4,
            "forbidden_words": ["또한", "더불어", "무료상담", "즉시연락", "100%"],
            
            # 사례 다양성 범위
            "amount_range": (1500000, 6200000),  # 150만원 ~ 620만원
            "period_range": (2, 8),  # 2주 ~ 8주
            "regions": ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산"],
            "debtor_types": ["개인", "법인", "프리랜서", "소상공인"],
            "reactions": ["분할상환", "연락회피", "주소불명", "협조적", "거부적"]
        }
    
    def generate_post(self, topic: str, search_results: List[Dict], 
                     category: str = "채권추심") -> Dict[str, Any]:
        """
        2단계 생성 파이프라인
        
        Args:
            topic: 주제
            search_results: 검색 결과
            category: 카테고리
            
        Returns:
            생성 결과
        """
        start_time = time.time()
        
        try:
            # 1) 검색 결과 필터링 및 MMR 중복 제거
            filtered_results = self._filter_and_deduplicate(search_results, top_k=8)
            
            # 2) 컨텍스트 요약 (불릿 포인트)
            fact_snippets = self._extract_fact_snippets(filtered_results)
            style_snippets = self._extract_style_snippets(filtered_results)
            
            # 3) 1단계: Draft 생성 (사실 초안)
            print("📝 1단계: Draft 생성 중...")
            draft = self._generate_draft(topic, fact_snippets)
            
            # 4) 2단계: Rewrite 생성 (스타일 적용)
            print("✨ 2단계: Rewrite 생성 중...")
            body_markdown = self._generate_rewrite(draft, topic, style_snippets, fact_snippets)
            
            # 5) 품질 게이트 검증
            print("🔍 품질 검증 중...")
            validation_result = self._validate_content(body_markdown, filtered_results)
            
            # 6) 표절 검증
            plagiarism_result = self._check_plagiarism(body_markdown, filtered_results)
            
            # 7) 실패 시 자동 수정
            if not validation_result["ok"] or not plagiarism_result["ok"]:
                print("⚠️ 품질 검증 실패 - 자동 수정 시도...")
                body_markdown = self._auto_fix(body_markdown, validation_result, plagiarism_result)
                
                # 재검증
                validation_result = self._validate_content(body_markdown, filtered_results)
                plagiarism_result = self._check_plagiarism(body_markdown, filtered_results)
            
            # 8) 제목 추출
            title = self._extract_title(body_markdown)
            
            # 9) 통계 계산
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "title": title,
                "body_markdown": body_markdown,
                "sources": self._format_sources(filtered_results),
                "stats": {
                    "latency_ms": latency_ms,
                    "lint_ok": validation_result["ok"],
                    "style_score": validation_result.get("style_score", 0.0),
                    "plag": {
                        "ok": plagiarism_result["ok"],
                        "ngram8": plagiarism_result.get("ngram8_overlap", 0.0),
                        "cosine_max": plagiarism_result.get("cosine_max", 0.0),
                        "simhash_dist": plagiarism_result.get("simhash_dist", 0)
                    }
                }
            }
            
        except Exception as e:
            print(f"❌ 생성 파이프라인 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "title": f"{topic} 관련 법적 검토",
                "body_markdown": self._fallback_content(topic),
                "sources": [],
                "stats": {
                    "latency_ms": int((time.time() - start_time) * 1000),
                    "lint_ok": False,
                    "style_score": 0.0,
                    "plag": {"ok": False, "ngram8": 0.0, "cosine_max": 0.0, "simhash_dist": 0}
                }
            }
    
    def _filter_and_deduplicate(self, results: List[Dict], top_k: int) -> List[Dict]:
        """검색 결과 필터링 및 MMR 중복 제거"""
        # 점수 필터링 (0.78 이상)
        filtered = [r for r in results if r.get("similarity", 0) >= 0.78]
        
        # MMR 중복 제거 (간단한 구현)
        deduplicated = []
        seen_titles = set()
        
        for result in filtered:
            title = result.get("title", "")
            if title not in seen_titles and len(deduplicated) < top_k:
                deduplicated.append(result)
                seen_titles.add(title)
        
        return deduplicated
    
    def _extract_fact_snippets(self, results: List[Dict]) -> str:
        """사실 스니펫 추출 (절차·서류·기간·주의 요지)"""
        facts = []
        for result in results[:5]:  # 상위 5개만
            content = result.get("content", "")
            # 핵심 사실만 추출 (간단한 구현)
            sentences = content.split(".")
            for sentence in sentences[:3]:  # 각 문서에서 3문장만
                if len(sentence.strip()) > 20:
                    facts.append(f"• {sentence.strip()}")
        
        return "\n".join(facts[:15])  # 최대 15개
    
    def _extract_style_snippets(self, results: List[Dict]) -> str:
        """스타일 스니펫 추출 (톤 힌트 1-3문장)"""
        styles = []
        for result in results[:3]:  # 상위 3개만
            content = result.get("content", "")
            # 네이버 블로그 톤의 문장 추출
            sentences = content.split(".")
            for sentence in sentences:
                if any(word in sentence for word in ["합니다", "됩니다", "입니다"]) and len(sentence.strip()) > 15:
                    styles.append(sentence.strip())
                    break
        
        return "\n".join(styles[:3])  # 최대 3개
    
    def _generate_draft(self, topic: str, fact_snippets: str) -> str:
        """1단계: 사실 초안 생성 (900-1100자)"""
        # 가이드 프롬프트 코어 적용
        prompt = f"""
[역할] 법무법인 블로그 에디터(한국어). 채권자 관점.

[사실 사용 규칙]
아래 컨텍스트의 사실(정의/절차/서류/기간/주의)만 근거로 하되, 문장·표현은 전부 새로 작성.
사례의 금액/날짜/지역/분할횟수는 현실 범위에서 새로 구성.

[구조/길이]
도입 → 문제 인식 → 법적 근거/절차 → 실무 조언 → 결론.
본문 900-1100자, 불릿/숫자 중심.

[FACT_SNIPPETS] (절차·서류·기간·주의 요지)
{fact_snippets}

[출력] 사실 초안만 출력.
"""
        
        # 간단한 템플릿 기반 생성 (실제로는 LLM 호출)
        draft = f"""
{topic}에 대한 법적 검토

{topic} 과정에서 발생하는 주요 문제점들을 체계적으로 분석해보겠습니다.

법적 근거와 절차를 명확히 이해하는 것이 중요합니다.

실무에서 주의해야 할 사항들을 정리했습니다.

전문가 상담을 통해 체계적으로 접근하시기 바랍니다.
"""
        
        return draft.strip()
    
    def _generate_rewrite(self, draft: str, topic: str, style_snippets: str, fact_snippets: str) -> str:
        """2단계: 스타일 적용 및 리라이팅 (1600-1900자)"""
        # 가이드 프롬프트 코어 적용
        prompt = f"""
[역할] 법무법인 블로그 에디터(한국어). 채권자 관점.

[스타일]
- 네이버 블로그 톤(정중·친절). 문장/문단 짧게(문단 2–4문장).
- 소제목/번호/불릿 적극 사용, 이모지 0~1개/섹션.
- 금지: '또한', '더불어', 과장/협박/불법추심 조장.

[사실 사용 규칙(중요)]
- 아래 컨텍스트의 사실(정의/절차/서류/기간/주의)만 근거로 하되,
  문장·표현은 전부 새로 작성하세요. 원문과 8-gram 동일 구절 금지.
- 사례의 금액/날짜/지역/분할횟수는 현실 범위에서 "새로" 구성.

[구조/길이]
- 도입 → 문제 인식 → 법적 근거/절차 → 실무 조언(체크리스트) → 결론/CTA.
- 본문 1,600–1,900자, Markdown. 각 섹션 소제목 필수.

[STYLE_SNIPPETS]  # 톤 힌트 1–3문장 (내용 복붙 금지)
{style_snippets}

[FACT_SNIPPETS]   # 절차·서류·기간·주의 요지(재서술)
{fact_snippets}

[출력] 최종 본문만 출력.
"""
        
        # 간단한 템플릿 기반 생성 (실제로는 LLM 호출)
        rewrite = f"""# {topic}에 대한 종합 가이드

## 도입

{topic}과 관련된 법적 문제를 체계적으로 검토해보겠습니다. 많은 분들이 이 과정에서 어려움을 겪고 있어, 명확한 가이드가 필요합니다.

## 문제 인식

{topic} 과정에서 발생하는 주요 문제점들은 다음과 같습니다:

- 법적 절차의 복잡성
- 필요한 서류의 다양성  
- 시간과 비용의 부담
- 전문 지식의 부족

## 법적 근거

{topic}은 관련 법령에 따라 체계적으로 진행되어야 합니다. 적절한 법적 근거를 바탕으로 한 접근이 중요합니다.

## 실무 절차

### 1단계: 사전 준비
- 관련 서류 수집
- 법적 검토
- 전략 수립

### 2단계: 법적 조치
- 적절한 절차 진행
- 법적 요구사항 충족
- 문서화

### 3단계: 후속 관리
- 진행 상황 모니터링
- 필요시 추가 조치
- 결과 정리

## 주의사항

{topic} 과정에서 주의해야 할 주요 사항들:

- 법적 절차의 엄격한 준수
- 시간 제한의 고려
- 비용 효율성
- 전문가 상담의 중요성

## 결론

{topic}은 신중하고 체계적인 접근이 필요한 법적 절차입니다. 전문가와의 상담을 통해 올바른 방향으로 진행하시기 바랍니다.

**상담 문의: 02-1234-5678**

---

*본 내용은 일반적인 가이드이며, 구체적인 사안에 대해서는 전문가와 상담하시기 바랍니다.*
"""
        
        return rewrite.strip()
    
    def _validate_content(self, content: str, sources: List[Dict]) -> Dict[str, Any]:
        """콘텐츠 품질 검증"""
        results = {
            "ok": True,
            "errors": [],
            "warnings": [],
            "style_score": 0.0
        }
        
        # 1) 길이 검증
        if len(content) < self.config["rewrite_min_length"] or len(content) > self.config["rewrite_max_length"]:
            results["errors"].append(f"길이 부적절: {len(content)}자 (목표: {self.config['rewrite_min_length']}-{self.config['rewrite_max_length']}자)")
            results["ok"] = False
        
        # 2) 소제목 개수 확인
        subheading_count = len(re.findall(r'^##\s+', content, re.MULTILINE))
        if subheading_count < self.config["min_subheadings"]:
            results["errors"].append(f"소제목 부족: {subheading_count}개 (최소 {self.config['min_subheadings']}개 필요)")
            results["ok"] = False
        
        # 3) 체크리스트 개수 확인
        checklist_count = len(re.findall(r'^\s*[-*]\s+', content, re.MULTILINE))
        if checklist_count < self.config["min_checklists"]:
            results["errors"].append(f"체크리스트 부족: {checklist_count}개 (최소 {self.config['min_checklists']}개 필요)")
            results["ok"] = False
        
        # 4) 문단별 문장 수 확인
        paragraphs = content.split('\n\n')
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip() and not paragraph.startswith('#'):
                sentences = len(re.findall(r'[.!?]', paragraph))
                if sentences > self.config["max_sentences_per_paragraph"]:
                    results["errors"].append(f"문단 {i+1}이 너무 깁니다: {sentences}문장 (최대 {self.config['max_sentences_per_paragraph']}문장)")
                    results["ok"] = False
        
        # 5) 금칙어 검증
        for word in self.config["forbidden_words"]:
            if word in content:
                results["errors"].append(f"금칙어 발견: '{word}'")
                results["ok"] = False
        
        # 6) 스타일 점수 계산
        style_score = self._calculate_style_score(content)
        results["style_score"] = style_score
        
        return results
    
    def _check_plagiarism(self, content: str, sources: List[Dict]) -> Dict[str, Any]:
        """표절 검증 (8-gram 중복 검사)"""
        result = {
            "ok": True,
            "ngram8_overlap": 0.0,
            "cosine_max": 0.0,
            "simhash_dist": 0,
            "warnings": []
        }
        
        # 8-gram 중복 검사
        content_ngrams = self._get_ngrams(content, 8)
        max_overlap = 0.0
        
        for source in sources:
            source_content = source.get("content", "")
            source_ngrams = self._get_ngrams(source_content, 8)
            
            if source_ngrams:
                overlap = len(content_ngrams & source_ngrams) / len(content_ngrams)
                max_overlap = max(max_overlap, overlap)
        
        result["ngram8_overlap"] = max_overlap
        
        if max_overlap > self.config["ngram8_threshold"]:
            result["ok"] = False
            result["warnings"].append(f"8-gram 중복율 초과: {max_overlap:.3f} (임계값: {self.config['ngram8_threshold']})")
        
        return result
    
    def _get_ngrams(self, text: str, n: int) -> set:
        """n-gram 추출"""
        words = re.findall(r'\w+', text.lower())
        return set(' '.join(words[i:i+n]) for i in range(len(words)-n+1))
    
    def _calculate_style_score(self, content: str) -> float:
        """스타일 점수 계산"""
        score = 0.0
        
        # 문단 길이 점수
        paragraphs = content.split('\n\n')
        avg_paragraph_length = sum(len(p.split('.')) for p in paragraphs if p.strip()) / len(paragraphs)
        if 2 <= avg_paragraph_length <= 4:
            score += 0.3
        
        # 소제목 점수
        subheading_count = len(re.findall(r'^##\s+', content, re.MULTILINE))
        if subheading_count >= 3:
            score += 0.3
        
        # 체크리스트 점수
        checklist_count = len(re.findall(r'^\s*[-*]\s+', content, re.MULTILINE))
        if checklist_count >= 1:
            score += 0.2
        
        # 금칙어 점수
        has_forbidden = any(word in content for word in self.config["forbidden_words"])
        if not has_forbidden:
            score += 0.2
        
        return score
    
    def _auto_fix(self, content: str, validation_result: Dict, plagiarism_result: Dict) -> str:
        """자동 수정 시도"""
        fixed = content
        
        # 길이 보정
        if len(fixed) < self.config["rewrite_min_length"]:
            fixed += "\n\n## 추가 정보\n\n더 자세한 상담이 필요하시면 전문가와 상담하시기 바랍니다."
        
        # 소제목 보정
        if fixed.count("##") < self.config["min_subheadings"]:
            fixed = fixed.replace("## 결론", "## 실무 조언\n\n전문가 상담을 권합니다.\n\n## 결론")
        
        # 체크리스트 보정
        if len(re.findall(r'^\s*[-*]\s+', fixed, re.MULTILINE)) < self.config["min_checklists"]:
            fixed = fixed.replace("## 결론", "## 체크리스트\n\n- 전문가 상담\n- 법적 검토\n- 절차 준수\n\n## 결론")
        
        return fixed
    
    def _extract_title(self, content: str) -> str:
        """제목 추출"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "법적 검토"
    
    def _format_sources(self, results: List[Dict]) -> List[Dict]:
        """소스 포맷팅"""
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "score": r.get("similarity", 0.0)
            }
            for r in results[:5]  # 상위 5개만
        ]
    
    def _fallback_content(self, topic: str) -> str:
        """폴백 콘텐츠"""
        return f"""
# {topic}에 대한 법적 검토

## 도입
{topic}과 관련된 법적 문제를 체계적으로 검토해보겠습니다.

## 문제 인식
많은 분들이 {topic} 과정에서 어려움을 겪고 있습니다.

## 법적 근거
관련 법령을 바탕으로 적절한 절차를 진행해야 합니다.

## 실무 절차
1. 사전 준비
2. 법적 조치
3. 후속 관리

## 결론
전문가와 상담하여 체계적으로 접근하시기 바랍니다.

**상담 문의: 02-1234-5678**
"""

def generate_guide_based_post(topic: str, search_results: List[Dict], 
                             category: str = "채권추심") -> Dict[str, Any]:
    """
    가이드 기반 파이프라인 진입점
    
    Args:
        topic: 주제
        search_results: 검색 결과
        category: 카테고리
        
    Returns:
        생성 결과
    """
    generator = GuideBasedGenerator()
    return generator.generate_post(topic, search_results, category)





