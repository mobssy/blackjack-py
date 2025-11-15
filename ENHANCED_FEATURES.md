# JackPy - 개선된 기능 가이드

## 🎨 새로운 기능

### 1. 실제 카드 이미지 시스템
- 고품질 PNG 카드 이미지 사용
- 실감나는 그림자 효과
- 부드러운 모서리 처리

### 2. 테마 시스템
세 가지 테마가 자동으로 적용됩니다:

#### 🟢 Classic 테마 (무료 플랜)
- 전통적인 카지노 그린 테이블
- 골드 테두리
- 클래식한 분위기

#### 🌑 Dark 테마 (VIP 플랜)
- 세련된 다크 그레이 배경
- 보라색 액센트
- 현대적인 느낌
- 그라데이션 배경

#### 💎 Luxury 테마 (비즈니스 플랜)
- 딥 네이비 배경
- 골드 테두리 및 강조색
- 프리미엄 느낌
- 그라데이션 배경

### 3. 카드 애니메이션
- 카드 뒤집기 GIF 애니메이션
- 카드 딜 애니메이션
- 부드러운 전환 효과

## 📦 설치 및 설정

### 1. 카드 이미지 다운로드

```bash
cd /Users/davidsong/Desktop/jackpy
python scripts/download_cards.py
```

이 스크립트는 무료 오픈소스 카드 이미지를 다운로드합니다.

### 2. 필요한 패키지 확인

```bash
pip install Pillow requests
```

## 🎮 사용 방법

### 자동 테마 적용

테마는 사용자의 플랜에 따라 자동으로 적용됩니다:

- **무료 사용자**: Classic 테마
- **VIP 사용자**: Dark 테마
- **비즈니스 그룹**: Luxury 테마

### 게임 플레이

```
/deal 100     # 게임 시작 (테마 자동 적용)
/hit          # 카드 추가
/stand        # 멈춤 및 결과 확인
```

## 🏗️ 아키텍처

### SOLID 원칙 적용

#### Single Responsibility Principle
- `ThemeManager`: 테마 관리만 담당
- `EnhancedCardImageGenerator`: 카드 이미지 생성만 담당
- `CardAnimationGenerator`: 애니메이션 생성만 담당

#### Open/Closed Principle
- 새로운 테마 추가 시 기존 코드 수정 불필요
- `Theme` 클래스 상속으로 확장 가능

#### Liskov Substitution Principle
- `get_card_generator()`와 `get_enhanced_card_generator()` 호환
- 동일한 인터페이스 제공

#### Interface Segregation Principle
- 각 생성기는 필요한 메서드만 제공
- 불필요한 의존성 없음

#### Dependency Inversion Principle
- 핸들러는 구체적인 생성기가 아닌 추상적인 인터페이스에 의존
- 테마는 외부에서 주입 가능

## 📁 파일 구조

```
jackpy/
├── assets/
│   ├── cards/              # 카드 이미지 (52장 + 뒷면)
│   └── themes/             # 테마 관련 리소스
├── bot/
│   ├── handlers/
│   │   └── blackjack.py    # 개선된 카드 시스템 사용
│   └── utils/
│       ├── themes.py       # 테마 시스템
│       ├── enhanced_card_image.py  # 개선된 카드 이미지
│       ├── card_animation.py       # 애니메이션
│       └── card_image.py   # 기존 카드 이미지 (폴백)
└── scripts/
    └── download_cards.py   # 카드 이미지 다운로드
```

## 🎯 주요 개선사항

### 결과 표시 개선
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

### 시각적 개선
- ✅ 실제 카드 이미지 사용
- ✅ 그림자 효과
- ✅ 그라데이션 배경
- ✅ 플랜별 자동 테마
- ✅ 깔끔한 결과 표시

## 🚀 성능

### 최적화
- 카드 생성기 싱글톤 패턴 사용
- 이미지 캐싱
- 효율적인 PIL 사용

### 메모리
- 카드 이미지: ~10MB (52장)
- 생성된 게임 이미지: ~500KB per game

## 🔧 커스터마이징

### 새 테마 추가

```python
# bot/utils/themes.py에 추가

CUSTOM = Theme(
    name="Custom",
    colors=ColorScheme(
        background=(R, G, B),
        table_color=(R, G, B),
        text_color=(R, G, B),
        border_color=(R, G, B),
        accent_color=(R, G, B),
        card_shadow=(R, G, B, A)
    ),
    card_style="modern",
    font_name="Arial",
    has_gradient=True
)
```

### 애니메이션 사용 예제

```python
from bot.utils.card_animation import get_animation_generator

# 카드 뒤집기 애니메이션
anim_gen = get_animation_generator()
gif_bytes = anim_gen.create_flip_animation("AS", frames=10, duration=50)

# 전송
await update.message.reply_animation(
    animation=BytesIO(gif_bytes),
    caption="카드 뒤집기!"
)
```

## 📝 TODO (향후 개선사항)

- [ ] 사용자별 테마 선택 기능
- [ ] 더 많은 테마 추가
- [ ] 카드 애니메이션 자동 적용
- [ ] 사운드 이펙트
- [ ] 승리 시 특수 효과

## 🐛 문제 해결

### 카드 이미지가 표시되지 않는 경우
1. 카드 이미지 다운로드 확인: `python scripts/download_cards.py`
2. assets/cards 폴더 확인
3. Pillow 설치 확인: `pip install Pillow`

### 테마가 적용되지 않는 경우
1. 사용자 VIP 상태 확인: `/my`
2. 그룹 플랜 확인: `/admin`
3. 데이터베이스 재시작

## 📄 라이선스

카드 이미지: [hayeah/playing-cards-assets](https://github.com/hayeah/playing-cards-assets) (MIT License)
