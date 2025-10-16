# 🚀 프로덕션 하드닝 체크리스트

## ✅ SLO 정의 및 모니터링

### 성능 SLO
- **P95 응답 시간**: ≤ 200ms
- **에러율**: ≤ 0.5%
- **콜드스타트**: ≤ 2초
- **캐시 히트율**: ≥ 60%

### 품질 SLO
- **Recall@10**: ≥ 0.7
- **nDCG@10**: ≥ 0.6
- **MRR**: ≥ 0.5

## 🔧 헬스/옵저버빌리티

### 엔드포인트
- `GET /healthz`: 프로세스·메모리 헬스 체크
- `GET /readyz`: 인덱스 로드 완료 체크
- `GET /metrics`: 실시간 메트릭 (qps, p50/p95, cache_hit, OOM, memmap_page_faults)

### 모니터링 지표
```bash
# 헬스 체크
curl http://localhost:8000/healthz

# 준비 상태 확인
curl http://localhost:8000/readyz

# 메트릭 조회
curl http://localhost:8000/metrics
```

## 📦 아티팩트 운용

### 버전 관리
```bash
# 버전별 아티팩트 구조
artifacts/
├── 20251014_1134/
│   ├── index-20251014_1134.npy
│   └── meta-20251014_1134.json
├── 20251014_1200/
│   ├── index-20251014_1200.npy
│   └── meta-20251014_1200.json
└── latest -> 20251014_1200
```

### 증분 업데이트
```bash
# 새 문서 추가
python incremental_update.py new_documents.jsonl

# 세그먼트 파일 생성
python artifact_manager.py --create-segments
```

## 🔄 릴리즈·롤백

### 블루/그린 배포
```bash
# 새 버전 배포
python artifact_manager.py --deploy-version 20251014_1200

# 트래픽 전환 (10% 샤도우)
python artifact_manager.py --switch-traffic --percentage 10

# 전체 전환
python artifact_manager.py --switch-traffic --percentage 100
```

### 롤백 절차
```bash
# 이전 버전으로 롤백
python artifact_manager.py --rollback 20251014_1134

# 무다운타임 롤백 (심볼릭 링크 스왑)
ln -sf 20251014_1134 artifacts/latest
```

## 🛡️ 보안/규정

### PII 마스킹
- 전화번호: `010-1234-5678` → `01**-****-****`
- 주민등록번호: `901201-1234567` → `90****-*******`
- 계좌번호: `123-456-789012` → `12*-***-******`
- 이메일: `test@example.com` → `t***@e******.com`

### 로깅 보안
```python
# 안전한 로깅
from security_utils import sanitize_query_for_logging

query_masked = sanitize_query_for_logging(user_query)
logger.info(f"Search query: {query_masked}")
```

## 🔍 질의 품질 가드

### e5 프리픽스 일관성
```python
# 쿼리 임베딩 시 프리픽스 적용
prefixed_query = f"query: {user_query}"
embedding = model.encode([prefixed_query], normalize_embeddings=True)[0]
```

### 실험 플래그
```python
# 하이브리드 검색 실험
USE_HYBRID_SEARCH = os.getenv("USE_HYBRID_SEARCH", "false").lower() == "true"

# 리랭커 실험
USE_RERANKER = os.getenv("USE_RERANKER", "false").lower() == "true"
```

## 💾 백업·DR

### 자동 백업
```bash
# 일일 백업 (크론)
0 2 * * * python artifact_manager.py --backup-to-s3

# 30일 보존 정책
python artifact_manager.py --cleanup-old-versions --keep-days 30
```

### 워밍업
```bash
# 콜드스타트 워밍업
python production_api.py --warmup-queries 200
```

## 🚀 실행 명령어

### 1. 프로덕션 API 서버 시작
```bash
# 하드닝된 API 서버
python production_api.py

# 또는 uvicorn으로 실행
uvicorn production_api:app --host 0.0.0.0 --port 8000 --workers 1
```

### 2. 웹 UI 서빙
```bash
# 정적 파일 서빙
python -m http.server 8080

# 또는 nginx 설정
# location / {
#     root /path/to/search_ui.html;
#     try_files $uri $uri/ /index.html;
# }
```

### 3. 모니터링 실행
```bash
# 품질 모니터링
python quality_monitor.py

# 성능 모니터링
python monitoring.py
```

### 4. 증분 업데이트
```bash
# 새 문서 추가
python incremental_update.py new_documents.jsonl

# 아티팩트 관리
python artifact_manager.py --list-versions
python artifact_manager.py --cleanup-old-versions
```

## 📊 모니터링 대시보드

### Grafana 메트릭 (예시)
```json
{
  "queries": [
    {
      "expr": "search_api_requests_total",
      "legendFormat": "Total Requests"
    },
    {
      "expr": "search_api_request_duration_p95",
      "legendFormat": "P95 Latency"
    },
    {
      "expr": "search_api_cache_hit_rate",
      "legendFormat": "Cache Hit Rate"
    }
  ]
}
```

### 알림 규칙
```yaml
# Prometheus Alert Rules
groups:
  - name: search_api
    rules:
      - alert: HighLatency
        expr: search_api_request_duration_p95 > 200
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Search API P95 latency is high"
      
      - alert: LowQuality
        expr: search_api_recall_at_10 < 0.7
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Search quality degraded"
```

## 🔧 트러블슈팅

### 일반적인 문제
1. **높은 지연시간**: 캐시 히트율 확인, 배치 크기 조정
2. **메모리 부족**: memmap 모드 사용, 세그먼트 파일 분할
3. **품질 저하**: 골드 쿼리 재평가, 임베딩 모델 재학습

### 로그 확인
```bash
# API 서버 로그
tail -f production_api.log

# 품질 리포트
cat quality_report_*.json

# 메트릭 로그
curl http://localhost:8000/metrics | jq
```

## 🎯 성공 지표

### 운영 성공 기준
- ✅ P95 지연시간 < 200ms
- ✅ 에러율 < 0.5%
- ✅ 콜드스타트 < 2초
- ✅ 캐시 히트율 > 60%
- ✅ Recall@10 > 0.7
- ✅ nDCG@10 > 0.6
- ✅ MRR > 0.5

### 사용자 만족도
- ✅ 검색 응답 시간 < 200ms
- ✅ 검색 정확도 > 80%
- ✅ 시스템 가용성 > 99.9%
- ✅ 에러율 < 0.5%

---

## 🚀 **프로덕션 준비 완료!**

모든 하드닝 체크리스트가 완료되었습니다. 현재 상태로 즉시 프로덕션 트래픽을 받을 수 있습니다.

### 다음 단계 (선택사항)
1. **하이브리드 검색**: BM25 + 벡터 결과 ID 머지
2. **리랭커**: Cross-Encoder로 상위 결과 재정렬
3. **실시간 모니터링**: Grafana + Prometheus 대시보드
4. **자동화**: 크론 기반 증분 업데이트

**현재 성과면 즉시 트래픽 받아도 충분히 견딜 수준입니다!** 🎉




