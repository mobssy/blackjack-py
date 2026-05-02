#!/bin/bash
# 서버 초기 설정 스크립트 (Oracle Cloud Ubuntu에서 1회 실행)

set -e

JACKPY_DIR="/home/ubuntu/jackpy"

echo "==> 패키지 업데이트..."
sudo apt-get update -q
sudo apt-get install -y python3.12 python3.12-venv python3-pip

echo "==> venv 생성 및 패키지 설치..."
cd "$JACKPY_DIR"
python3.12 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install \
  "python-telegram-bot==20.7" \
  "SQLAlchemy==2.0.23" \
  "alembic==1.13.0" \
  "Pillow==10.1.0" \
  "python-dotenv==1.0.0" \
  "requests==2.31.0" \
  "apscheduler"

echo "==> DB 초기화..."
venv/bin/python3 init_db.py

echo "==> systemd 서비스 등록..."
sudo tee /etc/systemd/system/jackpy.service > /dev/null <<EOF
[Unit]
Description=JackPy Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$JACKPY_DIR
ExecStart=$JACKPY_DIR/venv/bin/python3 -m bot.main
Restart=always
RestartSec=15
StandardOutput=append:/var/log/jackpy.log
StandardError=append:/var/log/jackpy.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jackpy
echo ""
echo "==> 설정 완료!"
echo "    .env 파일을 올린 후: sudo systemctl start jackpy"
