"""
텍스트 유틸리티 함수들
- PII 마스킹
- 금지어 필터링
- 텍스트 정리
- 키워드 추출
"""
import re
from typing import List, Dict, Any


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """텍스트에서 키워드 추출"""
    # 불용어 제거
    stopwords = {
        '은', '는', '이', '가', '을', '를', '에', '의', '와', '과', '도', '만', '부터', '까지',
        '에서', '에게', '한테', '께', '로', '으로', '와', '과', '도', '만', '부터', '까지',
        '그', '이', '저', '그것', '이것', '저것', '그런', '이런', '저런', '그렇게', '이렇게', '저렇게'
    }
    
    # 단어 추출 (2글자 이상)
    words = re.findall(r'[가-힣]{2,}', text)
    
    # 불용어 제거 및 빈도 계산
    word_freq = {}
    for word in words:
        if word not in stopwords and len(word) >= 2:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # 빈도순 정렬
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    return [word for word, freq in sorted_words[:max_keywords]]


def clean_text(text: str) -> str:
    """텍스트 정리"""
    if not text:
        return ""
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # 특수문자 정리
    text = re.sub(r'[^\w\s가-힣.,!?]', '', text)
    
    # 연속 공백 제거
    text = re.sub(r'\s+', ' ', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text


def mask_pii(text: str) -> str:
    """개인정보 마스킹"""
    if not text:
        return text
    
    # 전화번호 마스킹 (010-1234-5678, 02-123-4567 등)
    text = re.sub(r'(\d{2,3})-(\d{3,4})-(\d{4})', r'\1-****-\3', text)
    text = re.sub(r'(\d{3})-(\d{4})-(\d{4})', r'\1-****-\3', text)
    
    # 이메일 마스킹 (user@domain.com -> u***@domain.com)
    text = re.sub(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 
                  lambda m: m.group(1)[0] + '***@' + m.group(2), text)
    
    # 주민등록번호 마스킹 (123456-1234567 -> 123456-****567)
    text = re.sub(r'(\d{6})-(\d{7})', r'\1-****\2[-3:]', text)
    
    # 신용카드 번호 마스킹 (1234-5678-9012-3456 -> 1234-****-****-3456)
    text = re.sub(r'(\d{4})-(\d{4})-(\d{4})-(\d{4})', r'\1-****-****-\4', text)
    
    # 계좌번호 마스킹 (123-456-789012 -> 123-456-****12)
    text = re.sub(r'(\d{3})-(\d{3})-(\d{6})', r'\1-\2-****\3[-2:]', text)
    
    return text


def filter_forbidden_words(text: str, forbidden_words: List[str] = None) -> str:
    """금지어 필터링"""
    if not text or not forbidden_words:
        return text
    
    # 기본 금지어 목록
    default_forbidden = [
        "무료상담", "즉시연락", "24시간", "100%", "확실한", "최고의",
        "전문가", "특별할인", "지금바로", "한정특가", "무료견적",
        "또한", "더불어", "그리고", "그러나", "하지만", "그런데"
    ]
    
    if forbidden_words is None:
        forbidden_words = default_forbidden
    
    # 금지어 대체
    replacements = {
        "무료상담": "전문상담",
        "즉시연락": "빠른연락", 
        "24시간": "상시",
        "100%": "확실한",
        "확실한": "신뢰할 수 있는",
        "최고의": "우수한",
        "전문가": "전문가",
        "특별할인": "특별혜택",
        "지금바로": "바로",
        "한정특가": "특별가격",
        "무료견적": "견적상담",
        "또한": "그리고",
        "더불어": "함께",
        "그리고": "그리고",
        "그러나": "하지만",
        "하지만": "하지만",
        "그런데": "그런데"
    }
    
    for forbidden in forbidden_words:
        if forbidden in text:
            replacement = replacements.get(forbidden, "***")
            text = text.replace(forbidden, replacement)
    
    return text


def normalize_sentences(text: str) -> str:
    """문장 정규화"""
    if not text:
        return text
    
    # 문장 분리
    sentences = re.split(r'[.!?]\s*', text)
    
    normalized_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # 문장 끝 정규화
        if not sentence.endswith(('.', '!', '?')):
            sentence += '.'
        
        # 문장 시작 대문자
        if sentence and sentence[0].islower():
            sentence = sentence[0].upper() + sentence[1:]
        
        normalized_sentences.append(sentence)
    
    return ' '.join(normalized_sentences)


def extract_entities(text: str) -> Dict[str, List[str]]:
    """개체명 추출"""
    entities = {
        'amounts': [],
        'dates': [],
        'locations': [],
        'organizations': []
    }
    
    # 금액 추출 (1,000만원, 500만원 등)
    amounts = re.findall(r'(\d{1,3}(?:,\d{3})*)\s*만원', text)
    entities['amounts'] = amounts
    
    # 날짜 추출 (2024년 1월, 2024.01.01 등)
    dates = re.findall(r'(\d{4}년\s*\d{1,2}월|\d{4}\.\d{1,2}\.\d{1,2})', text)
    entities['dates'] = dates
    
    # 지역 추출 (서울, 경기, 부산 등)
    locations = re.findall(r'(서울|경기|인천|부산|대구|광주|대전|울산|강원|충북|충남|전북|전남|경북|경남|제주)', text)
    entities['locations'] = list(set(locations))
    
    # 기관명 추출 (법원, 검찰청, 경찰서 등)
    organizations = re.findall(r'(법원|검찰청|경찰서|법무법인|로펌)', text)
    entities['organizations'] = list(set(organizations))
    
    return entities


def validate_content_quality(text: str) -> Dict[str, Any]:
    """콘텐츠 품질 검증"""
    if not text:
        return {"passed": False, "errors": ["빈 텍스트"]}
    
    errors = []
    warnings = []
    
    # 길이 검증
    if len(text) < 500:
        errors.append("텍스트가 너무 짧습니다 (500자 미만)")
    elif len(text) > 5000:
        warnings.append("텍스트가 너무 깁니다 (5000자 초과)")
    
    # 문장 수 검증
    sentences = re.split(r'[.!?]', text)
    sentence_count = len([s for s in sentences if s.strip()])
    
    if sentence_count < 5:
        errors.append("문장 수가 부족합니다 (5개 미만)")
    elif sentence_count > 50:
        warnings.append("문장 수가 너무 많습니다 (50개 초과)")
    
    # 문단 수 검증
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) < 3:
        errors.append("문단 수가 부족합니다 (3개 미만)")
    
    # 금지어 검증
    forbidden_words = ["무료상담", "즉시연락", "100%", "또한", "더불어"]
    found_forbidden = [word for word in forbidden_words if word in text]
    if found_forbidden:
        errors.append(f"금지어 발견: {', '.join(found_forbidden)}")
    
    # PII 검증
    pii_patterns = [
        r'\d{2,3}-\d{3,4}-\d{4}',  # 전화번호
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # 이메일
        r'\d{6}-\d{7}',  # 주민등록번호
    ]
    
    found_pii = []
    for pattern in pii_patterns:
        if re.search(pattern, text):
            found_pii.append("개인정보")
    
    if found_pii:
        errors.append(f"개인정보 발견: {', '.join(found_pii)}")
    
    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "length": len(text),
            "sentence_count": sentence_count,
            "paragraph_count": len(paragraphs)
        }
    }


def format_phone_number(phone: str) -> str:
    """전화번호 포맷팅"""
    # 숫자만 추출
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    else:
        return phone


def format_amount(amount: str) -> str:
    """금액 포맷팅"""
    # 숫자만 추출
    digits = re.sub(r'\D', '', amount)
    
    if digits:
        # 만원 단위로 변환
        amount_num = int(digits)
        if amount_num >= 10000:
            return f"{amount_num // 10000}만원"
        else:
            return f"{amount_num}원"
    
    return amount