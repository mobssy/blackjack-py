<div align="center">
  <h1>JackPy</h1>
  <p>클럽하우스에서 모인 친구들과 텔레그램 그룹에서 같이 하는 블랙잭 봇<br/>
  A Telegram blackjack bot for playing together with friends from a Clubhouse room</p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.11%2B-black?style=flat-square&logo=python&logoColor=white" />
    <img src="https://img.shields.io/badge/python--telegram--bot-20.7-black?style=flat-square&logo=telegram&logoColor=white" />
  </p>
  <p><a href="#한국어">한국어</a> · <a href="#english">English</a></p>
</div>

---

## 한국어

### 소개

클럽하우스 음성방에서 대화하면서, 같은 텔레그램 그룹에 모여 딜러 한 명을 상대로 함께 블랙잭을 하는 봇입니다.
가상 칩으로만 플레이하며 실제 돈, 결제, 광고는 없습니다. 개인 채팅에서는 혼자 연습할 수도 있습니다.

한국어와 영어를 지원합니다. 처음엔 텔레그램 앱 언어에 맞춰지고(한국어가 아니면 영어), 개인 채팅의 `/start`에서 언제든 바꿀 수 있습니다. 그룹 테이블은 테이블을 연 사람의 언어로 진행됩니다.

### 그룹에서 같이 하기 (멀티 테이블)

1. 그룹에 봇을 초대하고 `/table` 로 테이블을 엽니다. (최대 7명)
2. 각자 `/join 100` 처럼 착석하며 베팅합니다. (`/join all` = 올인, 딜 전 `/leave` 로 퇴장·환불)
3. 테이블을 연 사람이 **딜 시작** 버튼을 누르거나, 3분이 지나면 자동으로 딜합니다.
4. 좌석 순서대로 차례가 오면 멘션 알림이 가고, 차례인 사람만 버튼(HIT / STAND / DOUBLE / SURRENDER / SPLIT / INSURANCE)을 누를 수 있습니다.
5. 30초 안에 선택하지 않으면 자동 스탠드됩니다.
6. 모두 끝나면 딜러가 플레이하고, 전원 결과와 잔액을 이미지 한 장으로 보여줍니다.
7. 결과 화면의 **같은 금액으로 계속** 버튼을 누르면 `/join` 없이 지난 판과 같은 금액으로 다음 판에 착석합니다. (누른 사람만 착석)

### 명령어

| 어디서 | 명령어 | 설명 |
|---|---|---|
| 그룹 | `/table` | 멀티 테이블 열기 (이미 있으면 현재 상태 다시 표시) |
| 그룹 | `/join [금액\|all]` | 착석 및 베팅 |
| 그룹 | `/leave` | 딜 전 퇴장 (베팅 반환) |
| 개인 채팅 | `/deal [금액\|all]` | 1인 게임 시작 |
| 개인 채팅 | `/hit` `/stand` `/double` `/surrender` `/split` `/insurance` | 1인 게임 액션 (버튼으로도 가능) |
| 어디서나 | `/wallet` | 잔액 및 통계 |
| 어디서나 | `/daily` | 일일 보상 (한국 시간 자정 리셋) |
| 어디서나 | `/give @아이디 금액` | 칩 선물 (그룹에서는 상대 메시지에 답장하며 `/give 금액`도 가능) |
| 어디서나 | `/my` `/stats` `/history` | 프로필 · 상세 통계 · 최근 게임 기록 |
| 어디서나 | `/rank` | 랭킹 (그룹에서는 그룹 멤버 랭킹) |
| 어디서나 | `/start` `/help` | 시작 메뉴 · 도움말 |
| 관리자 DM | `/admin stats` | 전체 통계 |
| 관리자 DM | `/add [user_id\|@username] [금액]` | 칩 지급 |

텔레그램 `/` 메뉴는 봇이 시작될 때 채팅 종류(개인/그룹)와 권한(관리자)에 맞게 자동으로 등록됩니다.

### 규칙

- 6덱 슈, 딜러는 16 이하와 소프트 17(A 포함 17)에서 히트, 하드 17 이상에서 스탠드
- 블랙잭 6:5 (1.2배), 일반 승리 1:1, 무승부는 베팅 반환
- 더블 다운: 첫 두 장에서 베팅 2배 + 카드 1장 후 자동 스탠드
- 서렌더: 첫 두 장에서 베팅 절반 회수
- 스플릿: 같은 랭크 2장, 1회만 가능. 에이스 스플릿은 카드 1장씩만. 스플릿 후 21은 블랙잭이 아닌 일반 21
- 인슈어런스: 딜러 업카드가 A일 때 베팅 절반, 딜러 블랙잭이면 2:1 (멀티 테이블에서는 라운드 종료 시 공개)

### 칩

