#!/bin/bash
# 자동 백업 스크립트
set -euo pipefail

# 타임스탬프 생성
TS=$(date +"%Y%m%d-%H%M%S")
echo "🚀 백업 시작: $TS"

# 백업 대상 디렉토리
SRC1="./artifacts"
SRC2="./embedding_output"
SRC3="./src/data"

# 로컬 백업 디렉토리
LOCAL_BACKUP_DIR="./backups"
mkdir -p "$LOCAL_BACKUP_DIR"

# 로컬 백업
echo "📦 로컬 백업 생성 중..."
tar -czf "$LOCAL_BACKUP_DIR/backup_$TS.tar.gz" \
    "$SRC1" \
    "$SRC2" \
    "$SRC3" \
    "simple_vector_store.py" \
    "sample_corpus.jsonl" \
    2>/dev/null || echo "⚠️ 일부 파일 누락 (정상)"

# 원격 백업 (rclone이 설정된 경우)
if command -v rclone &> /dev/null; then
    REMOTE_PATH="remote:lawblog-backup/$TS"
    echo "☁️ 원격 백업 시작: $REMOTE_PATH"
    
    # rclone으로 백업
    rclone copy "$SRC1" "$REMOTE_PATH/artifacts" --transfers=8 --progress
    [ -d "$SRC2" ] && rclone copy "$SRC2" "$REMOTE_PATH/embedding_output" --transfers=8 --progress || true
    [ -d "$SRC3" ] && rclone copy "$SRC3" "$REMOTE_PATH/src_data" --transfers=8 --progress || true
    
    # 중요 파일들도 백업
    [ -f "simple_vector_store.py" ] && rclone copy "simple_vector_store.py" "$REMOTE_PATH/" || true
    [ -f "sample_corpus.jsonl" ] && rclone copy "sample_corpus.jsonl" "$REMOTE_PATH/" || true
    
    echo "✅ 원격 백업 완료: $REMOTE_PATH"
else
    echo "⚠️ rclone이 설치되지 않음. 로컬 백업만 수행"
fi

# 오래된 백업 정리 (30일 이상)
echo "🧹 오래된 백업 정리 중..."
find "$LOCAL_BACKUP_DIR" -name "backup_*.tar.gz" -mtime +30 -delete 2>/dev/null || true

echo "🎉 백업 완료: $TS"
echo "📁 로컬 백업: $LOCAL_BACKUP_DIR/backup_$TS.tar.gz"









