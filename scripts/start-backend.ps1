# 백엔드 서버 시작 스크립트
Write-Host "🚀 백엔드 서버 시작 중..." -ForegroundColor Green

# CORS 설정
$env:CORS_ORIGINS="http://localhost:3000"

# 백엔드 서버 실행
python -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload

Write-Host "✅ 백엔드 서버가 http://localhost:8000 에서 실행 중입니다." -ForegroundColor Green




