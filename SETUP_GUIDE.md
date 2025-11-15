# JackPy - 설치 및 실행 가이드

## 🚀 빠른 시작

### 1. 필수 패키지 설치

```bash
cd /Users/davidsong/Desktop/jackpy

# 가상환경 활성화 (이미 생성되어 있음)
source venv/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt
```

### 2. 카드 이미지 다운로드

```bash
# 무료 오픈소스 카드 이미지 다운로드 (약 1-2분 소요)
python scripts/download_cards.py
```

이 스크립트는 52장의 카드 + 뒷면 이미지를 다운로드합니다.

### 3. 환경 변수 설정

`.env` 파일에 텔레그램 봇 토큰 설정:

```bash
TELEGRAM_TOKEN=your_telegram_bot_token_here
DATABASE_URL=sqlite:///jackpy.db
```

### 4. 데이터베이스 초기화

```bash
# 데이터베이스 마이그레이션
alembic upgrade head
```

### 5. 봇 실행

```bash
python -m bot.main
```

## 🎨 새로운 기능 확인

### 테마 시스템

봇이 실행되면 사용자의 플랜에 따라 자동으로 테마가 적용됩니다:

- **무료 사용자**: 🟢 Classic 테마 (전통적인 카지노 그린)
- **VIP 사용자**: 🌑 Dark 테마 (세련된 다크 모드)
- **비즈니스 그룹**: 💎 Luxury 테마 (프리미엄 골드)

### 게임 플레이

```
/deal 100     # 게임 시작 - 개선된 카드 이미지와 테마 적용!
/hit          # 카드 추가
/stand        # 멈춤 및 결과 확인
```

### 결과 확인

게임 종료 시 다음과 같은 개선된 결과를 볼 수 있습니다:

```
━━━━━━━━━━━━━━━━━━━━
🏆 게임 결과: 승리했습니다! 🏆
━━━━━━━━━━━━━━━━━━━━

🎯 플레이어: 20
🤖 딜러: 18

💰 베팅 금액: $100.00
💵 정산 금액: +$100.00
💳 현재 잔액: $1,200.00
━━━━━━━━━━━━━━━━━━━━
```

## 🧪 테스트 (선택사항)

### 기능 테스트 실행

```bash
# 개선된 기능 테스트
python scripts/test_features.py
```

### pytest 테스트 실행 (pytest 설치 시)

```bash
# 모든 테스트 실행
pytest tests/ -v

# 특정 테스트만 실행
pytest tests/test_themes.py -v
pytest tests/test_enhanced_card_image.py -v
```

## 📦 패키지 구조

```
jackpy/
├── assets/
│   ├── cards/              # 카드 이미지 (다운로드 후 생성됨)
│   │   ├── ace_of_spades.png
│   │   ├── king_of_hearts.png
│   │   ├── ...
│   │   └── back.png
│   └── themes/             # 테마 리소스
├── bot/
│   ├── handlers/
│   │   ├── blackjack.py    # 개선된 블랙잭 핸들러
│   │   ├── profile.py
│   │   ├── admin.py
│   │   └── vip.py
│   ├── utils/
│   │   ├── themes.py               # 테마 시스템
│   │   ├── enhanced_card_image.py  # 개선된 카드 이미지
│   │   ├── card_animation.py       # 애니메이션
│   │   ├── card_image.py           # 기존 카드 (폴백)
│   │   ├── deck.py
│   │   ├── payouts.py
│   │   └── ads.py
│   └── main.py
├── models/
├── scripts/
│   ├── download_cards.py   # 카드 다운로드 스크립트
│   └── test_features.py    # 기능 테스트 스크립트
├── tests/
│   ├── test_themes.py
│   └── test_enhanced_card_image.py
├── requirements.txt        # 의존성 목록
├── ENHANCED_FEATURES.md    # 개선된 기능 문서
└── SETUP_GUIDE.md         # 이 파일
```

## 🔧 문제 해결

### 카드 이미지가 표시되지 않는 경우

1. 카드 이미지 다운로드 확인:
   ```bash
   python scripts/download_cards.py
   ```

2. assets/cards 폴더 확인:
   ```bash
   ls assets/cards/
   # 53개 파일이 있어야 함 (52장 + back.png)
   ```

3. Pillow 설치 확인:
   ```bash
   pip install --upgrade Pillow
   ```

### 테마가 적용되지 않는 경우

1. 사용자 VIP 상태 확인:
   ```
   /my
   ```

2. 그룹 플랜 확인:
   ```
   /admin
   ```

3. 봇 재시작:
   ```bash
   # Ctrl+C로 중지 후
   python -m bot.main
   ```

### 데이터베이스 오류

```bash
# 데이터베이스 초기화
python -c "from models import drop_db, init_db; drop_db(); init_db()"

# 또는 마이그레이션
alembic downgrade base
alembic upgrade head
```

## 🎯 다음 단계

### 1. VIP 테스트

VIP 사용자로 테스트하려면:

```bash
# 데이터베이스에서 직접 VIP 활성화
python -c "
from models import get_db, User
with get_db() as db:
    user = db.query(User).filter(User.tg_user_id == YOUR_TELEGRAM_ID).first()
    if user:
        user.activate_vip(days=30)
        db.commit()
        print('VIP 활성화 완료!')
"
```

### 2. 비즈니스 플랜 테스트

그룹에서 비즈니스 플랜을 테스트하려면:

```bash
# 관리자 명령어 사용
/approve_business CHAT_ID
```

### 3. 애니메이션 테스트 (선택사항)

카드 애니메이션을 직접 테스트하려면:

```python
from bot.utils.card_animation import get_animation_generator
from io import BytesIO

gen = get_animation_generator()

# 카드 뒤집기 GIF 생성
gif_bytes = gen.create_flip_animation("AS", frames=10, duration=50)

# 파일로 저장
with open("flip.gif", "wb") as f:
    f.write(gif_bytes)
```

## 📚 추가 문서

- [ENHANCED_FEATURES.md](ENHANCED_FEATURES.md) - 개선된 기능 상세 설명
- [README.md](README.md) - 프로젝트 전체 개요

## 🎉 완료!

이제 JackPy 봇이 다음과 같은 개선된 기능을 제공합니다:

- ✅ 실제 카드 이미지
- ✅ 3가지 테마 시스템 (Classic, Dark, Luxury)
- ✅ 플랜별 자동 테마 적용
- ✅ 그림자 효과와 그라데이션
- ✅ 명확한 승패 결과 표시
- ✅ 카드 애니메이션 (GIF)
- ✅ SOLID 원칙 준수

즐거운 게임 되세요! 🎰
