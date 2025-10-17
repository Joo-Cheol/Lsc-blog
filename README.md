# LSC Blog Generator - 법무법인 혜안 채권추심 블로그 자동화 시스템

RAG(Retrieval-Augmented Generation) 기반의 채권추심 전문 블로그 글 자동 생성 시스템입니다. 네이버 블로그에서 관련 데이터를 수집하고, ChromaDB를 활용한 벡터 검색과 Gemini API를 통한 고품질 콘텐츠 생성을 제공합니다.

## 🚀 주요 기능

- **지능형 데이터 수집**: 네이버 블로그에서 채권추심 관련 글을 자동 크롤링
- **벡터 기반 검색**: ChromaDB를 활용한 의미적 문서 검색
- **RAG 기반 글 생성**: Gemini API를 통한 전문적이고 SEO 최적화된 블로그 글 생성
- **대화형 인터페이스**: 사용자 친화적인 명령어 기반 시스템
- **Next.js 웹 인터페이스**: 현대적인 웹 UI 제공
- **운영 모니터링**: 실시간 헬스 체크, 통계, 임베딩 캐시 hit rate 모니터링

## 📋 시스템 요구사항

- Python 3.8 이상
- Node.js 18 이상
- Chrome 브라우저 (Selenium WebDriver용)
- Gemini API 키

## 🛠️ 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/Joo-Cheol/Lsc-blog.git
cd Lsc-blog
```

### 2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
# Python 의존성
pip install -r config/requirements.txt

# Node.js 의존성
npm install
```

### 4. Chrome WebDriver 설치
```bash
# Windows (Chocolatey 사용)
choco install chromedriver

# macOS (Homebrew 사용)
brew install chromedriver

# Linux
sudo apt-get install chromium-chromedriver
```

### 5. 환경변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# Gemini API 키 설정
GEMINI_API_KEY=your_api_key_here
```

### 6. 시스템 테스트
```bash
# 전체 시스템 테스트
python test_api.py
python test_generate.py
```

## 🎯 사용 방법

### 웹 인터페이스 (권장)
```bash
# 프론트엔드 시작
npm run dev

# 백엔드 시작 (별도 터미널)
python api/main.py
```

### 명령어 옵션
```bash
# 데이터 크롤링만 실행
python src/crawler.py

# 특정 질문으로 블로그 글 생성
python src/generator/guide_based_generator.py

# 헤드리스 모드로 실행
python src/crawler.py --headless
```

## 📁 프로젝트 구조

```
Lsc-blog/
├── app/                    # Next.js 프론트엔드
├── api/                    # FastAPI 백엔드
├── src/                    # 핵심 Python 모듈
│   ├── crawler.py         # 네이버 블로그 크롤링
│   ├── generator/         # 블로그 글 생성 모듈
│   ├── search/            # 벡터 검색 모듈
│   ├── llm/               # LLM 서비스
│   └── data/              # 데이터 저장소
├── components/             # React 컴포넌트
├── lib/                    # 유틸리티 함수
├── scripts/                # 배포 및 실행 스크립트
├── docs/                   # 문서
└── monitoring/             # 모니터링 도구
```

## 🔧 모듈별 상세 설명

### crawler.py
- **기능**: 네이버 블로그에서 채권추심 관련 글 수집
- **기술**: Selenium WebDriver를 활용한 동적 콘텐츠 처리
- **대상**: '채권추심', '미수금 회수', '떼인 돈 받는 법' 등 키워드 검색 결과

### generator/
- **기능**: RAG 기반으로 전문적인 블로그 글 생성
- **기술**: Gemini API를 활용한 대화형 AI
- **특징**: 법무법인 혜안의 전문성을 반영한 고품질 콘텐츠 생성

### search/
- **기능**: 수집된 텍스트를 벡터화하여 ChromaDB에 저장
- **기술**: sentence-transformers를 활용한 다국어 임베딩
- **특징**: 텍스트 청킹, 전처리, 의미적 검색 지원

## 📊 시스템 워크플로우

1. **데이터 수집**: 네이버 블로그에서 채권추심 관련 글 크롤링
2. **벡터화**: 수집된 텍스트를 임베딩으로 변환하여 ChromaDB에 저장
3. **검색**: 사용자 질문과 관련된 문서를 의미적으로 검색
4. **생성**: 검색된 문서를 컨텍스트로 활용하여 Gemini API로 전문 글 생성
5. **출력**: SEO 최적화된 구조화된 블로그 글 제공

## 🎨 생성되는 블로그 글 구조

```
# [SEO 최적화 제목]

## 서론
[독자 관심 유도 및 문제 제기]

## [소제목 1]
[구체적 내용 및 사례]

## [소제목 2]
[실용적 조언 및 방법론]

## [소제목 3]
[법적 근거 및 주의사항]

## 결론
[핵심 요약 및 행동 지침]

---
*본 글은 법무법인 혜안에서 제공하는 일반적인 법률 정보입니다.*
```

## ⚠️ 주의사항

- **법적 한계**: 생성된 글은 일반적인 법률 정보이며, 구체적인 사안은 전문가 상담이 필요합니다.
- **API 제한**: Gemini API 사용량 제한을 확인하세요.
- **크롤링 윤리**: 네이버의 robots.txt 및 이용약관을 준수하세요.
- **개인정보**: 수집된 데이터의 개인정보 보호를 위해 적절한 처리가 필요합니다.

## 🐛 문제 해결

### Chrome WebDriver 오류
```bash
# WebDriver 버전 확인
chromedriver --version
chrome --version

# 버전 불일치 시 업데이트
pip install --upgrade selenium
```

### ChromaDB 오류
```bash
# 데이터베이스 초기화
rm -rf src/data/indexes/
python src/crawler.py
```

### API 키 오류
```bash
# 환경변수 확인
echo $GEMINI_API_KEY

# .env 파일 확인
cat .env
```

## 📈 성능 최적화

- **청크 크기 조정**: `src/search/embedding.py`의 `chunk_size` 파라미터 조정
- **검색 결과 수**: `n_references` 파라미터로 참조 문서 수 조정
- **크롤링 간격**: `src/crawler.py`의 `time.sleep()` 값 조정
- **임베딩 캐시 hit rate**: `(total_accesses - total_embeddings) / total_accesses * 100` - 캐시 효율성 지표

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요.

---

**법무법인 혜안** - 전문적이고 신뢰할 수 있는 법률 서비스
