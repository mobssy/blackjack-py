# 🎰 JackPy

**텔레그램 기반 프로덕션급 블랙잭 카지노 봇**

JackPy는 실제 상업 서비스를 목표로 개발된 텔레그램 블랙잭 게임 봇입니다.
무료/VIP/비즈니스 플랜 구조를 갖춘 수익형 커뮤니티 플랫폼입니다.

---

## 📋 목차

- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 실행](#설치-및-실행)
- [배포 가이드](#배포-가이드)
- [명령어](#명령어)
- [플랜 안내](#플랜-안내)
- [개발 가이드](#개발-가이드)
- [라이센스](#라이센스)

---

## ✨ 주요 기능

### 🎮 게임
- **블랙잭 게임**: `/deal`, `/hit`, `/stand` 명령어
- **실시간 게임**: 즉각적인 카드 딜 및 결과 정산
- **블랙잭 룰**: 3:2 배당, 딜러 17 스탠드
- **일일 보상**: `/daily` 명령어로 매일 보상 수령

### 💎 플랜 시스템
- **무료 플랜**: 기본 게임 기능, $200 일일 보상
- **VIP 플랜** ($30/월): 광고 제거, $500 일일 보상, 특별 혜택
- **비즈니스 플랜** ($500/월): 그룹 커스터마이징, 브랜딩, API 연동

### 🔐 결제 및 승인
- **수동 입금 시스템**: `/confirm` 명령어로 입금 확인 요청
- **관리자 승인**: `/approve`, `/reject` 명령어
- **VIP 자동 만료**: 스케줄러가 자동으로 만료 관리

### 📊 통계 및 프로필
- **개인 프로필**: `/my` 명령어로 상세 통계 확인
- **랭킹 시스템**: `/rank` 명령어로 순위 조회
- **게임 기록**: 모든 라운드 자동 저장

### 🛠️ 관리자 기능
- **승인 관리**: `/admin pending` 대기 목록 조회
- **통계 조회**: `/admin stats` 전체 통계
- **VIP 관리**: `/approve`, `/revoke` 명령어

---

## 🛠️ 기술 스택

### Backend
- **Python 3.11**: 최신 안정 버전
- **python-telegram-bot 20.7**: 텔레그램 봇 SDK
- **SQLAlchemy 2.0**: ORM
- **PostgreSQL 15**: 데이터베이스
- **APScheduler**: 스케줄링

### Infrastructure
- **GitHub Actions**: CI/CD
- **systemd**: 프로세스 관리
- **Alembic**: 데이터베이스 마이그레이션
- **Ubuntu 22.04**: 서버 OS

### Development
- **pytest**: 테스팅
- **flake8**: 린팅
- **black**: 코드 포맷팅

---

## 📁 프로젝트 구조

```
jackpy/
├── bot/                      # 봇 메인 코드
│   ├── handlers/             # 명령어 핸들러
│   │   ├── start.py          # /start, /help
│   │   ├── blackjack.py      # 게임 로직
│   │   ├── vip.py            # VIP/비즈니스 플랜
│   │   ├── admin.py          # 관리자 기능
│   │   └── profile.py        # 프로필/랭킹
│   ├── utils/                # 유틸리티
│   │   ├── deck.py           # 카드 덱 관리
│   │   ├── payouts.py        # 정산 로직
│   │   ├── ads.py            # 광고 시스템
│   │   └── scheduler.py      # 스케줄러
│   ├── middleware/           # 미들웨어
│   │   └── auth.py           # 인증/권한
│   └── main.py               # 메인 엔트리포인트
├── models/                   # 데이터베이스 모델
│   ├── base.py               # Base 설정
│   ├── user.py               # User 모델
│   ├── group.py              # Group 모델
│   ├── round.py              # Round 모델
│   ├── approval.py           # Approval 모델
│   └── ad_schedule.py        # AdSchedule 모델
├── infra/                    # 인프라 설정
│   ├── requirements.txt      # Python 의존성
│   ├── jackpy.service        # systemd 서비스
│   ├── alembic.ini           # Alembic 설정
│   └── alembic/              # 마이그레이션
├── .github/                  # GitHub Actions
│   └── workflows/
│       ├── ci.yml            # CI 파이프라인
│       └── deploy.yml        # 배포 파이프라인
├── tests/                    # 테스트
├── .env.example              # 환경변수 예시
└── README.md                 # 이 파일
```

---

## 🚀 설치 및 실행

### 1️⃣ 요구사항

- Python 3.11+
- PostgreSQL 15+
- Git

### 2️⃣ 로컬 개발 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/yourusername/jackpy.git
cd jackpy

# 2. 가상환경 생성 및 활성화
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r infra/requirements.txt

# 4. 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 값을 입력하세요

# 5. 데이터베이스 생성
createdb jackpy

# 6. 데이터베이스 마이그레이션
alembic -c infra/alembic.ini upgrade head

# 7. 봇 실행
python -m bot.main
```

### 3️⃣ 환경변수 설정

`.env` 파일에 다음 값을 설정하세요:

```env
# 필수 설정
TELEGRAM_TOKEN=your_bot_token_here
ADMIN_IDS=your_telegram_id
DATABASE_URL=postgresql://user:pass@localhost:5432/jackpy

# 선택 설정
BANK_ACCOUNT_INFO="국민은행 123-456-789012\n예금주: JackPy"
```

#### 텔레그램 봇 토큰 발급

1. Telegram에서 [@BotFather](https://t.me/botfather) 검색
2. `/newbot` 명령어 실행
3. 봇 이름 및 사용자명 설정
4. 발급받은 토큰을 `TELEGRAM_TOKEN`에 입력

#### 관리자 ID 확인

1. [@userinfobot](https://t.me/userinfobot)에게 메시지 전송
2. 표시된 ID를 `ADMIN_IDS`에 입력

---

## 📦 배포 가이드

### Ubuntu 22.04 서버 배포

#### 1️⃣ 서버 준비

```bash
# 필수 패키지 설치
sudo apt update
sudo apt install -y python3.11 python3.11-venv postgresql git

# 앱 사용자 생성
sudo useradd -m -s /bin/bash app

# 디렉토리 구조 생성
sudo mkdir -p /home/app/apps/jackpy/{current,releases,shared/{logs,venv}}
sudo chown -R app:app /home/app/apps
```

#### 2️⃣ PostgreSQL 설정

```bash
# PostgreSQL 사용자 및 데이터베이스 생성
sudo -u postgres psql
CREATE DATABASE jackpy;
CREATE USER jackpy_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE jackpy TO jackpy_user;
\q
```

#### 3️⃣ 환경변수 설정

```bash
# .env 파일 생성
sudo -u app nano /home/app/apps/jackpy/shared/.env
# 위에서 설명한 환경변수를 입력
```

#### 4️⃣ systemd 서비스 설정

```bash
# 서비스 파일 복사
sudo cp infra/jackpy.service /etc/systemd/system/

# 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable jackpy
sudo systemctl start jackpy

# 상태 확인
sudo systemctl status jackpy
```

#### 5️⃣ GitHub Actions 설정

GitHub 저장소 Settings > Secrets and variables > Actions에서 다음 시크릿 추가:

- `SSH_HOST`: 서버 IP 또는 도메인
- `SSH_USER`: SSH 사용자명 (예: app)
- `SSH_KEY`: SSH 프라이빗 키
- `SSH_PORT`: SSH 포트 (기본 22)

---

## 📚 명령어

### 🎮 게임 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/deal [금액]` | 블랙잭 게임 시작 | `/deal 100` |
| `/hit` | 카드 한 장 추가 | `/hit` |
| `/stand` | 멈춤 (딜러 차례) | `/stand` |
| `/wallet` | 잔액 확인 | `/wallet` |
| `/daily` | 일일 보상 받기 | `/daily` |
| `/rank` | 랭킹 조회 | `/rank` |

### 👤 사용자 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/start` | 봇 시작 및 플랜 안내 | `/start` |
| `/my` | 내 프로필 카드 | `/my` |
| `/help` | 도움말 | `/help` |
| `/stats` | 상세 통계 | `/stats` |

### 💎 VIP 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/vip` | VIP 플랜 안내 | `/vip` |
| `/confirm [입금자명] [금액] [기간]` | VIP 입금 확인 | `/confirm 홍길동 30 30` |

### 🏢 비즈니스 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/business` | 비즈니스 플랜 안내 | `/business` |
| `/confirm_business [입금자명] [금액]` | 비즈니스 입금 확인 | `/confirm_business 회사명 500` |

### 🔧 관리자 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/admin pending` | 승인 대기 목록 | `/admin pending` |
| `/admin stats` | 전체 통계 | `/admin stats` |
| `/approve [user_id] [days]` | VIP 승인 | `/approve 123456789 30` |
| `/approve_business [user_id] [chat_id]` | 비즈니스 승인 | `/approve_business 123456789 -100123456789` |
| `/reject [user_id] [사유]` | 승인 거절 | `/reject 123456789 입금 확인 불가` |
| `/revoke [user_id]` | VIP 해제 | `/revoke 123456789` |

---

## 💰 플랜 안내

### 🆓 무료 플랜

- ✅ 기본 게임 기능
- ✅ 일일 보상: $200
- ⚠️ 광고 있음

### 💎 VIP 플랜

**가격**: $30/월

- ✅ 광고 없음
- ✅ 일일 보상: $500 (2.5배)
- ✅ 특별 이벤트 참여
- ✅ 우선 지원

### 🏢 비즈니스 플랜

**가격**: $500/월 (그룹 전용)

- ✅ 완전한 브랜딩 커스터마이징
- ✅ 커스텀 로고 및 테마
- ✅ 광고 완전 제거
- ✅ 명령어 prefix 변경
- ✅ "JackPy Partner" 뱃지
- ✅ API/Webhook 연동
- ✅ 전담 지원

---

## 🧪 개발 가이드

### 테스트 실행

```bash
# 전체 테스트
pytest

# 커버리지 포함
pytest --cov=bot --cov=models --cov-report=html

# 특정 파일만
pytest tests/test_blackjack.py -v
```

### 코드 품질 검사

```bash
# Linting
flake8 bot/ models/

# Formatting
black bot/ models/

# Type checking (선택)
mypy bot/ models/
```

### 데이터베이스 마이그레이션

```bash
# 새 마이그레이션 생성
alembic -c infra/alembic.ini revision --autogenerate -m "migration description"

# 마이그레이션 실행
alembic -c infra/alembic.ini upgrade head

# 롤백
alembic -c infra/alembic.ini downgrade -1
```

### 로그 확인

```bash
# systemd 로그
sudo journalctl -u jackpy -f

# 애플리케이션 로그
tail -f /home/app/apps/jackpy/shared/logs/out.log
tail -f /home/app/apps/jackpy/shared/logs/err.log
```

---

## 🏗️ 아키텍처

### SOLID 원칙 적용

JackPy는 SOLID 설계 원칙을 철저히 따릅니다:

- **Single Responsibility**: 각 클래스/함수는 단일 책임
- **Open/Closed**: 확장에는 열려있고 수정에는 닫혀있음
- **Liskov Substitution**: 서브타입은 기본 타입으로 대체 가능
- **Interface Segregation**: 필요한 메서드만 인터페이스에 포함
- **Dependency Inversion**: 추상화에 의존, 구체화에 의존하지 않음

### 데이터베이스 스키마

```
users
├── id (PK)
├── tg_user_id (unique)
├── username
├── wallet
├── is_vip
└── vip_expires_at

groups
├── id (PK)
├── chat_id (unique)
├── plan (FREE/VIP/BUSINESS)
└── expires_at

rounds
├── id (PK)
├── user_id (FK)
├── bet
├── player_hand (JSON)
├── dealer_hand (JSON)
└── outcome
```

---

## 🔒 보안

- **환경변수**: 민감 정보는 `.env`에 저장
- **SQL Injection 방지**: ORM 사용
- **권한 검증**: 관리자 명령어 권한 체크
- **입력 검증**: 모든 사용자 입력 검증

---

## 📝 라이센스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

## 🤝 기여

기여는 언제나 환영합니다!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📞 문의

- **이메일**: support@jackpy.com
- **텔레그램**: [@jackpy_support](https://t.me/jackpy_support)
- **이슈**: [GitHub Issues](https://github.com/yourusername/jackpy/issues)

---

## 🙏 감사의 말

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [APScheduler](https://apscheduler.readthedocs.io/)

---

<div align="center">

**Made with ❤️ by JackPy Team**

[⬆ 맨 위로 이동](#-jackpy)

</div>
