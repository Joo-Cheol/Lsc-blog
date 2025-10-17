# 브랜치 전략 가이드

## 브랜치 구조

### 1. 브랜치 종류와 용도

#### main (보호/배포선)
- 항상 배포 가능한 상태
- 태그로 배포 버전 관리
- 보호 규칙: 직접 push 금지, PR만 머지, 필수 체크(테스트/리뷰)

#### dev (통합/일상 개발)
- 작업 브랜치의 머지 대상
- 스프린트 끝날 때 dev → main으로 릴리스 PR 생성

#### feature/<이슈번호-키워드> (짧게 사용)
- 단일 기능/수정 단위
- 예시: `feature/12-embed-cache`, `feature/21-reranker`
- 완료 후 dev로 PR, 머지 되면 브랜치 삭제

#### hotfix/<버그-키워드> (긴급 수정)
- 프로덕션 급한 버그
- hotfix/* → main 으로 PR, 동시에 dev에도 cherry-pick 또는 머지로 반영

## 머지 방식

- **feature → dev**: Squash merge(커밋 1개로 합치기) 권장 → 히스토리 깔끔
- **dev → main**: Merge commit 또는 Squash 중 하나를 팀 규칙으로 고정 (혼합 금지)

## 태그/버전

main 머지 시: SemVer 태그 붙이기 v0.3.0, v0.3.1 …

변경규모 기준:
- **major**: API/호환성 깨짐
- **minor**: 기능 추가(호환 유지)
- **patch**: 버그픽스/문서/성능 미세개선

## 실제 작업 흐름

### A. 최초 세팅(1회)
```bash
git checkout -b dev
git push -u origin dev
```

GitHub → Settings → Branches:
- Protect 'main': direct push 금지, PR 필수, 최소 1 review, status checks(required)
- (선택) Protect 'dev': direct push 금지, PR 필수

### B. 이슈 단위 작업

1. 이슈 생성(예: "임베딩 캐시 추가") → 번호 #34

2. 작업 브랜치 생성:
```bash
git checkout dev
git pull
git checkout -b feature/34-embed-cache
```

3. 커밋 규칙(예시):
```
feat(vector): add embed cache with duckdb and chunk_id hashing (#34)
test(vector): add unit tests for embed cache hit/miss (#34)
```

4. 원격 푸시:
```bash
git push -u origin feature/34-embed-cache
```

5. PR 생성: feature/34-embed-cache → dev

6. PR 템플릿 체크리스트:
   - [ ] 테스트 통과
   - [ ] 로그: [INDEX] added/skipped 출력
   - [ ] README/ENV 갱신
   - [ ] 성능/품질 지표 1개 이상 보고(예: 캐시 hit rate)

7. 머지: Squash merge

8. 브랜치 삭제:
```bash
git branch -d feature/34-embed-cache
git push origin --delete feature/34-embed-cache
```

### C. 릴리스(스프린트 종료 또는 기능묶음)
```bash
git checkout dev
git pull
git checkout main
git pull
git merge --no-ff dev -m "release: v0.4.0 - embed cache, reranker, guard"
git tag v0.4.0
git push origin main --tags
```

### D. 긴급 핫픽스
```bash
git checkout -b hotfix/41-chunk-null
# 수정 → 커밋
git push -u origin hotfix/41-chunk-null
# PR: hotfix/41-chunk-null → main  (머지)
# 동일 커밋을 dev에도 반영
git checkout dev
git pull
git cherry-pick <hotfix-commit-sha>   # 또는 main → dev 머지
git push
```

## 데이터/대용량 파일 주의(.gitignore/LFS)

크롤링 결과/임베딩/Chroma 인덱스는 원칙적으로 Repo에 올리지 않음

src/data/**, *.duckdb, *.sqlite, chroma/ 등은 .gitignore 처리

연구 공유가 필요하면 **샘플(소량)**만 올리거나 Git LFS 사용

## 커밋/PR 메시지 컨벤션

### 타입
- feat: 새로운 기능
- fix: 버그 수정
- refactor: 코드 리팩토링
- perf: 성능 개선
- test: 테스트 추가/수정
- docs: 문서 수정
- chore: 기타 작업

### 형식
```
type(scope): summary (#issue)
```

예시: `feat(search): add cross-encoder reranker (#52)`

### PR 템플릿 항목
- 변경 요약
- 테스트 방법
- 성능/품질 영향
- 스크린샷/로그
- 체크리스트(테스트/문서/ENV)

## 브랜치 전략 FAQ

### Q1. 혼자 개발하는데 dev가 꼭 필요해요?
**권장**: 필요합니다. dev가 있어야 main을 항상 깨끗하게 유지하고, 커서AI 자동화 작업을 feature로 쪼개 PR 리뷰/테스트를 거친 뒤 dev에 모아볼 수 있어요. 문제가 생겨도 main은 안전합니다.

### Q2. 작은 수정인데 feature 안 만들고 dev에 바로 커밋해도 되나요?
팀 규칙에 따라 허용 가능하지만, 일관성을 위해 모든 변경은 feature/*로 만드는 걸 추천합니다. 나중에 변경 이력 추적이 훨씬 쉽습니다.

### Q3. 커서AI가 자동으로 파일을 많이 고칠 때는?
커서AI 작업마다 작은 범위로 feature를 쪼개 주세요. "크롤러 스토리지"/"임베딩 캐시"/"리랭커"처럼 기능 단위로 나눠야 코드 리뷰와 롤백이 쉬워집니다.

## 한 줄 가이드

**"같은 브랜치에 계속 올리는 것"** → No.

**"보호된 main + dev + feature/* + hotfix/*"** → Yes.

PR은 Squash, 릴리스는 태그, 데이터는 .gitignore.
