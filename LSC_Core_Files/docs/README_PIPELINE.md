# 🏛️ 법무법인 혜안 채권추심 블로그 자동화 시스템 (재구성된 버전)

## 🎯 시스템 개요

**크롤링 → 벡터화 → ChromaDB 업서트** 전 과정을 재현 가능한 형태로 구현한 증분 크롤링 시스템입니다.

### 핵심 특징
- **증분 크롤링**: `last_seen_logno` 기반으로 신규 게시글만 수집
- **중복 차단**: SQLite PRIMARY KEY + ON CONFLICT UPDATE로 중복 방지
- **벡터 검증**: 모든 벡터에 `run_id`와 `source_file` 메타데이터 포함
- **재현 가능**: 실행마다 스냅샷 JSONL 생성으로 완전한 추적성

## 📁 프로젝트 구조

```
LSC/
├── src/
│   ├── crawler_incremental.py      # 증분 크롤링 (메인)
│   ├── state_io.py                 # 증분 상태 관리
│   ├── merge_to_master.py          # SQLite 병합 및 중복 차단
│   ├── vectorize_to_chroma.py      # ChromaDB 벡터화
│   ├── utils_text.py               # 텍스트 정제 및 청킹
│   └── data/
│       ├── master/
│       │   ├── posts.sqlite        # 정본 DB
│       │   └── exports/            # 신규분 JSONL
│       ├── indexes/
│       │   └── chroma/             # ChromaDB 저장소
│       └── processed/              # 실행별 스냅샷
├── state/
│   └── last_seen_logno.json        # 증분 상태
├── run_full_pipeline.py            # Python 통합 실행
├── run_pipeline.ps1                # PowerShell 실행
└── requirements.txt
```

## 🚀 실행 방법

### 1. PowerShell 실행 (권장)
```powershell
# 기본 실행
.\run_pipeline.ps1

# 옵션 지정
.\run_pipeline.ps1 -BlogId "tjwlswlsdl" -CategoryNo 6 -MaxPages 20 -Verify

# 단계별 실행
.\run_pipeline.ps1 -SkipCrawl        # 크롤링 건너뛰기
.\run_pipeline.ps1 -SkipMerge        # 병합 건너뛰기
.\run_pipeline.ps1 -SkipVectorize    # 벡터화 건너뛰기
```

### 2. Python 실행
```bash
# 전체 파이프라인
python run_full_pipeline.py --blog-id tjwlswlsdl --category-no 6 --max-pages 20

# 단계별 실행
python run_full_pipeline.py --skip-crawl      # 크롤링 건너뛰기
python run_full_pipeline.py --skip-merge      # 병합 건너뛰기
python run_full_pipeline.py --skip-vectorize  # 벡터화 건너뛰기
```

### 3. 개별 모듈 실행
```bash
# 1단계: 증분 크롤링
python src/crawler_incremental.py --blog-id tjwlswlsdl --category-no 6 --max-pages 20

# 2단계: SQLite 병합
python src/merge_to_master.py --input "src/data/processed/2025-10-13_0934/posts_2025-10-13_0934.jsonl" --run-id 2025-10-13_0934 --stats

# 3단계: ChromaDB 벡터화
python src/vectorize_to_chroma.py --input "src/data/master/exports/new_for_index_2025-10-13_0934.jsonl" --run-id 2025-10-13_0934 --source-file "src/data/processed/2025-10-13_0934/posts_2025-10-13_0934.jsonl" --verify
```

## 📊 데이터 흐름

### 1. 증분 크롤링
```
네이버 블로그 → 페이지네이션 → 신규 logno 필터링 → 상세 정보 수집 → JSONL 스냅샷
```

### 2. SQLite 병합
```
JSONL 스냅샷 → 중복 차단 → 신규분 추출 → 정본 DB 업데이트 → 신규분 JSONL 생성
```

### 3. ChromaDB 벡터화
```
신규분 JSONL → 텍스트 청킹 → 임베딩 생성 → ChromaDB upsert → 검증
```

## 🔧 핵심 모듈 설명

### `crawler_incremental.py`
- **기능**: 증분 크롤링 (last_seen_logno 기반)
- **출력**: `src/data/processed/{RUN_ID}/posts_{RUN_ID}.jsonl`
- **특징**: 페이지네이션 + 신규 게시글만 수집

### `state_io.py`
- **기능**: 증분 상태 관리
- **파일**: `state/last_seen_logno.json`
- **특징**: 마지막 처리된 logno 저장/로드

