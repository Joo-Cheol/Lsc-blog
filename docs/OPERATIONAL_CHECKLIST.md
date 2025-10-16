# 🚀 LSC 운영 체크리스트

## 📋 **릴리스 전 10분 셀프QA**

### ✅ **1. 헬스체크 검증**
```bash
# Liveness 체크 (프로세스 살았는지)
curl http://localhost:8000/health/live
# 예상: {"ok": true}

# Readiness 체크 (의존성 준비됐는지)
curl http://localhost:8000/health/ready
# 예상: {"ok": true, "model_ping": "ok", "detail": "ok"}
```

### ✅ **2. API 스모크 테스트**
```bash
# 짧은 토픽 테스트
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "채권추심", "keywords": "독촉"}'

# 긴 토픽 테스트
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "채권추심 지급명령 절차와 주의사항", "keywords": "지급명령, 독촉, 집행권원, 소액사건"}'

# 키워드 없는 테스트
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "채권추심 기본 개념"}'
```

### ✅ **3. 로깅 검증**
```bash
# 로그 파일 확인
tail -f logs/server.log

# 예상 로그 형태:
# {"type": "access", "req_id": "xxx", "method": "GET", "path": "/health/live", "status": 200, "ms": 1.2, "ok": true}
# {"type": "access", "req_id": "yyy", "method": "POST", "path": "/api/generate", "status": 200, "ms": 2500.5, "ok": true}
```

### ✅ **4. 보안 검증**
- [ ] `.env` 파일이 Git에 추적되지 않음
- [ ] API 키가 하드코딩되지 않음
- [ ] 보안 헤더가 응답에 포함됨
- [ ] CORS 설정이 적절함

### ✅ **5. 아티팩트 디렉토리**
- [ ] `artifacts/` 디렉토리 권한 확인
- [ ] 백업 정책 확인
- [ ] 디스크 공간 충분함

### ✅ **6. 롤백 준비**
```bash
# 현재 상태를 태그로 저장
git tag release-$(date +%Y%m%d)
git push origin release-$(date +%Y%m%d)

# 문제 발생 시 롤백
git checkout release-YYYYMMDD
```

## 🔧 **운영 명령어**

### 서버 시작
```powershell
.\scripts\run_production.ps1
```

### 테스트 실행
```bash
python src\tests\test_gemini_improved.py
```

### 로그 모니터링
```bash
# 실시간 로그
tail -f logs/server.log

# 에러 로그만
grep "type.*error" logs/server.log

# 특정 요청 ID 추적
grep "req_id.*xxx" logs/server.log
```

### 헬스체크 모니터링
```bash
# Kubernetes/PM2용
curl -f http://localhost:8000/health/live || exit 1
curl -f http://localhost:8000/health/ready || exit 1
```

## 🚨 **장애 대응**

### 1. API 응답 없음
- [ ] 프로세스 상태 확인
- [ ] 포트 8000 사용 중인지 확인
- [ ] 로그 파일 확인

### 2. Gemini API 오류
- [ ] API 키 유효성 확인
- [ ] 모델명 확인
- [ ] 네트워크 연결 확인

### 3. 메모리/CPU 과부하
- [ ] 로그에서 응답 시간 확인
- [ ] 동시 요청 수 제한
- [ ] 서버 리소스 모니터링

## 📊 **성능 지표**

### 정상 범위
- **응답 시간**: < 5초 (블로그 생성)
- **헬스체크**: < 100ms
- **에러율**: < 1%
- **메모리 사용량**: < 1GB

### 알림 임계값
- **응답 시간**: > 10초
- **에러율**: > 5%
- **메모리 사용량**: > 2GB
- **디스크 사용량**: > 80%

## 🔄 **정기 점검**

### 일일
- [ ] 헬스체크 상태 확인
- [ ] 에러 로그 검토
- [ ] API 응답 시간 확인

### 주간
- [ ] 로그 파일 로테이션
- [ ] 아티팩트 디렉토리 정리
- [ ] 의존성 업데이트 검토

### 월간
- [ ] API 키 로테이션
- [ ] 백업 복원 테스트
- [ ] 성능 벤치마크





