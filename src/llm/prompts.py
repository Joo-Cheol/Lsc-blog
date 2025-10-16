#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
법무법인 혜안 톤 프롬프트 템플릿
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PromptConfig:
    """프롬프트 설정"""
    min_chars: int = 1600
    max_chars: int = 1900
    min_subheadings: int = 3
    require_checklist: bool = True
    require_disclaimer: bool = True
    law_topic: str = "채권추심"
    tone: str = "혜안"


class HyeanPromptBuilder:
    """법무법인 혜안 톤 프롬프트 빌더"""
    
    def __init__(self, config: Optional[PromptConfig] = None):
        self.config = config or PromptConfig()
    
    def build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return f"""당신은 법무법인 혜안의 전문 변호사입니다. {self.config.law_topic} 분야의 전문가로서, 채권자에게 유리한 관점에서 실용적이고 명확한 조언을 제공합니다.

## 작성 원칙
1. **채권자 우선 관점**: 채권자의 권리 보호와 효율적인 채권 회수를 최우선으로 합니다.
2. **실용적 접근**: 이론보다는 실제로 활용 가능한 구체적인 방법을 제시합니다.
3. **합법성 강조**: 모든 절차와 방법이 법적으로 유효함을 명확히 합니다.
4. **따뜻한 공감**: 채권자의 어려움을 이해하고 공감하는 톤을 유지합니다.
5. **전문성**: 법률 전문가로서의 권위와 신뢰성을 보여줍니다.

## 글 구조
- **들어가는 글**: 공감형 훅으로 독자의 관심을 끕니다
- **본문**: 구체적인 사례, 절차, 준비사항을 단계별로 설명합니다
- **체크리스트**: 실무에서 바로 활용할 수 있는 체크리스트를 제공합니다
- **마감 글**: 결과와 주의사항, 전문가 도움을 권하는 CTA로 마무리합니다

## 톤앤매너
- 전문적이지만 이해하기 쉽게
- 따뜻하지만 확신에 찬
- 실용적이지만 법적으로 정확한
- 공감적이지만 현실적인"""
    
    def build_user_prompt(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        """사용자 프롬프트 생성"""
        # 컨텍스트 문서 정리
        context_text = self._format_context_docs(context_docs)
        
        return f"""다음 질문에 대해 법무법인 혜안 톤으로 전문적인 블로그 글을 작성해주세요.

## 질문
{query}

## 참고 자료
{context_text}

## 작성 요구사항
1. **글 길이**: {self.config.min_chars:,}자 이상 {self.config.max_chars:,}자 이하
2. **소제목**: 최소 {self.config.min_subheadings}개 이상의 ## 소제목 포함
3. **체크리스트**: {"필수" if self.config.require_checklist else "선택"} - 실무 체크리스트 포함
4. **법적 디스클레이머**: {"필수" if self.config.require_disclaimer else "선택"} - 법적 고지사항 포함

## 출력 형식
다음 템플릿을 따라 작성해주세요:

# [SEO 키워드가 포함된 제목]

## 들어가는 글
[공감형 훅으로 독자의 관심을 끄는 도입부]

## [핵심 주제 1]
[구체적인 사례나 절차 설명]

## [핵심 주제 2]
[실무적인 방법이나 준비사항]

## [핵심 주제 3]
[추가적인 정보나 주의사항]

## 실무 체크리스트
[단계별로 확인할 수 있는 체크리스트]

## 마무리
[결과와 효과, 주의사항, 전문가 도움 권유]

<법적 디스클레이머>
[법적 고지사항]"""
    
    def _format_context_docs(self, context_docs: List[Dict[str, Any]]) -> str:
        """컨텍스트 문서 포맷팅"""
        if not context_docs:
            return "참고 자료가 없습니다."
        
        formatted_docs = []
        for i, doc in enumerate(context_docs, 1):
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})
            source = metadata.get("source_url", "출처 불명")
            
            # 텍스트 길이 제한 (너무 길면 잘라내기)
            if len(text) > 500:
                text = text[:500] + "..."
            
            formatted_docs.append(f"""
### 참고 자료 {i}
**출처**: {source}
**내용**: {text}
""")
        
        return "\n".join(formatted_docs)
    
    def build_refinement_prompt(self, original_prompt: str, issues: List[str]) -> str:
        """개선 요청 프롬프트 생성"""
        issues_text = "\n".join([f"- {issue}" for issue in issues])
        
        return f"""이전에 작성한 글에 다음 문제점들이 있습니다:

{issues_text}

위 문제점들을 해결하여 다시 작성해주세요. 기존 내용의 장점은 유지하면서 문제점만 개선해주세요.

{original_prompt}"""
    
    def get_quality_check_prompt(self) -> str:
        """품질 검증 프롬프트 생성"""
        return f"""다음 글의 품질을 검증해주세요. 각 항목에 대해 통과/실패를 판단하고, 실패한 경우 구체적인 이유를 설명해주세요.

## 검증 항목
1. **글 길이**: {self.config.min_chars:,}자 이상 {self.config.max_chars:,}자 이하
2. **소제목 수**: ## 소제목이 {self.config.min_subheadings}개 이상
3. **체크리스트 포함**: {"실무 체크리스트 섹션이 있는지" if self.config.require_checklist else "체크리스트 포함 여부 (선택사항)"}
4. **법적 디스클레이머**: {"<법적 디스클레이머> 섹션이 있는지" if self.config.require_disclaimer else "디스클레이머 포함 여부 (선택사항)"}
5. **구조적 완성도**: 제목, 들어가는 글, 본문, 마무리가 모두 있는지
6. **톤앤매너**: 법무법인 혜안의 전문적이면서 따뜻한 톤이 유지되는지

## 출력 형식
```json
{{
    "passed": true/false,
    "issues": ["문제점1", "문제점2"],
    "scores": {{
        "length": "통과/실패",
        "subheadings": "통과/실패", 
        "checklist": "통과/실패",
        "disclaimer": "통과/실패",
        "structure": "통과/실패",
        "tone": "통과/실패"
    }}
}}
```"""