### `merge_to_master.py`
- **기능**: SQLite 병합 및 중복 차단
- **입력**: 스냅샷 JSONL
- **출력**: 정본 DB + 신규분 JSONL
- **특징**: PRIMARY KEY(logno) + ON CONFLICT UPDATE

### `vectorize_to_chroma.py`
- **기능**: ChromaDB 벡터화
- **입력**: 신규분 JSONL
- **출력**: ChromaDB 컬렉션
- **특징**: 청킹 + 메타데이터 + 검증

### `utils_text.py`
- **기능**: 텍스트 정제 및 청킹
- **특징**: 슬라이딩 윈도우 + 해시 계산

## 📋 JSONL 스키마

### 스냅샷 JSONL (한 줄 = 1 포스트)
```json
{
  "logno": 223990677354,
  "url": "https://blog.naver.com/...logNo=223990677354",
  "title": "제목",
  "category_no": 6,
  "category_name": "채권추심",
  "posted_at": "2024-12-31T10:22:00+09:00",
  "content": "본문 전체 텍스트",
  "crawled_at": "2025-10-13T09:12:43+09:00",
  "content_hash": "sha256(...)"
}
```

### ChromaDB 메타데이터
```json
{
  "logno": 223990677354,
  "chunk_idx": 0,
  "run_id": "2025-10-13_0934",
  "source_file": "src/data/processed/2025-10-13_0934/posts_2025-10-13_0934.jsonl",
  "posted_at": "2024-12-31T10:22:00+09:00",
  "title": "제목",
  "url": "https://blog.naver.com/...",
  "category_no": 6,
  "category_name": "채권추심",
  "content_hash": "sha256(...)",
  "chunk_count": 3
}
```

## 🔍 검증 방법

### ChromaDB 검증
```python
# 런별 벡터 수 확인
res = collection.get(where={"run_id": "2025-10-13_0934"}, limit=1000000)
print(f"이번 런 벡터: {len(res['ids'])}")

# 파일별 벡터 수 확인
res = collection.get(where={"source_file": "src/data/processed/2025-10-13_0934/posts_2025-10-13_0934.jsonl"}, limit=1000000)
print(f"이 파일 벡터: {len(res['ids'])}")

# 특정 글번호 확인
res = collection.get(where={"logno": 223990677354}, limit=1000)
print(f"이 글 벡터: {len(res['ids'])}")
```

### SQLite 검증
```bash
# 통계 확인
python src/merge_to_master.py --input "dummy.jsonl" --stats

# 직접 쿼리
sqlite3 src/data/master/posts.sqlite "SELECT COUNT(*) FROM posts;"
sqlite3 src/data/master/posts.sqlite "SELECT category_no, COUNT(*) FROM posts GROUP BY category_no;"
```

## ⚙️ 설정 및 튜닝

### 성능 최적화
- **SQLite**: `PRAGMA journal_mode=WAL; synchronous=NORMAL;`
- **ChromaDB**: 배치 크기 100, GPU 사용 가능
- **크롤링**: 요청 간 지연 0.5-1.0초

### 메모리 관리
- **청킹**: max_tokens=1200, overlap=200
- **배치 처리**: 100개씩 upsert
- **임시 파일**: 자동 정리

## 🛠️ 문제 해결

### 일반적인 문제
1. **ChromeDriver 오류**: `selenium/drivers/chromedriver.exe` 확인
2. **ChromaDB 오류**: `pip install chromadb` 재설치
3. **메모리 부족**: 배치 크기 조정

### 복구 방법
1. **상태 초기화**: `state/last_seen_logno.json` 삭제
2. **DB 초기화**: `src/data/master/posts.sqlite` 삭제
3. **ChromaDB 초기화**: `src/data/indexes/chroma/` 삭제

## 📈 운영 원칙

1. **증분성**: 크롤러는 last_seen_logno로 이전보다 큰 logno만 저장
2. **중복 차단**: SQLite PRIMARY KEY(logno) + ON CONFLICT UPDATE
3. **인덱싱 범위 축소**: 매 실행 신규분 JSONL만 Chroma에 upsert
4. **메타데이터 일관성**: 모든 청크에 동일한 run_id/source_file/logno
5. **검증 가능**: ChromaDB where 조건으로 수량/샘플 확인

## 🎉 완성!

이제 **"크롤링은 증분으로 수집하여 실행(run)마다 JSONL 스냅샷을 만들고, 스냅샷은 SQLite에 UPSERT로 병합해 중복을 차단합니다. 병합에서 나온 신규 글만 청크→임베딩하여 ChromaDB에 upsert하며, 모든 벡터에 run_id와 source_file 메타데이터를 넣어 런/파일 단위 검증이 가능하도록"** 구현되었습니다!
