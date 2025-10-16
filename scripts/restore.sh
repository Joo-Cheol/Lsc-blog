#!/bin/bash
# 백업 복구 스크립트
set -euo pipefail

if [ $# -eq 0 ]; then
    echo "사용법: $0 <백업_타임스탬프>"
    echo "예시: $0 20251015-030000"
    echo ""
    echo "사용 가능한 백업:"
    ls -la ./backups/backup_*.tar.gz 2>/dev/null | sed 's/.*backup_\(.*\)\.tar\.gz/\1/' || echo "백업이 없습니다"
    exit 1
fi

SNAP=$1
echo "🔄 복구 시작: $SNAP"

# 로컬 백업에서 복구
LOCAL_BACKUP="./backups/backup_$SNAP.tar.gz"
if [ -f "$LOCAL_BACKUP" ]; then
    echo "📦 로컬 백업에서 복구: $LOCAL_BACKUP"
    
    # 기존 파일 백업 (안전장치)
    if [ -d "./artifacts" ] || [ -d "./embedding_output" ]; then
        echo "⚠️ 기존 데이터를 안전하게 백업 중..."
        mv ./artifacts ./artifacts.backup.$(date +%s) 2>/dev/null || true
        mv ./embedding_output ./embedding_output.backup.$(date +%s) 2>/dev/null || true
    fi
    
    # 복구 실행
    tar -xzf "$LOCAL_BACKUP"
    echo "✅ 로컬 백업 복구 완료"
    
elif command -v rclone &> /dev/null; then
    # 원격 백업에서 복구
    REMOTE_PATH="remote:lawblog-backup/$SNAP"
    echo "☁️ 원격 백업에서 복구: $REMOTE_PATH"
    
    # 기존 파일 백업
    if [ -d "./artifacts" ] || [ -d "./embedding_output" ]; then
        echo "⚠️ 기존 데이터를 안전하게 백업 중..."
        mv ./artifacts ./artifacts.backup.$(date +%s) 2>/dev/null || true
        mv ./embedding_output ./embedding_output.backup.$(date +%s) 2>/dev/null || true
    fi
    
    # 원격에서 복구
    rclone copy "$REMOTE_PATH/artifacts" ./artifacts --delete-during --progress
    [ -d "$REMOTE_PATH/embedding_output" ] && rclone copy "$REMOTE_PATH/embedding_output" ./embedding_output --delete-during --progress || true
    [ -d "$REMOTE_PATH/src_data" ] && rclone copy "$REMOTE_PATH/src_data" ./src/data --delete-during --progress || true
    
    # 중요 파일들 복구
    rclone copy "$REMOTE_PATH/simple_vector_store.py" . || true
    rclone copy "$REMOTE_PATH/sample_corpus.jsonl" . || true
    
    echo "✅ 원격 백업 복구 완료"
else
    echo "❌ 백업을 찾을 수 없습니다: $SNAP"
    echo "로컬 백업: $LOCAL_BACKUP"
    echo "rclone이 설치되지 않아 원격 백업을 사용할 수 없습니다"
    exit 1
fi

echo "🎉 복구 완료: $SNAP"
echo "💡 서버를 재시작하여 변경사항을 적용하세요"