- 시작 칩 $1,000, 최소 베팅 $1 (소수점 둘째 자리까지)
- 일일 보상 $200 + 연속 출석 시 하루 $25씩 추가 (최대 +$175)
- 연승 보너스: 3연승부터 승리 정산액의 +10%, 5연승부터 +20%
- 파산 구제: 잔액이 $10 미만이면 4시간마다 $50

### 직접 실행하기

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env        # TELEGRAM_TOKEN, ADMIN_IDS 입력
./venv/bin/python -m bot.main
```

- DB는 기본적으로 SQLite 파일(`jackpy.db`)이며 첫 실행 시 자동으로 만들어집니다.
- **같은 봇 토큰으로 두 곳에서 동시에 실행하지 마세요.** 텔레그램 업데이트를 서로 가져가서 충돌합니다. 개발할 때는 별도 테스트 봇 토큰을 쓰세요.
- 진행 중인 게임과 테이블은 `game_sessions.json`, `table_sessions.json`에 저장되어 재시작 후에도 이어집니다.

### 개발

```bash
./venv/bin/python -m pytest tests/ -q
./venv/bin/python -m black bot/ models/ tests/ scripts/      # CI와 같은 black 23.11.0
./venv/bin/python -m flake8 bot/ models/ tests/ scripts/ --select=E9,F63,F7,F82
```

CI(GitHub Actions)가 push마다 위 세 가지를 확인합니다.

### 서버 배포

systemd로 운영합니다 (유닛: [`infra/jackpy.service`](infra/jackpy.service)).

- **새 서버 준비 (1회):** 서버에서 [`scripts/server_setup.sh`](scripts/server_setup.sh)를 `sudo`로 실행하면 실행 계정, 코드, 가상환경, 한글 폰트, systemd 등록까지 처리합니다. 이후 `.env`에 토큰을 입력하고 시작합니다.
- **배포:** main에 push한 뒤 로컬에서 실행합니다. 서버에서 pull → (의존성 변경 시) 설치 → import 확인 → 재시작 → 기동 로그 확인까지 진행하고, 문제가 있으면 실패로 끝납니다.

```bash
JACKPY_HOST=<서버 IP> JACKPY_APP_USER=<봇 실행 계정> ./scripts/deploy.sh
```

진행 중인 게임과 테이블은 재시작 후 자동으로 복원됩니다.

---

## English

### About

A bot for playing blackjack together against one dealer in a Telegram group, while chatting in a Clubhouse voice room.
Play money only — no real money, payments, or ads. You can also practice solo in a private chat.

Korean and English are supported. Your language starts out matching your Telegram app (English for anything other than Korean) and can be changed anytime with `/start` in a private chat. A group table uses the language of the person who opened it.

### Playing together (multiplayer table)

1. Add the bot to a group and open a table with `/table` (up to 7 players).
2. Everyone takes a seat and bets, e.g. `/join 100` (`/join all` = all-in, `/leave` before the deal to get your bet back).
3. The host presses **Deal**, or dealing starts automatically after 3 minutes.
4. Players act in seat order. The current player is mentioned and only they can press the buttons (HIT / STAND / DOUBLE / SURRENDER / SPLIT / INSURANCE).
5. No choice within 30 seconds means an automatic stand.
6. When everyone is done, the dealer plays and the results and balances for every seat are shown in a single image.
7. Press **Same bet again** on the results to take a seat in the next round with the same bet, no `/join` needed (only the person who presses it is seated).

### Commands

| Where | Command | Description |
|---|---|---|
| Group | `/table` | Open a table (or re-show the current one) |
| Group | `/join [amount\|all]` | Take a seat and bet |
| Group | `/leave` | Leave before the deal (bet returned) |
| Private chat | `/deal [amount\|all]` | Start a solo game |
| Private chat | `/hit` `/stand` `/double` `/surrender` `/split` `/insurance` | Solo game actions (buttons also work) |
| Anywhere | `/wallet` | Balance and stats |
| Anywhere | `/daily` | Daily reward (resets at midnight KST) |
| Anywhere | `/give @username amount` | Send chips (in a group you can also reply to their message with `/give amount`) |
| Anywhere | `/my` `/stats` `/history` | Profile, detailed stats, recent games |
| Anywhere | `/rank` | Leaderboard (group members only when used in a group) |
| Anywhere | `/start` `/help` | Start menu, help |
| Admin DM | `/admin stats` | Global stats |
| Admin DM | `/add [user_id\|@username] [amount]` | Give chips |

The Telegram `/` menu is registered automatically on startup for each chat type (private/group) and role (admin).

### Rules

- 6-deck shoe; the dealer hits 16 or less and soft 17 (17 with an Ace), stands on hard 17+
- Blackjack pays 6:5 (1.2x), a win pays 1:1, a push returns the bet
- Double down: on the first two cards, 2x bet + one card, then auto-stand
- Surrender: on the first two cards, get half the bet back
- Split: a same-rank pair, once only. Split aces get one card each. A two-card 21 after a split is a regular 21, not blackjack
- Insurance: half the bet when the dealer shows an Ace, pays 2:1 on dealer blackjack (revealed at the end of the round at a multiplayer table)

### Chips

- Start with $1,000; minimum bet $1 (up to two decimal places)
- Daily reward $200, plus $25 per consecutive day (up to +$175)
- Win streak bonus: +10% of winnings from 3 wins in a row, +20% from 5
- Bankruptcy rescue: $50 every 4 hours when your balance is below $10

### Running it yourself

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env        # fill in TELEGRAM_TOKEN, ADMIN_IDS
./venv/bin/python -m bot.main
```

