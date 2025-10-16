import re

def sanitize(s: str) -> str:
    """프롬프트 인젝션 방지를 위한 텍스트 정화"""
    s = re.sub(r'https?://\S+', '', s)  # URL 제거
    s = re.sub(r'(?:지시|명령|프롬프트).*', '', s)  # 의심 패턴 컷
    s = re.sub(r'[<>{}[\]()]', '', s)  # 특수 문자 제거
    return s.strip()

def compress_to_facts(text: str, max_lines=4) -> str:
    """
    숫자/기간/절차 키워드가 있는 문장을 우선 추출해 3~4줄로 압축.
    """
    sents = re.split(r'(?<=[.!?])\s+', text)
    key = [s for s in sents if re.search(r'(기간|주|일|개월|서류|절차|신청|법원|채권|지급명령)', s)]
    out = (key or sents)[:max_lines]
    # 정화 후 반환
    sanitized = [sanitize(x) for x in out if x.strip()]
    return "- " + "\n- ".join([re.sub(r'\s+', ' ', x).strip() for x in sanitized if x.strip()])
