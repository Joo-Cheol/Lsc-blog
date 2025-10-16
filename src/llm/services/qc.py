import re
from typing import NamedTuple

class QCResult(NamedTuple):
    passed: bool
    reason: str
    length_ok: bool
    h2_ok: bool
    checklist_ok: bool
    formal_ok: bool
    forbidden_ok: bool
    numeric_ok: bool

def run_qc(text: str) -> QCResult:
    """품질 검사 실행"""
    
    # 1) 길이 검사 (1600~1900자) - 가이드와 일치
    content_length = len(text)
    length_ok = 1600 <= content_length <= 1900
    
    # 2) H2 소제목 검사 (최소 3개)
    h2_count = len(re.findall(r'^##\s+', text, re.MULTILINE))
    h2_ok = h2_count >= 3
    
    # 3) 체크리스트 검사 (5항) - 유연한 헤더 패턴
    m = re.search(r"##\s*(준비\s*서류|준비서류|체크리스트|준비\s*물|준비사항)([\s\S]+?)(?:\n##\s|$)", text, re.I)
    if m:
        checklist_count = len(re.findall(r"^\s*(?:[-*]|\d+\.)\s+", m.group(2), re.M))
    else:
        # 체크리스트 섹션이 없으면 전체에서 찾기
        checklist_patterns = [
            r'^\s*[-*]\s+',  # 마크다운 리스트
            r'^\s*\d+\.\s+',  # 번호 리스트
        ]
        checklist_count = 0
        for pattern in checklist_patterns:
            checklist_count += len(re.findall(pattern, text, re.MULTILINE))
    
    checklist_ok = checklist_count >= 5
    
    # 4) 종결형 검사 ('~습니다/합니다' 비율) - 격식형 확대
    sentences = re.findall(r'[^.!?]*[.!?]', text)
    formal_sentences = len(re.findall(r'[^.!?]*(?:습니다|합니다)[.!?]', text))
    formal_ratio = formal_sentences / len(sentences) if sentences else 0
    formal_ok = formal_ratio >= 0.8  # 80% 이상으로 격식형 강화
    
    # 5) 금칙어 검사 ('또한', '더불어' 사용 금지)
    forbidden_words = ['또한', '더불어']
    forbidden_count = sum(text.count(word) for word in forbidden_words)
    forbidden_ok = forbidden_count == 0
    
    # 6) 숫자/날짜 검증 (지급명령 2-6주 등 도메인 범위) - 문맥 제한
    numeric_ok = True
    # 키워드 주변 문맥에서만 검사 (과탐지 방지)
    context_keywords = ['지급명령', '독촉', '절차', '기간', '처리']
    
    for keyword in context_keywords:
        # 키워드 주변 ±50자 윈도우에서 숫자 검사
        for match in re.finditer(rf'.{{0,50}}{keyword}.{{0,50}}', text, re.IGNORECASE):
            window = match.group(0)
            # 주 단위 검사 (지급명령 관련)
            for num_match in re.findall(r'(\d+)\s*주', window):
                num = int(num_match)
                if not (2 <= num <= 6):
                    numeric_ok = False
                    break
            # 일 단위 검사 (처리 기간 관련)
            for num_match in re.findall(r'(\d+)\s*일', window):
                num = int(num_match)
                if not (1 <= num <= 30):
                    numeric_ok = False
                    break
            # 개월 단위 검사 (제한 기간 관련)
            for num_match in re.findall(r'(\d+)\s*개월', window):
                num = int(num_match)
                if not (1 <= num <= 12):
                    numeric_ok = False
                    break
            if not numeric_ok:
                break
        if not numeric_ok:
            break
    
    # 전체 통과 여부
    passed = length_ok and h2_ok and checklist_ok and formal_ok and forbidden_ok and numeric_ok
    
    # 실패 사유 수집
    reasons = []
    if not length_ok:
        reasons.append(f"길이 부적절 ({content_length}자, 목표: 1600~1900자)")
    if not h2_ok:
        reasons.append(f"H2 소제목 부족 ({h2_count}개, 최소 3개 필요)")
    if not checklist_ok:
        reasons.append(f"체크리스트 부족 ({checklist_count}항, 최소 5항 필요)")
    if not formal_ok:
        reasons.append(f"종결형 비율 낮음 ({formal_ratio:.1%}, 목표: 80% 이상)")
    if not forbidden_ok:
        reasons.append(f"금칙어 사용 ({forbidden_count}회, '또한/더불어' 금지)")
    if not numeric_ok:
        reasons.append("숫자/날짜 범위 벗어남 (지급명령 2-6주, 기타 도메인 범위)")
    
    reason = "; ".join(reasons) if reasons else "모든 기준 통과"
    
    return QCResult(
        passed=passed,
        reason=reason,
        length_ok=length_ok,
        h2_ok=h2_ok,
        checklist_ok=checklist_ok,
        formal_ok=formal_ok,
        forbidden_ok=forbidden_ok,
        numeric_ok=numeric_ok,
    )