- The database defaults to a SQLite file (`jackpy.db`), created on first run.
- **Never run two instances with the same bot token** — they compete for Telegram updates and conflict. Use a separate test bot token for development.
- In-progress games and tables are saved to `game_sessions.json` and `table_sessions.json` and resume after a restart.

### Development

```bash
./venv/bin/python -m pytest tests/ -q
./venv/bin/python -m black bot/ models/ tests/ scripts/      # black 23.11.0, same as CI
./venv/bin/python -m flake8 bot/ models/ tests/ scripts/ --select=E9,F63,F7,F82
```

CI (GitHub Actions) runs these three checks on every push.

### Deployment

Runs under systemd (unit: [`infra/jackpy.service`](infra/jackpy.service)).

- **New server (once):** run [`scripts/server_setup.sh`](scripts/server_setup.sh) with `sudo` on the server. It creates the service account, clones the code, sets up the venv, installs Korean fonts, and registers the systemd unit. Then fill in `.env` and start the service.
- **Deploy:** push to main, then run the script locally. On the server it pulls, installs dependencies if they changed, checks imports, restarts, and verifies the startup log — failing loudly if anything is wrong.

```bash
JACKPY_HOST=<server IP> JACKPY_APP_USER=<service account> ./scripts/deploy.sh
```

In-progress games and tables are restored automatically after a restart.

---

## Project structure

```
bot/
  main.py              entry point: handler registration, table resume, menu sync
  handlers/            Telegram handlers
    blackjack.py       solo game, /wallet, /daily
    table.py           multiplayer table (/table /join /leave, buttons, timers)
    settlement.py      shared DB settlement for solo and table games
    menu.py            `/` command menu sync
    profile.py         /my /rank /stats /history
    start.py           /start /help, language, menu buttons
    give.py            /give chip gifts
    admin.py           /admin stats, /add
  middleware/auth.py   auto-registers users, groups, and group members
  middleware/rate_limit.py  waits and retries on Telegram flood control (429)
  utils/               Telegram-independent logic
    blackjack_game.py  hands, split, double, insurance
    table.py           multiplayer table rules and turns
    deck.py            cards and hand values
    payouts.py         payouts, outcomes, win streaks
    rewards.py         daily reward streak, bankruptcy rescue
    gifting.py         /give argument parsing and chip transfer rules
    i18n.py            Korean/English strings
    bot_commands.py    command menu definitions
    session_store.py   game/table persistence (JSON)
    game_scene.py, game_renderer.py   solo game image (felt table)
    table_view.py, table_renderer.py  multiplayer table captions and image
    felt.py            felt, chips and printed table text shared by the images
    casino_card_renderer.py, themes.py   card faces and backs
    fonts.py           Pretendard font loading
    glyph_filter.py    drops characters the font can't draw (emoji) from image text
    photo_encoding.py  encodes rendered images as JPEG for Telegram
models/                SQLAlchemy models (User, Group, GroupMember, Round)
tests/                 pytest suite
assets/                card images and fonts
infra/                 systemd unit, Alembic, production requirements
scripts/
  deploy.sh            deploy to the server (pull, check, restart, verify)
  server_setup.sh      one-time setup of a new Debian/Ubuntu server
  rebuild_stats.py     recompute game stats from round history (--dry-run)
  download_cards.py    re-download the card images
```

## Credits

- Card images: [hayeah/playing-cards-assets](https://github.com/hayeah/playing-cards-assets) (MIT), derived from Vector Playing Cards (public domain)
- Font: [Poppins](assets/fonts/Poppins/OFL.txt) (SIL Open Font License 1.1)
- Font: [Pretendard](assets/fonts/Pretendard/OFL.txt) by Kil Hyung-jin (SIL Open Font License 1.1)

## License

Copyright © 2026 David Song. All rights reserved.

이 저장소는 소스 코드를 **열람할 수 있도록** 공개되어 있으며, 열람이 사용 권한을 부여하지는 않습니다. 저작권자의 서면 허락 없이 복제·수정·배포·운영할 수 없습니다.
This repository is public so the source can be **viewed**; viewing does not grant a license to use it. See [LICENSE](LICENSE) for details and third-party asset licenses.
