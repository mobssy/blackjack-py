# JackPy - Telegram Blackjack Bot

텔레그램 블랙잭 봇. Python 3.12 + python-telegram-bot 20.7 + SQLAlchemy 2.0 + Pillow.

## 아키텍처

- `bot/main.py` — 봇 진입점 (핸들러 등록, 로깅, 스케줄러)
- `bot/handlers/` — 텔레그램 명령어/콜백 핸들러
  - `blackjack.py` — /deal /hit /stand /double /surrender /split /insurance
    /wallet /daily (출석 스트릭·파산 구제 포함), 게임 버튼 콜백,
    정산(`_settle_game`)과 렌더링(`_render_game_result`) 분리 구조
  - `profile.py` — /my /rank(그룹에서는 그룹별 랭킹) /stats /history
  - `start.py` — /start /help, 언어 선택, 메뉴 버튼 콜백 라우팅 (game_* 콜백은
    blackjack.game_button_callback으로 위임)
- `bot/utils/` — 텔레그램 의존성 없는 로직
  - `blackjack_game.py` — BlackjackGame (멀티 핸드: hands/bets 리스트,
    player_hand/bet은 활성 핸드 프로퍼티)
  - `deck.py` — 카드/덱/핸드 계산, `payouts.py` — 배당 계산 및 결과 판정
  - `i18n.py` — ko/en 문자열, `t(key, lang, **kwargs)`. 키는 반드시 양쪽 언어에 추가
  - `casino_card_renderer.py` — 게임 이미지 렌더러 (유일한 렌더러)
  - `rewards.py` — 일일 보상 출석 스트릭 / 파산 구제 계산 (상태는 User.stats_json의
    daily_streak, last_rescue_at 키에 저장 — 컬럼 추가 마이그레이션 회피)
  - `session_store.py` — 게임 세션 JSON 영속화 (game_sessions.json, gitignore됨)
- `models/` — SQLAlchemy 모델 (User, Group, GroupMember, Round, Approval, AdSchedule).
  DB는 `DATABASE_URL` 환경변수 (기본 sqlite:///./jackpy.db), `init_db()`로 create_all
- 미들웨어(`bot/middleware/auth.py`)는 각각 다른 handler group(-3/-2/-1)에 등록해야
  함 — PTB는 같은 group에서 첫 매칭 핸들러 하나만 실행

## 주의사항

- **게임 세션**: 메모리 dict + JSON 영속화. 상태 변이 시 `_persist_sessions()` 호출
  필수 (새 변이 지점 추가 시 누락 주의). 재시작 시 module import에서 자동 복원
- **정산 순서 불변식**: DB 정산 커밋 → 세션 pop → 메시지 전송.
  전송 실패 시에도 이중 정산이 없도록 이 순서를 유지할 것
- DateTime 컬럼은 naive로 저장됨 — aware datetime과 비교 시 UTC 간주 변환 필요
  (`User.is_vip_active` 참고)
- 사용자에게 보이는 문자열은 하드코딩 금지, `i18n.py`의 `t()` 사용

## 개발 명령어

```bash
./venv/bin/python -m pytest tests/ -q          # 테스트
./venv/bin/python -m black bot/ models/ tests/ scripts/   # 포맷 (CI에서 --check)
# 주의: black은 CI에 고정된 23.11.0을 사용할 것 — 버전이 다르면 포맷 결과가 달라 CI 실패
./venv/bin/python -m flake8 bot/ models/ tests/ scripts/ --select=E9,F63,F7,F82
./venv/bin/python -m bot.main                   # 봇 실행 (.env에 TELEGRAM_TOKEN 필요)
```

## 컨벤션

- 커밋: 한국어 conventional commits (feat:/fix:/chore:), main에 직접 커밋 후 즉시 push
- CI (.github/workflows/ci.yml): flake8 에러 레벨 + black --check + pytest —
  커밋 전 세 가지 모두 로컬에서 통과 확인
- 의존성: `infra/requirements.txt`(CI/프로덕션)와 `requirements.txt`(루트) 동기화 유지
