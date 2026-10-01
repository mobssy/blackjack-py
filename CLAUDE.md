# JackPy - Telegram Blackjack Bot

클럽하우스에서 모인 사람들이 텔레그램 그룹에서 같이 하는 블랙잭 게임 봇
(수익화 없는 순수 게임 — VIP/구독/광고 기능 추가하지 말 것). Python 3.12 + python-telegram-bot 20.7 + SQLAlchemy 2.0 + Pillow.

## 아키텍처

- `bot/main.py` — 봇 진입점 (핸들러 등록, 로깅, 테이블 재개·메뉴 동기화)
- `bot/handlers/` — 텔레그램 명령어/콜백 핸들러
  - `blackjack.py` — /deal /hit /stand /double /surrender /split /insurance
    /wallet /daily (출석 스트릭·파산 구제 포함), 게임 버튼 콜백.
    액션 로직(`_act_*`)은 명령어/버튼 공용이고 응답 방식만 `CommandView`(새 메시지)/
    `CallbackView`(메시지 수정)로 다름. game_* 버튼은 block=False로 동시 실행되므로
    1인 게임 상태 변경은 반드시 `_user_lock` 안에서 할 것 (연타 이중 정산 방지)
  - `table.py` — 그룹 멀티 테이블 /table /join /leave, tbl_* 버튼 콜백.
    채팅방별 asyncio.Lock으로 상태 변경 직렬화, 베팅 마감/턴 타임아웃은 asyncio 태스크
    (재시작 시 post_init의 `resume_tables`가 메시지·타이머 재개)
    채팅방엔 테이블 메시지를 하나만 유지 — 새 메시지 전송 후 `_retire_message`로 이전 것 삭제
    (착석/퇴장도 별도 안내 없이 현황 메시지를 다시 올림). 카드·합계는 이미지에만, 캡션은 짧게
  - `settlement.py` — 1인 게임/테이블 공용 DB 정산 (`apply_settlement`는 커밋 안 함 →
    테이블은 전 좌석을 한 트랜잭션으로 정산)
  - `menu.py` — 봇 시작 시 `/` 명령어 메뉴를 스코프(개인/그룹/그룹관리자/봇관리자 DM)·
    언어(ko/en)별로 동기화. 옛 목록이 남지 않도록 넓은 스코프까지 모두 덮어씀
  - `give.py` — /give 칩 선물 (@username 또는 답장으로 받는 사람 지정, 이체 규칙은
    `bot/utils/gifting.py`)
  - `profile.py` — /my /rank(그룹에서는 그룹별 랭킹) /stats /history
  - `start.py` — /start /help, 언어 선택, 메뉴 버튼 콜백 라우팅 (game_* 콜백은
    main.py에서 blackjack.game_button_callback으로 직접 등록)
- `bot/utils/` — 텔레그램 의존성 없는 로직
  - `blackjack_game.py` — BlackjackGame (멀티 핸드: hands/bets 리스트,
    player_hand/bet은 활성 핸드 프로퍼티)
  - `table.py` — BlackjackTable (좌석마다 덱/딜러 핸드를 공유하는 BlackjackGame 주입,
    공유 `dealer_hand`는 재할당 금지·제자리 변경만), `table_view.py` — 테이블 HTML 캡션
    및 이미지용 SeatView 변환, `table_renderer.py` — 딜러+좌석 그리드 이미지
    (카드/배경은 CasinoCardRenderer의 card_image/background 재사용)
  - `deck.py` — 카드/덱/핸드 계산, `payouts.py` — 배당 계산 및 결과 판정
  - `i18n.py` — ko/en 문자열, `t(key, lang, **kwargs)`. 키는 반드시 양쪽 언어에 추가
  - `casino_card_renderer.py` — 1인 게임 이미지 렌더러
  - `rewards.py` — 일일 보상 출석 스트릭 / 파산 구제 계산 (상태는 User.stats_json의
    daily_streak, last_rescue_at 키에 저장 — 컬럼 추가 마이그레이션 회피)
  - `session_store.py` — 게임 세션/멀티 테이블 JSON 영속화 (game_sessions.json,
    table_sessions.json, gitignore됨)
