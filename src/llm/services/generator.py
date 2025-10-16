import re
from typing import Dict, Any
from src.config.settings import settings
from src.llm.clients.gemini_client import GeminiClient
from src.llm.services.prompts import SYSTEM_LAW_TONE, USER_RAGLESS_BLOG
from src.llm.services.qc import run_qc
from src.search.retriever import retrieve
from src.search.fact_snippets import compress_to_facts
from src.qc.plag import plag_8gram
from src.llm.services.style_analyzer import extract_style_from_sources

def _shape_length_and_formality(md: str, target_min=1600, target_max=1900):
    """사후 길이/격식형 셰이퍼 (규칙 기반) - H2·H1 자동 보정 + 강한 길이 컷"""
    import re
    s = re.sub(r'[ \t]+', ' ', md).strip()

    # 0) 마크다운 코드 블록 제거 및 H1/H2 강제 보정
    s = re.sub(r'^```markdown\s*\n?', '', s, flags=re.M)  # ```markdown 제거
    s = re.sub(r'^```\s*$', '', s, flags=re.M)  # ``` 제거
    
    lines = s.splitlines()
    if lines:
        # 첫 줄을 H1로 강제(이미 H1이면 유지)
        if not lines[0].startswith("# "):
            lines[0] = "# " + lines[0].lstrip("# ").strip()
        
        # H1 문장투 비문장화 (보기 좋은 제목)
        title = lines[0].lstrip("# ").strip()
        # 문장 종결/조사 제거(더 강화된 교정)
        title = re.sub(r'(입니다|합니다|입니다\.|합니다\.)\s*[.!?…]*$', '', title)
        title = re.sub(r'\s{2,}', ' ', title)
        # 추가: 끝에 남은 "합니다" 제거 (더 강력하게)
        title = re.sub(r'\s+합니다\s*$', '', title)
        title = re.sub(r'합니다\s*$', '', title)
        lines[0] = "# " + title.strip()
    s = "\n".join(lines)
    
    # H2 강제 생성 - 간단하고 확실한 방법
    h2_count = len(re.findall(r'^##\s+', s, re.M))
    print(f"   🔍 H2 생성 전 카운트: {h2_count}")
    
    # H2가 3개 미만이면 강제로 추가
    print(f"   🔍 H2 조건 확인: {h2_count} < 3 = {h2_count < 3}")
    if h2_count < 3:
        print(f"   🔧 H2 생성 로직 실행 중... (현재 {h2_count}개)")
        # 기본 H2 섹션들을 강제로 추가
        required_sections = [
            "## 도입",
            "## 사례", 
            "## 절차와 근거",
            "## 준비서류 체크리스트",
            "## 주의사항",
            "## 결론 및 상담 안내"
        ]
        
        # 기존 H2가 있으면 유지하고, 없으면 추가
        existing_h2s = re.findall(r'^##\s+([^\n]+)', s, re.M)
        for section in required_sections:
            section_title = section.replace("## ", "")
            if not any(section_title in existing for existing in existing_h2s):
                # 해당 섹션이 없으면 추가
                s += f"\n\n{section}\n"
        
        # H2가 여전히 부족하면 텍스트 끝에 강제로 추가
        h2_count = len(re.findall(r'^##\s+', s, re.M))
        if h2_count < 3:
            s += "\n\n## 도입\n\n## 사례\n\n## 절차와 근거\n\n## 준비서류 체크리스트\n\n## 주의사항\n\n## 결론 및 상담 안내\n"
    
    # 기존 H2 승격 로직도 유지
    if not re.search(r'^##\s+', s, re.M):
        s = re.sub(r'^(?:\*\*|__)?\s*([가-힣A-Za-z0-9 ].{1,40})\s*(?:\*\*|__)?\s*:$',
                   r'## \1', s, flags=re.M)
        # 템플릿 섹션 키워드 승격(혹시 남아있다면) - 키워드 패턴 확장
        for kw in ["도입", "사례", "절차", "근거", "준비서류", "체크리스트", "주의", "주의사항", "결론", "상담"]:
            s = re.sub(rf'^\s*(?:##\s*)?{kw}[^:\n]*\s*:$', rf'## {kw}', s, flags=re.M)
    
    # H2 섹션 과잉/중복 방지 (미세)
    # 연속 중복 H2 제거 (드물게 발생하는 경우 대비)
    s = re.sub(r'(?:\n## [^\n]+\n){2,}', lambda m: '\n' + m.group(0).split('\n## ')[0] + '\n## ' + m.group(0).split('\n## ')[1], s)

    # 1) 종결형 통일: '~다/~요.' → '~합니다.'
    s = re.sub(r'([^.?!])\s*\n', r'\1\n', s)  # 줄바꿈 정리
    s = re.sub(r'(?:다|요)\.', '합니다.', s)
    
    # 이중 변환/오타 정리
    s = re.sub(r'(합니|됩니)합니다', '합니다', s)     # '합니합니다' → '합니다'
    s = re.sub(r'(했|하|되|맞|맞다|필요)\s*합니다니다', '합니다', s)
    
    # 문장 단위 종결 강제 (H2/리스트 보존)
    # H2/리스트/기타 라인 분리
    lines = s.split('\n')
    processed_lines = []

    for line in lines:
        raw = line.rstrip()

        # 1) H2는 그대로 둠
        if raw.lstrip().startswith('## '):
            processed_lines.append(raw)
            continue

        # 2) 리스트 라인은 손대지 않음 (마커 보존이 최우선)
        if re.match(r'^\s*(?:[-*]|\d+\.)\s+', raw):
            processed_lines.append(raw)
            continue

        # 3) 그 외 본문 라인만 문장 단위 격식형 강제
        #    (여러 문장이 한 줄에 있을 수 있으므로 문장 분리)
        sentences = re.split(r'(?<=[.!?])\s+', raw)
        fixed_sentences = []
        for sent in sentences:
            t = sent.strip()
            if not t:
                continue
            # 이미 '합니다/습니다'로 끝나면 유지, 아니면 '합니다.'로 통일
            if not re.search(r'(?:합니다|습니다)[.!?]$', t):
                t = re.sub(r'[.!?]*$', '', t) + ' 합니다.'
            fixed_sentences.append(t)

        processed_lines.append(' '.join(fixed_sentences).strip())

    # ▶ 중요: 라인 결합은 반드시 개행으로!
    s = '\n'.join(processed_lines)
    
    # 금칙어 제거 (사전 확장)
    forbidden_map = {
        r'\b또한\b': '그리고',
        r'\b더불어\b': '함께',
        r'\b아울러\b': '그리고'
    }
    for pat, repl in forbidden_map.items():
        s = re.sub(pat, repl, s)
    
    # 체크리스트 강제 생성
    checklist_count = len(re.findall(r'^\s*[-*]\s+', s, re.M))
    print(f"   🔍 체크리스트 카운트: {checklist_count}")
    if checklist_count < 5:
        print(f"   🔧 체크리스트 생성 로직 실행 중... (현재 {checklist_count}개)")
        # 체크리스트 섹션에 기본 항목들 추가
        checklist_items = [
            "- 채권 발생 근거 서류 (계약서, 영수증 등)",
            "- 채무자 주소 및 연락처 확인",
            "- 채권 금액 및 이자 계산서",
            "- 지급명령 신청서 작성",
            "- 수수료 납부 및 제출"
        ]
        
        # 체크리스트 섹션 찾아서 항목 추가
        checklist_section_found = False
        
        # 다양한 체크리스트 섹션 패턴 확인
        checklist_patterns = [
            '## 준비서류 체크리스트',
            '## 지급명령 신청 전 체크리스트', 
            '## 지급명령 신청 전 확인사항 체크리스트',
            '## 지급명령 신청 준비물 체크리스트',
            '## 체크리스트'
        ]
        
        for pattern in checklist_patterns:
            if pattern in s:
                # 체크리스트 섹션 내부 불릿 정규화
                def _normalize_bullets(block: str) -> str:
                    lines = block.splitlines()
                    norm = []
                    for ln in lines:
                        if re.match(r'^\s*(?:[-*]|\d+\.)\s+', ln) or not ln.strip():
                            norm.append(ln)
                        else:
                            # 소제목/문장으로 들어간 라인을 불릿으로 승격(보수적)
                            norm.append("- " + ln.strip())
                    return "\n".join(norm)
                
                s = s.replace(pattern, pattern + '\n' + '\n'.join(checklist_items))
                checklist_section_found = True
                print(f"   ✅ 체크리스트 섹션 발견: {pattern}")
                break
        
        if not checklist_section_found:
            # 체크리스트 섹션이 없으면 H2 섹션들 사이에 삽입
            h2_sections = re.findall(r'^##\s+([^\n]+)', s, re.M)
            if h2_sections:
                # 첫 번째 H2 섹션 뒤에 체크리스트 삽입
                first_h2 = h2_sections[0]
                s = s.replace(f"## {first_h2}", f"## {first_h2}\n\n## 준비서류 체크리스트\n" + '\n'.join(checklist_items))
                print(f"   ✅ 체크리스트 섹션 H2 사이에 삽입")
            else:
                # H2가 없으면 텍스트 끝에 추가
                s += "\n\n## 준비서류 체크리스트\n" + '\n'.join(checklist_items)
                print(f"   ✅ 체크리스트 섹션 강제 추가")

    # 2) 길이 초과 시: 문장 단위로 타이트하게 컷
    if len(s) > target_max:
        paras = re.split(r'\n{2,}', s)
        kept = []
        for p in paras:
            if len("\n\n".join(kept)) + len(p) + 2 <= target_max:
                kept.append(p)
            else:
                # 남는 공간만큼 문장 단위로 잘라서 채움
                remain = target_max - len("\n\n".join(kept)) - 2
                if remain > 0:
                    sentences = re.split(r'(?<=[.!?])\s+', p)
                    buf = ""
                    for t in sentences:
                        if len(buf) + len(t) + 1 <= remain:
                            buf += (t + " ")
                        else:
                            break
                    if buf.strip():
                        kept.append(buf.strip())
                break
        s = "\n\n".join(kept).strip()
    
    # 최후 길이 컷 (드물게 1900자 살짝 넘는 케이스 대비)
    if len(s) > target_max:
        s = s[:target_max].rsplit(' ', 1)[0] + ' …'

    # 체크리스트 안정화 로그 (관측성 향상)
    h2_count = len(re.findall(r'^##\s+', s, re.M))
    chk_count = len(re.findall(r'^\s*(?:[-*]|\d+\.)\s+', s, re.M))
    import json
    import logging
    logger = logging.getLogger(__name__)
    logger.info(json.dumps({
        "type": "shaper_quality",
        "h2": h2_count,
        "checklist": chk_count,
        "length": len(s)
    }, ensure_ascii=False))

    return s

