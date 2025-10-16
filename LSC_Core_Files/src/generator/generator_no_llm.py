"""
A 파이프라인: LLM 없는 네이버 블로그 생성기
- e5 임베딩 + MMR + 스타일 프로파일 + 표절 가드
- 슬롯 기반 템플릿 자동 채움
- 네이버 친화 HTML 출력
"""
import time
import re
import hashlib
from typing import Dict, Any, List, Optional
import numpy as np

from .templates import NAVER_TEMPLATES
from .selector import MMRSelector
from .style_profile import StyleProfileManager
from .plagiarism_guard import PlagiarismGuard
from .renderer import NaverHTMLRenderer
from .validators import ContentValidator
from .textutils import extract_keywords, clean_text, mask_pii


class NoLLMGenerator:
    """A 파이프라인: LLM 없는 블로그 생성기"""
    
    def __init__(self):
        self.config = {
            # 길이 설정
            "min_length": 1600,
            "max_length": 1900,
            
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
            "cooperation_levels": ["협조적", "거부적"]
        }
        
        # 컴포넌트 초기화
        self.selector = MMRSelector()
        self.style_manager = StyleProfileManager()
        self.plagiarism_guard = PlagiarismGuard()
        self.renderer = NaverHTMLRenderer()
        self.validator = ContentValidator()
    
    def generate(self, topic: str, results: List[Dict], model, 
                category: str = "채권추심", hashtags: int = 10) -> Dict[str, Any]:
        """
        A 파이프라인 메인 생성 함수
        
        Args:
            topic: 주제
            results: 검색 결과 리스트
            model: e5 모델
            category: 카테고리
            hashtags: 해시태그 개수
            
        Returns:
            생성 결과
        """
        start_time = time.time()
        
        try:
            print(f"🚀 A 파이프라인 시작: {topic}")
            
            # 1) 검색 결과 필터링 및 MMR 중복 제거
            filtered_results = self._filter_and_deduplicate(results, top_k=8)
            
            # 2) 스타일 프로파일 분석
            style_profile = self.style_manager.analyze_style(filtered_results)
            
            # 3) MMR로 핵심 문장 선택
            selected_sentences = self.selector.select_sentences(
                filtered_results, 
                topic, 
                top_k=15
            )
            
            # 4) 슬롯 기반 템플릿 채움
            slots = self._fill_template_slots(topic, selected_sentences, style_profile)
            
            # 5) 네이버 HTML 생성
            html_content = self.renderer.render_naver_html(topic, slots)
            
            # 6) 품질 검증
            validation_result = self.validator.validate(html_content, filtered_results)
            
            # 7) 표절 검사
            plagiarism_result = self.plagiarism_guard.check_plagiarism(
                html_content, filtered_results
            )
            
            # 8) PII 마스킹
            html_content = mask_pii(html_content)
            
            # 9) 금지어 필터링
            html_content = self._filter_forbidden_words(html_content)
            
            # 10) 최종 검증
            if not validation_result["passed"]:
                print("⚠️ 품질 검증 실패, 자동 수정 시도...")
                html_content = self._auto_fix(html_content, validation_result)
            
            generation_time = time.time() - start_time
            
            return {
                "html": html_content,
                "title": self._extract_title(html_content),
                "stats": {
                    "generation_time": generation_time,
                    "mode": "e5-only",
                    "style_score": style_profile.get("score", 0.0),
                    "plagiarism_score": plagiarism_result.get("score", 0.0),
                    "validation": validation_result,
                    "plagiarism": plagiarism_result,
                    "sources": self._format_sources(filtered_results[:5])
                }
            }
            
        except Exception as e:
            print(f"❌ A 파이프라인 오류: {e}")
            return {
                "html": self._fallback_content(topic),
                "title": f"{topic}에 대한 법적 검토",
                "stats": {
                    "error": str(e),
                    "mode": "fallback"
                }
            }
    
    def _filter_and_deduplicate(self, results: List[Dict], top_k: int = 8) -> List[Dict]:
        """검색 결과 필터링 및 중복 제거"""
        if not results:
            return []
        
        # 유사도 점수 기준 정렬
        sorted_results = sorted(results, key=lambda x: x.get("similarity", 0), reverse=True)
        
        # 상위 K개 선택
        filtered = sorted_results[:top_k]
        
        # 중복 제거 (제목 기준)
        seen_titles = set()
        deduplicated = []
        
        for result in filtered:
            title = result.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                deduplicated.append(result)
        
        return deduplicated
    
    def _fill_template_slots(self, topic: str, sentences: List[str], 
                           style_profile: Dict) -> Dict[str, str]:
        """슬롯 기반 템플릿 채움"""
        slots = {}
        
        # 핵심 키워드 추출
        keywords = extract_keywords(topic)
        core_keyword = keywords[0] if keywords else topic
        
        # Hook 슬롯
        slots["hook"] = NAVER_TEMPLATES["hook"].format(
            topic=topic,
            핵심키워드=core_keyword
        )
        
        # 사례 슬롯
        slots["cases"] = self._generate_cases(sentences)
        
        # 절차 슬롯
        slots["procedure"] = self._generate_procedure(sentences)
        
        # 체크리스트 슬롯
        slots["checklist"] = self._generate_checklist(sentences)
        
        # 주의사항 슬롯
        slots["cautions"] = self._generate_cautions(sentences)
        
        # CTA 슬롯
        slots["cta"] = NAVER_TEMPLATES["cta"]
        
        # 소스 슬롯
        slots["sources"] = self._generate_sources(sentences)
        
        # 해시태그 슬롯
        slots["hashtags"] = self._generate_hashtags(topic, keywords)
        
        return slots
    
    def _generate_cases(self, sentences: List[str]) -> str:
        """실제 사례 생성"""
        case_template = """
        <div class="case-example">
        <h4>📋 실제 사례</h4>
        <p><strong>금액:</strong> {amount}만원</p>
        <p><strong>기간:</strong> {period}주</p>
        <p><strong>지역:</strong> {region}</p>
        <p><strong>채무자 유형:</strong> {debtor_type}</p>
        <p><strong>결과:</strong> {result}</p>
        </div>
        """
        
        # 랜덤 사례 생성
        import random
        amount = random.randint(150, 620)
        period = random.randint(2, 8)
        region = random.choice(self.config["regions"])
        debtor_type = random.choice(self.config["debtor_types"])
        cooperation = random.choice(self.config["cooperation_levels"])
        
        if cooperation == "협조적":
            result = "성공적으로 해결"
        else:
            result = "법적 절차 진행 중"
        
        return case_template.format(
            amount=amount,
            period=period,
            region=region,
            debtor_type=debtor_type,
            result=result
        )
    
    def _generate_procedure(self, sentences: List[str]) -> str:
        """절차 생성"""
        procedure_steps = [
            "1. 사전 조사 및 자료 수집",
            "2. 독촉장 발송",
            "3. 지급명령 신청",
            "4. 강제집행 신청",
            "5. 후속 관리"
        ]
        
        procedure_html = "<ol>\n"
        for step in procedure_steps:
            procedure_html += f"<li>{step}</li>\n"
        procedure_html += "</ol>"
        
        return procedure_html
    
    def _generate_checklist(self, sentences: List[str]) -> str:
        """체크리스트 생성"""
        checklist_items = [
            "채권 증명서류 준비",
            "채무자 주소 확인",
            "소멸시효 확인",
            "법정이자 계산",
            "소송비용 예산"
        ]
        
        checklist_html = "<ul>\n"
        for item in checklist_items:
            checklist_html += f"<li>✅ {item}</li>\n"
        checklist_html += "</ul>"
        
        return checklist_html
    
    def _generate_cautions(self, sentences: List[str]) -> str:
        """주의사항 생성"""
        cautions = [
            "소멸시효를 반드시 확인하세요",
            "채무자의 소재를 정확히 파악하세요",
            "법정이자와 지연손해금을 구분하세요"
        ]
        
        cautions_html = "<ul>\n"
        for caution in cautions:
            cautions_html += f"<li>⚠️ {caution}</li>\n"
        cautions_html += "</ul>"
        
        return cautions_html
    
    def _generate_sources(self, sentences: List[str]) -> str:
        """참고 자료 생성"""
        sources = [
            "민법 제390조 (채권의 목적)",
            "민사소송법 제462조 (지급명령)",
            "민사집행법 제1조 (강제집행)"
        ]
        
        sources_html = "<ul>\n"
        for source in sources:
            sources_html += f"<li>📚 {source}</li>\n"
        sources_html += "</ul>"
        
        return sources_html
    
    def _generate_hashtags(self, topic: str, keywords: List[str]) -> str:
        """해시태그 생성"""
        base_tags = ["#채권추심", "#법무법인", "#법률상담"]
        topic_tags = [f"#{keyword}" for keyword in keywords[:3]]
        
        all_tags = base_tags + topic_tags
        return " ".join(all_tags)
    
    def _filter_forbidden_words(self, content: str) -> str:
        """금지어 필터링"""
        forbidden_words = NAVER_TEMPLATES["forbidden_words"]
        
        for word in forbidden_words:
            # 금지어를 대체 표현으로 변경
            if word == "무료상담":
                content = content.replace(word, "전문상담")
            elif word == "즉시연락":
                content = content.replace(word, "빠른연락")
            elif word == "100%":
                content = content.replace(word, "확실한")
            else:
                content = content.replace(word, "***")
        
        return content
    
    def _auto_fix(self, content: str, validation_result: Dict) -> str:
        """자동 수정"""
        # 기본적인 수정 로직
        if validation_result.get("min_subheadings", 0) < 3:
            content += "\n\n## 추가 정보\n- 법적 검토\n- 절차 준수\n\n## 결론"
        
        return content
    
    def _extract_title(self, content: str) -> str:
        """제목 추출"""
        # HTML에서 h1 태그 찾기
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
        if h1_match:
            return clean_text(h1_match.group(1))
        
        # Markdown에서 # 제목 찾기
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return clean_text(line[2:])
        
        return "법적 검토"
    
    def _format_sources(self, results: List[Dict]) -> List[Dict]:
        """소스 포맷팅"""
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "score": r.get("similarity", 0.0)
            }
            for r in results[:5]
        ]
    
    def _fallback_content(self, topic: str) -> str:
        """폴백 콘텐츠"""
        return f"""
        <h1>{topic}에 대한 법적 검토</h1>
        
        <div class="hook">
        💡 {topic}에서 가장 중요한 것은 <strong>체계적인 접근</strong>입니다.
        </div>
        
        <h3>📋 실제 사례</h3>
        <div class="case-example">
        <p><strong>금액:</strong> 300만원</p>
        <p><strong>기간:</strong> 4주</p>
        <p><strong>지역:</strong> 서울</p>
        <p><strong>결과:</strong> 성공적으로 해결</p>
        </div>
        
        <h3>⚖️ 핵심 절차</h3>
        <ol>
        <li>사전 조사 및 자료 수집</li>
        <li>독촉장 발송</li>
        <li>지급명령 신청</li>
        <li>강제집행 신청</li>
        <li>후속 관리</li>
        </ol>
        
        <h3>✅ 체크리스트</h3>
        <ul>
        <li>✅ 채권 증명서류 준비</li>
        <li>✅ 채무자 주소 확인</li>
        <li>✅ 소멸시효 확인</li>
        <li>✅ 법정이자 계산</li>
        <li>✅ 소송비용 예산</li>
        </ul>
        
        <h3>⚠️ 주의사항</h3>
        <ul>
        <li>⚠️ 소멸시효를 반드시 확인하세요</li>
        <li>⚠️ 채무자의 소재를 정확히 파악하세요</li>
        <li>⚠️ 법정이자와 지연손해금을 구분하세요</li>
        </ul>
        
        <div class="cta">
        사건 번호·금액·기한만 알려주시면 <strong>10분 내</strong> 전략을 제시합니다.
        </div>
        
        <h3>📚 참고 자료</h3>
        <ul>
        <li>📚 민법 제390조 (채권의 목적)</li>
        <li>📚 민사소송법 제462조 (지급명령)</li>
        <li>📚 민사집행법 제1조 (강제집행)</li>
        </ul>
        
        <div class="hashtags">
        #채권추심 #법무법인 #법률상담
        </div>
        """


def generate_no_llm(topic: str, results: List[Dict], model, 
                   category: str = "채권추심", hashtags: int = 10) -> Dict[str, Any]:
    """
    A 파이프라인 진입점
    
    Args:
        topic: 주제
        results: 검색 결과 리스트
        model: e5 모델
        category: 카테고리
        hashtags: 해시태그 개수
        
    Returns:
        생성 결과
    """
    generator = NoLLMGenerator()
    return generator.generate(topic, results, model, category, hashtags)
