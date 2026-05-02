#!/bin/bash
# Oracle Cloud 배포 스크립트
# 사용법: ./scripts/deploy.sh <서버IP> <SSH키경로>
# 예: ./scripts/deploy.sh 150.230.x.x ~/.ssh/jackpy_oracle.key

set -e

SERVER_IP="${1:?'서버 IP를 입력하세요: ./deploy.sh <IP> <KEY>'}"
SSH_KEY="${2:?'SSH 키 경로를 입력하세요: ./deploy.sh <IP> <KEY>'}"
REMOTE_USER="ubuntu"
REMOTE_DIR="/home/ubuntu/jackpy"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"

echo "==> 파일 동기화 중..."
rsync -avz \
  --exclude='venv/' \
  --exclude='venv_backup/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.git/' \
  --exclude='*.log' \
  --exclude='*.log.old' \
  --exclude='*.db' \
  --exclude='.env' \
  --exclude='.DS_Store' \
  --exclude='bot_output.log' \
  -e "ssh $SSH_OPTS" \
  ./ "$REMOTE_USER@$SERVER_IP:$REMOTE_DIR/"

echo "==> 완료! 서버에서 setup.sh를 실행하세요:"
echo "    ssh $SSH_OPTS $REMOTE_USER@$SERVER_IP 'bash $REMOTE_DIR/scripts/server_setup.sh'"