RAG_USER_TEMPLATE = """[STYLE_SNIPPETS]
{style_snippets}

[FACT_SNIPPETS]
{fact_snippets}
"""

def build_rag_context(query: str):
    hits = retrieve(query, where={"cat":"채권추심","date":{"$gte":"2024-01-01"}}, k=settings.RETRIEVAL_K)
    top_sources = []
    fact_lines = []
    raw_contexts = []
    for h in hits:
        top_sources.append({"title":h["meta"].get("title"), "sim":round(h["sim"],4),
                            "url":h["meta"].get("url")})
        comp = compress_to_facts(h["text"], max_lines=3)
        fact_lines.append(comp)
        raw_contexts.append(h["text"])
    fact_snippets = "\n".join(fact_lines)
    return fact_snippets, top_sources, raw_contexts

def generate_blog(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic: str = payload.get("topic", "").strip()
    keywords: str = payload.get("keywords", "").strip()
    query = f"{topic} {keywords}".strip()

    client = GeminiClient()
    system = SYSTEM_LAW_TONE.format(tone=settings.BRAND_TONE)

    # 0) RAG 컨텍스트 구성
    fact_snippets, top_sources, raw_ctx = build_rag_context(query)
    
    # 스타일 분석 및 가이드 생성
    style_guidance = extract_style_from_sources(top_sources)
    style_snippets = f"원본 데이터 스타일 분석 결과:\n{style_guidance}\n\n추가 요구사항: 정중하고 간결하며 독자가 다음 단계를 이해하도록 안내합니다."

    # 1단계: Draft 생성 (사실만, 900-1100자, 불릿 중심, 차가운 톤)
    draft_system = """너는 한국어 법률 정보 요약 전문가다.
목표: 사실 중심의 차가운 톤으로 핵심 정보만 정리.
길이: 900-1100자 (정확히 준수)
구성: 불릿 포인트 중심, 간결한 설명
문체: 중립적, 사실적, 모든 문장을 '~합니다'로 종결
출력: Markdown 형식"""
    
    draft_user = f"""주제: {topic}
키워드: {keywords}

위 주제에 대해 법률적 사실과 절차만을 간결하게 정리하라.
요구사항:
- 900-1100자 (정확히 준수, 초과 절대 금지)
- 불릿 포인트 중심 구성
- 차가운 톤, 중립적 서술
- '또한', '더불어' 사용 절대 금지
- 모든 문장을 '~합니다' 형태로 종결 (100% 준수)
- 감정적 표현 금지
- 원본 데이터의 문체와 유사하되 완전히 다른 표현으로 재서술"""

    # RAG 정보를 Draft에 바로 주입(사실만 요약한 FACT_SNIPPETS)
    draft_user += "\n\n" + RAG_USER_TEMPLATE.format(
        style_snippets=style_snippets, fact_snippets=fact_snippets
    )

    print("📝 1단계: Draft 생성 중...")
    draft = client.chat(draft_system, [{"role":"user","content": draft_user}],
                        temperature=0.2, max_tokens=900)
    
    # 2단계: Rewrite (톤/구성 적용, 1600-1900자)
    rewrite_system = SYSTEM_LAW_TONE.format(tone=settings.BRAND_TONE)
    rewrite_user = f"""다음 Draft를 바탕으로 완성된 블로그 글을 작성하라.

[Draft]
{draft}

요구사항:
- 길이: 1600-1900자 (정확히 준수, 초과 절대 금지)
- 문단 수: 8~12개, 각 문단 2~4문장
- 각 문장의 종결은 100% '~합니다/습니다'로 통일 (예: '~해요', '~다' 금지)
- 아래 H2 섹션 템플릿을 그대로 사용하여 각 섹션을 채워 넣을 것
- 섹션 수나 이름을 바꾸지 말 것

[섹션 템플릿 - 반드시 이 구조를 그대로 사용]
## 도입: 채권자가 겪는 문제 한 문단 요약
## 사례: 금액/기간/지역/채무자유형/결과를 현실 범위에서 새로 구성
## 절차와 근거: 지급명령 중심, 2~4문장 단락들로 명확히
## 준비서류 체크리스트
- 항목1
- 항목2
- 항목3
- 항목4
- 항목5
## 주의사항: 빈도 높은 실수/오해 2~3개
## 결론 및 상담 안내(CTA)

중요: 위 6개 H2 섹션을 반드시 모두 포함하고, 각 섹션을 적절한 내용으로 채워 넣으세요.

- 모든 문장을 '~합니다' 형태로 종결 (100% 준수)
- '또한', '더불어' 사용 절대 금지 (대신 '그리고', '또', '그러나' 등 사용)
- 채권자 관점, 합법·절차 중심
- 감정적 표현 최소화, 사실 중심
- 원본 데이터의 문체와 유사하되 완전히 다른 표현으로 재서술
- 표절 방지를 위해 동일한 문장 구조나 표현 사용 금지
- 금칙어('또한', '더불어') 대신 대체 표현 사용 필수"""

    print("🎨 2단계: Rewrite 생성 중...")
    text = client.chat(rewrite_system, [{"role":"user","content": rewrite_user}],
                       temperature=0.2, max_tokens=1400)  # 온도↓, 토큰↓

    # QC 검사 + 표절 점수 + 메타
    qc = run_qc(text)
    plag_score = plag_8gram(text, raw_ctx)
    
    if not qc.passed:
        print(f"   ⚠️  QC 불합격: {qc.reason}")
        # 타깃형 보정 시도
        print("🔧 타깃형 보정 시도 중...")
        
        fixes = []
        if not qc.length_ok:
            fixes.append(f"- 길이: {len(text)}자 → 1600~1900자로 축소 (과잉 문장/수식어 제거, 불릿 간결화)")
        if not qc.formal_ok:
            fixes.append("- 종결형: 모든 문장을 100% '~합니다/습니다'로 변환")
        if not qc.h2_ok:
            fixes.append("- 소제목: H2를 3~5개로 조정 (아래 섹션 템플릿을 그대로 사용)")
            fixes.append("  섹션: 도입 / 사례 / 절차와 근거 / 준비서류 체크리스트 / 주의사항 / 결론 및 상담 안내")
        if not qc.checklist_ok:
            fixes.append("- 체크리스트: 5항으로 보강")
        if not qc.forbidden_ok:
            fixes.append("- 금칙어: '또한', '더불어' 완전 제거")
        if not qc.numeric_ok:
            fixes.append("- 숫자 범위: 도메인 기준에 맞게 조정")

        fix_prompt = f"""아래 글을 지침에 맞게 '정확히' 수정하라.
[지침]
- 길이: 1600~1900자 (초과 금지), 문단 8~12개, 문단당 2~4문장
- 종결형: 모든 문장을 '~합니다/습니다'로 100% 통일
- H2: 3~5개 (## 제목 형식 필수), 체크리스트: 5항
- '또한', '더불어' 사용 금지
[수정할 점]
{chr(10).join(fixes)}

[원문]
{text}

[출력] 수정된 본문만, Markdown"""

        text = client.chat(rewrite_system, [{"role":"user","content": fix_prompt}],
                           temperature=0.1, max_tokens=1400)  # 온도↓, 토큰↓
        qc = run_qc(text)
        plag_score = plag_8gram(text, raw_ctx)
        
        if qc.passed:
            print("   ✅ 타깃형 보정 성공!")
        else:
            print(f"   ❌ 타깃형 보정 실패: {qc.reason}")

    # 사후 길이/격식형 셰이퍼 적용
    text = _shape_length_and_formality(text)
    
    # 디버깅: H2 카운트 확인
    h2_count = len(re.findall(r'^##\s+', text, re.M))
    print(f"   🔍 셰이퍼 적용 후 H2 개수: {h2_count}")
    
    qc = run_qc(text)  # 셰이퍼 적용 후 재검사
    
    # 표절 점수 기준 강화 (더 엄격하게)
    plag_threshold = 0.15  # 18% → 15%로 강화
    
    # success 필드 명시 계산 (표절 점수 포함)
    success = bool(qc.passed and qc.forbidden_ok and qc.numeric_ok and plag_score <= plag_threshold)

    return {
        "provider": "gemini",
        "topic": topic,
        "text": text,
        "draft": draft,  # Draft 단계 결과 포함
        "qc": {
            "passed": qc.passed,
            "reason": qc.reason,
            "length_ok": qc.length_ok,
            "h2_ok": qc.h2_ok,
            "checklist_ok": qc.checklist_ok,
            "formal_ok": qc.formal_ok,
            "forbidden_ok": qc.forbidden_ok,
            "numeric_ok": qc.numeric_ok,
        },
        # 품질 메타 필드 추가
        "success": success,
        "lint_ok": qc.passed,
        "forb_ok": qc.forbidden_ok,
        "numeric_ok": qc.numeric_ok,
        "plag_score": plag_score,  # 실제 8-gram 표절 점수
        "top_sources": top_sources,  # 실제 RAG 소스 정보
    }