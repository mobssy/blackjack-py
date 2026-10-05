#!/usr/bin/env bash
# JackPy 서버 초기 설정 (Debian/Ubuntu, 새 서버에서 1회 실행)
# 봇 실행 계정 생성 → 코드 클론 → venv/의존성 → .env → systemd 등록
#
# 사용법 (서버에서, sudo 가능한 계정으로):
#   curl -fsSL https://raw.githubusercontent.com/mobssy/blackjack-py/main/scripts/server_setup.sh -o server_setup.sh
#   sudo bash server_setup.sh [봇 실행 계정 (기본: jackpy)]
#
# 이후 .env에 TELEGRAM_TOKEN, ADMIN_IDS를 입력하고 `sudo systemctl start jackpy`.
# 기존 서버의 jackpy.db를 옮길 때는 시작 전에 $APP_DIR/jackpy.db로 복사한다.

set -euo pipefail

APP_USER="${1:-jackpy}"
APP_DIR="/home/$APP_USER/jackpy"
REPO_URL="https://github.com/mobssy/blackjack-py.git"

if [ "$(id -u)" -ne 0 ]; then
    echo "sudo로 실행하세요: sudo bash $0 [계정]" >&2
    exit 1
fi

echo "==> 패키지 설치 (python3, venv, git)"
# 이미지 글꼴(Pretendard)은 저장소 assets/fonts에 포함되어 있어 시스템 폰트가 필요 없다
apt-get update -q
apt-get install -y -q python3 python3-venv python3-pip git

echo "==> 실행 계정: $APP_USER"
if ! id "$APP_USER" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash "$APP_USER"
fi
as_app() { sudo -u "$APP_USER" "$@"; }

echo "==> 코드: $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    as_app git -C "$APP_DIR" pull --ff-only origin main
else
    as_app git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "==> 가상환경 및 의존성"
if [ ! -d venv ]; then
    as_app python3 -m venv venv
fi
as_app ./venv/bin/pip install -q --upgrade pip
as_app ./venv/bin/pip install -q -r infra/requirements.txt

if [ ! -f .env ]; then
    as_app cp .env.example .env
    chmod 600 .env
    echo "==> .env 생성됨 — TELEGRAM_TOKEN, ADMIN_IDS를 입력하세요: $APP_DIR/.env"
fi

echo "==> systemd 등록"
sed -e "s|^User=.*|User=$APP_USER|" \
    -e "s|/home/jackpy/jackpy|$APP_DIR|g" \
    infra/jackpy.service > /etc/systemd/system/jackpy.service
touch /var/log/jackpy.log
systemctl daemon-reload
systemctl enable jackpy

echo
echo "✅ 설정 완료"
echo "   1. $APP_DIR/.env 에 TELEGRAM_TOKEN, ADMIN_IDS 입력"
echo "   2. 같은 토큰으로 실행 중인 다른 봇이 없는지 확인 (있으면 충돌)"
echo "   3. sudo systemctl start jackpy && tail -f $APP_DIR/jackpy.log"
