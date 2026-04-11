#!/bin/bash
# JackPy 봇 실행 스크립트 (launchd용)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

# .env 로드 (공백/특수문자 포함된 값 안전 처리)
if [ -f "$SCRIPT_DIR/.env" ]; then
    while IFS='=' read -r key value; do
        # 주석 및 빈 줄 무시
        [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
        # 따옴표 제거 후 export
        value="${value%\"}"
        value="${value#\"}"
        export "$key=$value"
    done < "$SCRIPT_DIR/.env"
fi

# venv Python으로 실행
exec "$SCRIPT_DIR/venv/bin/python3" -m bot.main
