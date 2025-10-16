# GPU 최적화 벡터화 실행 스크립트
# RTX 4070 Ti SUPER 16GB + 64GB RAM 최적화

Write-Host "🚀 GPU 최적화 벡터화 시스템 시작" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# 1) 가상환경 활성화
Write-Host "📦 가상환경 활성화 중..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# 2) NVIDIA GPU만 노출
Write-Host "🎮 NVIDIA GPU 설정 중..." -ForegroundColor Yellow
$env:CUDA_VISIBLE_DEVICES = "1"

# 3) 필요한 패키지 설치 확인
Write-Host "📋 필수 패키지 설치 중..." -ForegroundColor Yellow
pip install --upgrade "torch==2.5.*" --index-url https://download.pytorch.org/whl/cu124
pip install --upgrade torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install "chromadb>=0.5.5" "sentence-transformers>=3.0.1" "tqdm" "pydantic<3" "pyarrow"

# 4) GPU 상태 확인
Write-Host "🔍 GPU 상태 확인 중..." -ForegroundColor Yellow
python -c "import torch; print('PyTorch 버전:', torch.__version__); print('CUDA 사용 가능:', torch.cuda.is_available()); print('CUDA 버전:', torch.version.cuda if torch.cuda.is_available() else 'N/A'); print('GPU 이름:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

# 5) 벡터화 실행
Write-Host "⚡ 벡터화 및 색인 시작..." -ForegroundColor Green
$env:PYTHONPATH = "src"
python .\src\ingest\embed_to_chroma.py

Write-Host "✅ 벡터화 완료!" -ForegroundColor Green