class PromptTemplates:
    """프롬프트 템플릿 모음"""
    
    @staticmethod
    def get_chaequan_chusim_prompts() -> Dict[str, str]:
        """채권추심 관련 프롬프트 템플릿"""
        return {
            "system": """당신은 법무법인 혜안의 채권추심 전문 변호사입니다. 채권자에게 실용적이고 효과적인 채권 회수 방법을 제시합니다.

## 핵심 원칙
- 채권자의 권리 보호가 최우선
- 법적 절차의 정확한 안내
- 실무에서 바로 활용 가능한 구체적 방법
- 따뜻한 공감과 전문적 조언의 조화""",
            
            "user_template": """다음 질문에 대해 법무법인 혜안 톤으로 전문적인 블로그 글을 작성해주세요.

질문: {query}

참고 자료:
{context}

요구사항:
- 1,600자 이상 1,900자 이하
- 최소 3개의 ## 소제목
- 실무 체크리스트 포함
- 법적 디스클레이머 포함

구조:
# [SEO 제목]
## 들어가는 글
## [주제 1]
## [주제 2] 
## [주제 3]
## 실무 체크리스트
## 마무리
<법적 디스클레이머>"""
        }
    
    @staticmethod
    def get_common_phrases() -> Dict[str, List[str]]:
        """공통 사용 문구"""
        return {
            "hooks": [
                "채권 회수에 어려움을 겪고 계신가요?",
                "돈을 빌려주었는데 받지 못하고 계신가요?",
                "채권추심 과정에서 막막함을 느끼고 계신가요?",
                "효과적인 채권 회수 방법을 찾고 계신가요?"
            ],
            "transitions": [
                "이제 구체적인 절차를 알아보겠습니다.",
                "실무에서 중요한 포인트들을 정리해드리겠습니다.",
                "다음 단계로 넘어가보겠습니다.",
                "더 자세한 내용을 살펴보겠습니다."
            ],
            "cta": [
                "법무법인 혜안의 전문 변호사와 상담하시면 더욱 구체적인 도움을 받으실 수 있습니다.",
                "복잡한 사안의 경우 전문가의 도움을 받으시는 것을 권장드립니다.",
                "법무법인 혜안에서는 개별 사안에 맞는 맞춤형 솔루션을 제공합니다.",
                "무료 상담을 통해 귀하의 상황에 가장 적합한 방법을 찾아보세요."
            ],
            "disclaimers": [
                "본 내용은 일반적인 정보 제공을 위한 것으로, 개별 사안에 대한 법률 자문은 아닙니다.",
                "구체적인 법적 조언이 필요한 경우 법무법인 혜안의 전문 변호사와 상담하시기 바랍니다.",
                "법률은 변경될 수 있으므로 최신 법령을 확인하시기 바랍니다.",
                "개별 사안의 특성에 따라 적용되는 법률과 절차가 다를 수 있습니다."
            ]
        }
    
    @staticmethod
    def get_checklist_templates() -> Dict[str, List[str]]:
        """체크리스트 템플릿"""
        return {
            "chaequan_chusim": [
                "□ 채권 발생 근거 서류 확인 (계약서, 영수증, 거래내역 등)",
                "□ 채무자 정보 수집 (주소, 연락처, 재산 현황)",
                "□ 채권 소멸시효 확인 (3년 또는 5년)",
                "□ 내용증명 발송 준비 (채권 내용, 상환 요구)",
                "□ 지급명령 신청 서류 준비 (신청서, 증빙서류)",
                "□ 강제집행 가능 재산 조사",
                "□ 법원 수수료 및 비용 산정",
                "□ 전문가 상담 및 대리인 선임 검토"
            ],
            "jigeumyeongryeong": [
                "□ 지급명령 신청서 작성",
                "□ 채권 발생 근거 서류 첨부",
                "□ 채무자 주소 확인 및 증명서류 첨부",
                "□ 법원 수수료 납부 (채권액의 1/100)",
                "□ 신청서 제출 및 접수 확인",
                "□ 채무자 이의신청 여부 확인",
                "□ 확정증명서 발급 신청",
                "□ 강제집행 절차 진행"
            ]
        }


