# 🛠️ JackPy 설치 가이드

## PostgreSQL 에러 해결

### macOS에서 PostgreSQL 설치

```bash
# Homebrew로 PostgreSQL 설치
brew install postgresql@15

# PostgreSQL 시작
brew services start postgresql@15

# PATH 추가 (현재 터미널)
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"

# PATH 영구 추가 (~/.zshrc 또는 ~/.bash_profile)
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 데이터베이스 생성
createdb jackpy
```

### 의존성 설치

```bash
# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r infra/requirements.txt
```

---

## 임시 해결책: SQLite로 개발 (PostgreSQL 없이)

PostgreSQL 설치 없이 바로 시작하려면:

### 1. requirements.txt 수정 (psycopg2 제외)

```bash
# psycopg2-binary 없이 설치
pip install python-telegram-bot==20.7 \
    SQLAlchemy==2.0.23 \
    alembic==1.13.0 \
    APScheduler==3.10.4 \
    python-dotenv==1.0.0 \
    Pillow==10.1.0 \
    pytz==2023.3
```

### 2. .env 파일에서 SQLite 사용

```env
# PostgreSQL 대신 SQLite
DATABASE_URL=sqlite:///./jackpy.db
```

### 3. 봇 실행

```bash
# 데이터베이스 초기화
python -c "from models import init_db; init_db()"

# 봇 실행
python -m bot.main
```

---

## 추천 방법: PostgreSQL 설치

실제 프로덕션 환경에서는 PostgreSQL을 사용하는 것이 좋습니다.

```bash
# 1. PostgreSQL 설치
brew install postgresql@15

# 2. 서비스 시작
brew services start postgresql@15

# 3. 데이터베이스 생성
createdb jackpy

# 4. 의존성 설치
source venv/bin/activate
pip install -r infra/requirements.txt

# 5. 봇 실행
python -m bot.main
```

---

## 확인 명령어

```bash
# PostgreSQL 설치 확인
psql --version

# pg_config 위치 확인
which pg_config

# Python에서 psycopg2 설치 확인
python -c "import psycopg2; print('OK')"

# SQLAlchemy 설치 확인
python -c "import sqlalchemy; print('OK')"
```

---

## VS Code에서 Pylance 에러 해결

### 방법 1: Python 인터프리터 선택

1. `Cmd + Shift + P` (macOS) 또는 `Ctrl + Shift + P` (Windows/Linux)
2. "Python: Select Interpreter" 입력
3. `./venv/bin/python` 선택

### 방법 2: 설정 파일 생성

`.vscode/settings.json` 파일 생성:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.analysis.extraPaths": [
    "${workspaceFolder}"
  ],
  "python.analysis.typeCheckingMode": "basic"
}
```

---

## 문제 해결 체크리스트

- [ ] PostgreSQL 설치됨
- [ ] PostgreSQL 서비스 실행 중
- [ ] 가상환경 생성됨 (`venv/` 폴더 존재)
- [ ] 가상환경 활성화됨 (`which python` 확인)
- [ ] 의존성 설치됨 (`pip list` 확인)
- [ ] `.env` 파일 생성됨
- [ ] VS Code에서 올바른 인터프리터 선택됨

---

## 빠른 확인 스크립트

```bash
#!/bin/bash

echo "=== JackPy 설치 확인 ==="

# PostgreSQL 확인
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL 설치됨: $(psql --version)"
else
    echo "❌ PostgreSQL 미설치"
fi

# 가상환경 확인
if [ -d "venv" ]; then
    echo "✅ 가상환경 존재"
else
    echo "❌ 가상환경 없음"
fi

# .env 파일 확인
if [ -f ".env" ]; then
    echo "✅ .env 파일 존재"
else
    echo "❌ .env 파일 없음"
fi

# SQLAlchemy 확인
if ./venv/bin/python -c "import sqlalchemy" 2>/dev/null; then
    echo "✅ SQLAlchemy 설치됨"
else
    echo "❌ SQLAlchemy 미설치"
fi
```

저장 후 실행:
```bash
chmod +x check_install.sh
./check_install.sh
```
