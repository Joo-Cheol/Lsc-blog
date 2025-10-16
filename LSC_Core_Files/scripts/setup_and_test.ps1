# Gemini API 설정 및 테스트 스크립트
Write-Host "🚀 Gemini API 설정 및 테스트 시작..." -ForegroundColor Green

# 1. 가상환경 설정
Write-Host "1. 가상환경 설정..." -ForegroundColor Yellow
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 의존성 설치
Write-Host "2. 의존성 설치..." -ForegroundColor Yellow
pip install -r requirements.txt

# 3. .env 파일 설정
Write-Host "3. .env 파일 설정..." -ForegroundColor Yellow
if (-not (Test-Path ".\.env")) {
    Copy-Item "env_template" ".\.env"
    Write-Host "⚠️  .env 파일이 생성되었습니다. API 키를 설정해주세요!" -ForegroundColor Red
    Write-Host "   notepad .env" -ForegroundColor Cyan
    notepad .env
} else {
    Write-Host "✅ .env 파일이 이미 존재합니다." -ForegroundColor Green
}

# 4. 테스트 실행
Write-Host "4. 테스트 실행..." -ForegroundColor Yellow
python test_gemini_improved.py

Write-Host "🎉 설정 완료!" -ForegroundColor Green