- `models/` — SQLAlchemy 모델 (User, Group, GroupMember, Round).
  수익화(VIP/플랜) 기능은 제거됨 — User.is_vip 등 레거시 컬럼은 기존 DB의 NOT NULL
  제약 때문에 정의만 유지 (삭제하면 신규 INSERT 실패). 운영 DB에 approvals/ad_schedules
  테이블도 남아 있지만 미사용.
  DB는 `DATABASE_URL` 환경변수 (기본 sqlite:///./jackpy.db), `init_db()`로 create_all
- `bot/middleware/rate_limit.py` — RetryAfterLimiter: 텔레그램 Flood control(429) 시
  대기 후 재시도 (Application.builder().rate_limiter로 전 요청에 적용).
  테이블은 메시지 전송이 실패해도 타이머를 finally로 예약해 라운드가 멈추지 않게 함
- 미들웨어(`bot/middleware/auth.py`)는 각각 다른 handler group(-3/-2/-1)에 등록해야
  함 — PTB는 같은 group에서 첫 매칭 핸들러 하나만 실행

## 주의사항

- **게임 세션**: 메모리 dict + JSON 영속화. 상태 변이 시 `_persist_sessions()` 호출
  필수 (새 변이 지점 추가 시 누락 주의). 재시작 시 module import에서 자동 복원
- **정산 순서 불변식**: DB 정산 커밋 → 세션 pop → 메시지 전송.
  전송 실패 시에도 이중 정산이 없도록 이 순서를 유지할 것
- DateTime 컬럼은 naive로 저장됨 — aware datetime과 비교 시 UTC 간주 변환 필요
  (`User.can_claim_daily` 참고)
- 사용자에게 보이는 문자열은 하드코딩 금지, `i18n.py`의 `t()` 사용
- **명령어 추가/삭제 시** `bot/utils/bot_commands.py` 메뉴 목록과 `cmd_desc_<명령어>`
  i18n 키도 함께 수정 (tests/test_bot_commands.py가 main.py 등록 목록과 대조해 강제)
- 텔레그램 메뉴는 BotFather에서 수정하지 말 것 — 재시작 시 코드 정의로 덮어써짐
- 문서는 README.md(한/영) 하나로 관리 — 명령어·규칙·보상 수치·파일 구조를 바꾸면
  README의 한국어/영어 섹션과 Project structure를 함께 갱신
- 라이선스: 공개 저장소지만 열람만 허용(All rights reserved, LICENSE 파일).
  서드파티 에셋(카드 이미지 MIT, Poppins OFL)은 LICENSE 하단에 명시

## 개발 명령어

```bash
./venv/bin/python -m pytest tests/ -q          # 테스트
./venv/bin/python -m black bot/ models/ tests/ scripts/   # 포맷 (CI에서 --check)
# 주의: black은 CI에 고정된 23.11.0을 사용할 것 — 버전이 다르면 포맷 결과가 달라 CI 실패
./venv/bin/python -m flake8 bot/ models/ tests/ scripts/ --select=E9,F63,F7,F82
./venv/bin/python -m bot.main                   # 봇 실행 (.env에 TELEGRAM_TOKEN 필요)
JACKPY_HOST=<IP> JACKPY_SSH_USER=<ssh계정> JACKPY_APP_USER=<봇계정> ./scripts/deploy.sh  # 운영 배포 (push 후)
```

## 컨벤션

- 커밋: 한국어 conventional commits (feat:/fix:/chore:), main에 직접 커밋 후 즉시 push
- CI (.github/workflows/ci.yml): flake8 에러 레벨 + black --check + pytest —
  커밋 전 세 가지 모두 로컬에서 통과 확인
- 의존성: `infra/requirements.txt`(CI/프로덕션)와 `requirements.txt`(루트) 동기화 유지
