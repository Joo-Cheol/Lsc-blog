# LSC 프로덕션 서버 실행 스크립트
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"; chcp 65001 > $null
$env:PYTHONPATH = "src"

Write-Host "🚀 LSC 프로덕션 서버 시작..." -ForegroundColor Green

# 가상환경 확인 및 생성
if (-not (Test-Path ".venv")) {
    Write-Host "📦 가상환경 생성 중..." -ForegroundColor Yellow
    python -m venv .venv
}

# 가상환경 활성화
Write-Host "🔧 가상환경 활성화..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# 의존성 설치
Write-Host "📚 의존성 설치..." -ForegroundColor Yellow
pip install -r .\config\requirements.txt

# 로그 디렉토리 생성
if (-not (Test-Path ".\logs")) { 
    New-Item -ItemType Directory -Path .\logs | Out-Null 
}

# .env 파일 확인
if (-not (Test-Path ".\.env")) {
    Write-Host "⚠️  .env 파일이 없습니다. config/env.example을 참고하여 생성해주세요." -ForegroundColor Red
    exit 1
}

# 서버 실행 (로그 파일로 출력)
Write-Host "🌐 서버 시작..." -ForegroundColor Green
uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --log-level info *>&1 | Tee-Object -FilePath .\logs\server.log
