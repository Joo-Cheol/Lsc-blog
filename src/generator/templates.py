"""
네이버 블로그용 템플릿
"""

NAVER_TEMPLATES = {
    "title": "{topic}, {기간} 안에 끝내는 핵심 절차 | 실무형 가이드",
    "cta": "사건 번호·금액·기한만 알려주시면 **10분 내** 전략을 제시합니다.",
    
    # 슬롯 템플릿
    "hook": "💡 {topic}에서 가장 중요한 것은 **{핵심키워드}**입니다.",
    "case_intro": "📋 실제 사례를 통해 확인해보겠습니다.",
    "procedure_intro": "⚖️ {topic} 절차는 다음과 같습니다.",
    "checklist_intro": "✅ 체크리스트로 놓치지 마세요.",
    "caution_intro": "⚠️ 주의사항을 반드시 확인하세요.",
    
    # HTML 템플릿
    "html_template": """
<h1>{title}</h1>

<div class="hook">
{hook}
</div>

<h3>📋 실제 사례</h3>
{cases}

<h3>⚖️ 핵심 절차</h3>
{procedure}

<h3>✅ 체크리스트</h3>
{checklist}

<h3>⚠️ 주의사항</h3>
{cautions}

<div class="cta">
{cta}
</div>

<h3>📚 참고 자료</h3>
{sources}

<div class="hashtags">
{hashtags}
</div>
""",
    
    # 금지어 목록
    "forbidden_words": [
        "무료상담", "즉시연락", "24시간", "100%", "확실한", "최고의",
        "전문가", "특별할인", "지금바로", "한정특가", "무료견적"
    ]
}
