# 📊 Grafana 대시보드 설정 가이드

## 🎯 **권장 패널 구성**

### **1. 검색 성능 패널**
```promql
# 검색 P95 응답 시간
histogram_quantile(0.95, rate(http_request_seconds_bucket{path="/api/search"}[5m]))

# 검색 요청 수 (성공/실패)
rate(search_requests_total[5m])

# 검색 캐시 히트율
rate(search_requests_total{status="success"}[5m]) / rate(search_requests_total[5m]) * 100
```

### **2. 생성 품질 패널**
```promql
# QC 통과율
rate(generate_requests_total{status="success"}[5m]) / rate(generate_requests_total[5m]) * 100

# 생성 요청 수 (성공/QC실패/에러)
rate(generate_requests_total[5m])

# 평균 생성 시간
histogram_quantile(0.50, rate(http_request_seconds_bucket{path="/api/generate"}[5m]))
```

### **3. 에러 모니터링 패널**
```promql
# 429 (레이트 리밋) 에러율
rate(http_requests_total{status="429"}[5m])

# 401 (인증 실패) 에러율  
rate(http_requests_total{status="401"}[5m])

# 5xx (서버 에러) 에러율
rate(http_requests_total{status=~"5.."}[5m])

# 전체 에러율
rate(http_requests_total{status=~"4..|5.."}[5m]) / rate(http_requests_total[5m]) * 100
```

### **4. 시스템 리소스 패널**
```promql
# HTTP 요청 수 (전체)
rate(http_requests_total[5m])

# 평균 응답 시간 (전체)
histogram_quantile(0.50, rate(http_request_seconds_bucket[5m]))

# P95 응답 시간 (전체)
histogram_quantile(0.95, rate(http_request_seconds_bucket[5m]))
```

## 🚨 **알람 설정**

### **Critical 알람**
```yaml
# 5xx 에러율 5% 초과
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "High 5xx error rate detected"

# QC 통과율 80% 미만
- alert: LowQCPassRate
  expr: rate(generate_requests_total{status="success"}[5m]) / rate(generate_requests_total[5m]) < 0.8
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "QC pass rate below 80%"

# 검색 P95 응답 시간 2초 초과
- alert: SlowSearchResponse
  expr: histogram_quantile(0.95, rate(http_request_seconds_bucket{path="/api/search"}[5m])) > 2
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "Search response time too slow"
```

### **Warning 알람**
```yaml
# 429 에러율 1% 초과
- alert: HighRateLimit
  expr: rate(http_requests_total{status="429"}[5m]) / rate(http_requests_total[5m]) > 0.01
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High rate limit errors"

# 캐시 히트율 70% 미만
- alert: LowCacheHitRate
  expr: rate(search_requests_total{status="success"}[5m]) / rate(search_requests_total[5m]) < 0.7
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Cache hit rate below 70%"
```

## 📋 **대시보드 JSON 설정**

### **기본 대시보드 구조**
```json
{
  "dashboard": {
    "title": "LSC Blog Generator - 운영 대시보드",
    "panels": [
      {
        "title": "검색 성능",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_seconds_bucket{path=\"/api/search\"}[5m]))",
            "legendFormat": "P95 응답시간"
          }
        ]
      },
      {
        "title": "QC 통과율",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(generate_requests_total{status=\"success\"}[5m]) / rate(generate_requests_total[5m]) * 100",
            "legendFormat": "통과율 %"
          }
        ]
      },
      {
        "title": "에러율",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=\"429\"}[5m])",
            "legendFormat": "429 Rate Limit"
          },
          {
            "expr": "rate(http_requests_total{status=\"401\"}[5m])",
            "legendFormat": "401 Unauthorized"
          },
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx Server Error"
          }
        ]
      }
    ]
  }
}
```

## 🔧 **Prometheus 설정**

### **prometheus.yml**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'lsc-blog-generator'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

## 📊 **로그 기반 메트릭 (선택사항)**

### **Loki 쿼리 예시**
```logql
# 검색 품질 로그 분석
{job="lsc-blog-generator"} |= "search_result" | json | unwrap combo | rate()

# 생성 품질 로그 분석  
{job="lsc-blog-generator"} |= "generate_result" | json | unwrap qc_passed | rate()

# 에러 로그 분석
{job="lsc-blog-generator"} |= "error" | json | unwrap error_category | rate()
```

## 🎯 **운영 체크리스트**

### **일일 모니터링**
- [ ] QC 통과율 90% 이상 유지
- [ ] 검색 P95 응답시간 1초 이하
- [ ] 5xx 에러율 1% 이하
- [ ] 캐시 히트율 80% 이상

### **주간 리뷰**
- [ ] 에러 패턴 분석
- [ ] 성능 트렌드 분석
- [ ] 알람 정책 검토
- [ ] 대시보드 개선

## 🚀 **고급 기능**

### **A/B 테스트 메트릭**
```promql
# Alpha 가중치별 검색 성능 비교
histogram_quantile(0.95, rate(http_request_seconds_bucket{path="/api/search",alpha="0.1"}[5m]))
histogram_quantile(0.95, rate(http_request_seconds_bucket{path="/api/search",alpha="0.2"}[5m]))
histogram_quantile(0.95, rate(http_request_seconds_bucket{path="/api/search",alpha="0.3"}[5m]))
```

### **사용자별 메트릭**
```promql
# API Key별 사용량
rate(http_requests_total{api_key_hash="abc123"}[5m])
rate(http_requests_total{api_key_hash="def456"}[5m])
```

이 가이드를 따라 설정하면 **완벽한 운영 모니터링 시스템**이 구축됩니다! 🎉






