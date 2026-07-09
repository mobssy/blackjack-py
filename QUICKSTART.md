# 🚀 JackPy 빠른 시작 가이드

## ✅ 설정 완료 항목

- ✅ 텔레그램 봇 토큰 설정됨
- ✅ 관리자 ID 설정됨
- ✅ `.env` 파일 생성됨
- ✅ 모든 코드 작성 완료
- ✅ Python 3.11+ deprecation 수정 완료

---

## 📋 시작 전 체크리스트

### 1️⃣ 필수 소프트웨어 설치 확인

```bash
# Python 3.11+ 확인
python3 --version  # 3.11 이상이어야 함

# PostgreSQL 확인
psql --version

# pip 확인
pip3 --version
```

### 2️⃣ PostgreSQL 데이터베이스 생성

```bash
# PostgreSQL 서버 시작 (macOS)
brew services start postgresql@15

# 또는 (Linux)
sudo systemctl start postgresql

# 데이터베이스 생성
createdb jackpy

# 연결 테스트
psql jackpy -c "SELECT version();"
```

---

## 🎯 로컬 실행 (3단계)

### 1단계: 가상환경 생성 및 의존성 설치

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r infra/requirements.txt
```

### 2단계: 데이터베이스 초기화

```bash
# Python에서 테이블 생성
python3 -c "from models import init_db; init_db()"

# 또는 Makefile 사용
make db-init
```

### 3단계: 봇 실행!

```bash
# 봇 시작
python3 -m bot.main

# 또는 Makefile 사용
make run
```

---

## 📱 텔레그램에서 테스트

봇이 실행되면 텔레그램에서 다음을 테스트하세요:

### 기본 명령어
```
/start      - 봇 시작 (자동으로 $1,000 지급됨)
/help       - 도움말
/my         - 내 프로필
```

### 게임 테스트
```
/deal 100   - $100 베팅으로 블랙잭 시작
/hit        - 카드 한 장 더
/stand      - 멈춤
/double     - 더블 다운 (첫 두 장)
/surrender  - 서렌더 (베팅액 절반 회수)
/split      - 스플릿 (같은 랭크 2장)
/wallet     - 잔액 확인
/daily      - 일일 보상 ($200)
```

### 관리자 명령어 (당신만 사용 가능)
```
/admin pending  - 승인 대기 목록
/admin stats    - 전체 통계
```

---

## 🛠️ 개발 도구 (Makefile)

편리한 개발을 위한 명령어들:

```bash
# 의존성 설치
make install

# 테스트 실행
make test

# 코드 린팅
make lint

# 코드 포맷팅
make format

# 봇 실행
make run

# 임시 파일 정리
make clean

# 데이터베이스 초기화
make db-init

# 마이그레이션 생성
make db-migrate msg="Add new field"

# 마이그레이션 적용
make db-upgrade
```

---

## 🐛 문제 해결

### 문제: PostgreSQL 연결 오류

```bash
# PostgreSQL이 실행 중인지 확인
psql -l

# 실행되지 않으면 시작
brew services start postgresql@15  # macOS
sudo systemctl start postgresql    # Linux
```

### 문제: 모듈을 찾을 수 없음

```bash
# 가상환경이 활성화되었는지 확인
which python3  # venv 경로가 표시되어야 함

# 의존성 재설치
pip install -r infra/requirements.txt
```

### 문제: 텔레그램 봇이 응답하지 않음

1. `.env` 파일의 `TELEGRAM_TOKEN`이 올바른지 확인
2. 봇 로그 확인: `tail -f jackpy.log`
3. 텔레그램에서 봇을 차단하지 않았는지 확인

---

## 📊 로그 확인

```bash
# 실시간 로그 보기
tail -f jackpy.log

# 에러 로그만 보기
grep ERROR jackpy.log

# 최근 100줄 보기
tail -n 100 jackpy.log
```

---

## 🎮 첫 게임 플레이 시나리오

1. **봇 시작**
   ```
   /start
   ```
   → 환영 메시지와 $1,000 지급

2. **첫 게임**
   ```
   /deal 50
   ```
   → 블랙잭 게임 시작

3. **카드 추가 또는 멈춤**
   ```
   /hit    (카드가 더 필요하면)
   /stand  (현재 패로 승부)
   ```

4. **결과 확인**
   → 자동으로 결과 표시 및 정산

5. **잔액 확인**
   ```
   /wallet
   ```

6. **프로필 보기**
   ```
   /my
   ```

---

## 💡 다음 단계

### 개발 모드
- 코드 수정 후 봇 재시작: `Ctrl+C` → `make run`
- 테스트 작성: `tests/` 디렉토리
- 새 기능 추가: `bot/handlers/` 디렉토리

### 프로덕션 배포
- `README.md`의 "배포 가이드" 섹션 참고
- Ubuntu 서버 + systemd 설정
- GitHub Actions로 자동 배포

---

## 📞 지원

문제가 발생하면:
1. `jackpy.log` 파일 확인
2. GitHub Issues에 문의
3. README.md의 자세한 문서 참고

---

## 🎉 준비 완료!

모든 설정이 완료되었습니다. 이제 다음 명령어로 봇을 시작하세요:

```bash
source venv/bin/activate
make run
```

텔레그램에서 `/start` 명령어를 입력하면 봇이 응답할 것입니다!

**행운을 빕니다! 🎰**