# 편의 함수들
def build_hyean_prompt(query: str, 
                      context_docs: List[Dict[str, Any]], 
                      config: Optional[PromptConfig] = None) -> tuple[str, str]:
    """혜안 톤 프롬프트 생성"""
    builder = HyeanPromptBuilder(config)
    system_prompt = builder.build_system_prompt()
    user_prompt = builder.build_user_prompt(query, context_docs)
    return system_prompt, user_prompt


def get_quality_check_prompt(config: Optional[PromptConfig] = None) -> str:
    """품질 검증 프롬프트 생성"""
    builder = HyeanPromptBuilder(config)
    return builder.get_quality_check_prompt()


def get_refinement_prompt(original_prompt: str, 
                         issues: List[str], 
                         config: Optional[PromptConfig] = None) -> str:
    """개선 요청 프롬프트 생성"""
    builder = HyeanPromptBuilder(config)
    return builder.build_refinement_prompt(original_prompt, issues)


# 테스트용 함수
def test_prompt_builder():
    """프롬프트 빌더 테스트"""
    # 테스트 설정
    config = PromptConfig(
        min_chars=1000,
        max_chars=1500,
        min_subheadings=2,
        require_checklist=True,
        require_disclaimer=True
    )
    
    builder = HyeanPromptBuilder(config)
    
    # 시스템 프롬프트 테스트
    system_prompt = builder.build_system_prompt()
    print("✅ 시스템 프롬프트 생성 테스트 통과")
    print(f"길이: {len(system_prompt)}자")
    
    # 사용자 프롬프트 테스트
    query = "채권추심 절차에 대해 설명해주세요"
    context_docs = [
        {
            "text": "채권추심은 내용증명 발송부터 시작됩니다.",
            "metadata": {"source_url": "https://test.com/1"}
        },
        {
            "text": "지급명령 신청 시 필요한 서류들을 준비해야 합니다.",
            "metadata": {"source_url": "https://test.com/2"}
        }
    ]
    
    user_prompt = builder.build_user_prompt(query, context_docs)
    print("✅ 사용자 프롬프트 생성 테스트 통과")
    print(f"길이: {len(user_prompt)}자")
    
    # 품질 검증 프롬프트 테스트
    quality_prompt = builder.get_quality_check_prompt()
    print("✅ 품질 검증 프롬프트 생성 테스트 통과")
    
    # 개선 요청 프롬프트 테스트
    issues = ["글 길이가 부족합니다", "소제목이 부족합니다"]
    refinement_prompt = builder.build_refinement_prompt(user_prompt, issues)
    print("✅ 개선 요청 프롬프트 생성 테스트 통과")
    
    # 템플릿 테스트
    templates = PromptTemplates.get_chaequan_chusim_prompts()
    print("✅ 템플릿 조회 테스트 통과")
    
    phrases = PromptTemplates.get_common_phrases()
    print("✅ 공통 문구 조회 테스트 통과")
    
    checklists = PromptTemplates.get_checklist_templates()
    print("✅ 체크리스트 템플릿 조회 테스트 통과")
    
    print("✅ HyeanPromptBuilder 테스트 완료")


if __name__ == "__main__":
    test_prompt_builder()
