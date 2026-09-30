#!/usr/bin/env bash
# JackPy 운영 서버 배포
# git pull → (의존성 변경 시) pip install → import 확인 → 재시작 → 로그 확인
#
# 사용법:
#   JACKPY_HOST=<서버 IP> ./scripts/deploy.sh
#
# 환경변수:
#   JACKPY_HOST      (필수) 서버 주소
#   JACKPY_SSH_USER  SSH 접속 계정 (기본: 현재 로컬 사용자)
#   JACKPY_SSH_KEY   SSH 키 경로 (기본: ~/.ssh/google_compute_engine)
#   JACKPY_APP_USER  봇 실행 계정 (기본: jackpy)
#   JACKPY_DIR       서버의 코드 경로 (기본: /home/$JACKPY_APP_USER/jackpy)
#
# 배포 전 main에 push되어 있어야 한다 (서버는 origin/main을 pull).

set -euo pipefail

HOST="${JACKPY_HOST:?JACKPY_HOST(서버 주소)를 지정하세요}"
SSH_USER="${JACKPY_SSH_USER:-$USER}"
SSH_KEY="${JACKPY_SSH_KEY:-$HOME/.ssh/google_compute_engine}"
APP_USER="${JACKPY_APP_USER:-jackpy}"
APP_DIR="${JACKPY_DIR:-/home/$APP_USER/jackpy}"

if [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then
    echo "⚠️  커밋되지 않은 로컬 변경이 있습니다 (서버에는 origin/main만 배포됩니다)"
fi
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main 2>/dev/null)" ]; then
    echo "⚠️  로컬 HEAD가 origin/main과 다릅니다 — push를 잊지 않았는지 확인하세요"
fi

echo "==> $SSH_USER@$HOST ($APP_DIR) 배포 시작"

ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$SSH_USER@$HOST" \
    sudo bash -s -- "$APP_USER" "$APP_DIR" <<'REMOTE'
set -euo pipefail
APP_USER="$1"
APP_DIR="$2"
cd "$APP_DIR"
as_app() { sudo -u "$APP_USER" "$@"; }

for f in game_sessions.json table_sessions.json; do
    if [ -f "$f" ]; then
        echo "ℹ️  진행 중인 세션 있음 ($f) — 재시작 후 자동 복원됩니다"
    fi
done

OLD_HEAD="$(as_app git rev-parse HEAD)"
as_app git pull --ff-only origin main
NEW_HEAD="$(as_app git rev-parse HEAD)"
if [ "$OLD_HEAD" = "$NEW_HEAD" ]; then
    echo "ℹ️  새 커밋 없음 ($NEW_HEAD) — 재시작만 진행합니다"
else
    as_app git log --oneline "$OLD_HEAD..$NEW_HEAD"
fi

if ! as_app git diff --quiet "$OLD_HEAD" "$NEW_HEAD" -- infra/requirements.txt; then
    echo "==> 의존성 변경 감지 — pip install"
    as_app ./venv/bin/pip install -q -r infra/requirements.txt
fi

echo "==> import 확인 (실패하면 재시작하지 않음)"
as_app ./venv/bin/python -c "import bot.handlers, bot.handlers.menu" >/dev/null

LOG=jackpy.log
BEFORE=0
if [ -f "$LOG" ]; then
    BEFORE="$(wc -l < "$LOG")"
fi

echo "==> 재시작"
systemctl restart jackpy

for _ in $(seq 1 30); do
    if tail -n +"$((BEFORE + 1))" "$LOG" 2>/dev/null | grep -q "Application started"; then
        break
    fi
    sleep 1
done

NEW_LOG="$(tail -n +"$((BEFORE + 1))" "$LOG" 2>/dev/null || true)"
if ! grep -q "Application started" <<<"$NEW_LOG"; then
    echo "❌ 30초 안에 기동 로그가 없습니다. 상태: $(systemctl is-active jackpy)"
    tail -n 20 "$LOG" || true
    exit 1
fi
if grep -qE "Conflict|Traceback" <<<"$NEW_LOG"; then
    echo "❌ 기동 로그에 Conflict/Traceback 발견 (같은 토큰으로 다른 곳에서 실행 중일 수 있음)"
    grep -E "Conflict|Traceback" <<<"$NEW_LOG" | tail -n 5
    exit 1
fi
echo "✅ 배포 완료 — $(systemctl is-active jackpy), $(as_app git log -1 --format='%h %s')"
REMOTE
