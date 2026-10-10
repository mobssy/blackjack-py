"""
1인 게임 핸들러 테스트
- 명령어/버튼이 같은 액션 로직을 쓰고 응답 방식만 다른지
- 버튼 콜백 동시 실행(block=False) 시 사용자 잠금으로 직렬화되는지
  (연타로 인한 이중 정산 방지, 다른 사용자는 HIT 연출을 기다리지 않음)
"""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.handlers import blackjack as bj
from bot.handlers import common
from bot.utils.blackjack_game import BlackjackGame
from bot.utils.deck import Deck
from bot.utils.i18n import t
from models.base import Base
from models.user import User


@pytest.fixture
def env(monkeypatch):
    """인메모리 DB + 렌더링/정산/영속화 스텁"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    for uid in (1, 2):
        session.add(User.create_new(uid, None, f"U{uid}"))
    session.commit()

    @contextmanager
    def fake_get_db():
        yield session

    settled = []

    def fake_settle(user_tg_id, game, results, chat_id):
        settled.append(user_tg_id)
        return {"wallet": 0.0}

    monkeypatch.setattr(bj, "get_db", fake_get_db)
    monkeypatch.setattr(common, "get_db", fake_get_db)  # user_lang
    monkeypatch.setattr(bj, "save_sessions", lambda sessions: None)
    monkeypatch.setattr(bj, "settle_game", fake_settle)
    monkeypatch.setattr(bj, "_render_game_image", lambda *a, **k: b"img")
    monkeypatch.setattr(
        bj, "_render_game_result", lambda *a, **k: (b"img", "result", None)
    )
    monkeypatch.setattr(bj, "HIT_REVEAL_DELAY", 0.05)
    monkeypatch.setattr(bj, "game_sessions", {})
    monkeypatch.setattr(bj, "_user_locks", {})
    return SimpleNamespace(settled=settled, session=session)


def _wallet(env, user_id: int) -> float:
    return float(User.find_by_tg_id(env.session, user_id).wallet)


def _start_game(user_id: int) -> BlackjackGame:
    game = BlackjackGame(user_id, 10.0)
    game.hands[0] = ["2S", "3H"]  # 히트해도 버스트하지 않는 핸드
    game.dealer_hand[:] = ["9C", "7D"]
    bj.game_sessions[user_id] = game
    return game


def _callback(user_id: int, data: str, log: list):
    async def answer(*args, **kwargs):
        pass

    async def edit_message_media(media, reply_markup=None):
        log.append((user_id, "media", media.caption))

    async def edit_message_caption(caption, reply_markup=None):
        log.append((user_id, "caption", caption))

    async def reply_text(text, **kwargs):
        log.append((user_id, "notice", text))

    query = SimpleNamespace(
        data=data,
        answer=answer,
        edit_message_media=edit_message_media,
        edit_message_caption=edit_message_caption,
        message=SimpleNamespace(reply_text=reply_text),
    )
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=user_id),
        callback_query=query,
    )


def _command(user_id: int, log: list):
    async def reply_photo(photo, caption, reply_markup=None):
        log.append((user_id, "photo", caption))

    async def reply_text(text, reply_markup=None):
        log.append((user_id, "text", text))

    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=user_id),
        message=SimpleNamespace(reply_photo=reply_photo, reply_text=reply_text),
    )


def _press(update):
    return bj.game_button_callback(update, None)


class TestViews:
    def test_command_stand_sends_new_photo(self, env):
        _start_game(1)
        log = []
        asyncio.run(bj.cmd_stand(_command(1, log), None))
        assert log == [(1, "photo", "result")]
        assert env.settled == [1]
        assert 1 not in bj.game_sessions

    def test_button_stand_edits_message(self, env):
        _start_game(1)
        log = []
        asyncio.run(_press(_callback(1, "game_stand", log)))
        assert log == [(1, "media", "result")]
        assert env.settled == [1]

    def test_no_game_command_vs_button(self, env):
        log = []
        asyncio.run(bj.cmd_hit(_command(1, log), None))
        asyncio.run(_press(_callback(1, "game_hit", log)))
        no_game = t("no_game", "ko")
        assert log == [(1, "text", no_game), (1, "caption", no_game)]

    def test_button_hit_animates_then_reveals(self, env):
        game = _start_game(1)
        log = []
        asyncio.run(_press(_callback(1, "game_hit", log)))
        assert log == [
            (1, "media", t("drawing_card", "ko")),
            (1, "media", t("card_drawn", "ko")),
        ]
        assert len(game.player_hand) == 3

    def test_unknown_button_ignored(self, env):
        _start_game(1)
        log = []
        asyncio.run(_press(_callback(1, "game_bogus", log)))
        assert log == []
        assert 1 in bj.game_sessions


class TestConcurrency:
    def test_double_click_stand_settles_once(self, env):
        """같은 사용자의 STAND 연타가 동시에 실행돼도 정산은 한 번"""
        _start_game(1)
        log = []

        async def run():
            await asyncio.gather(
                _press(_callback(1, "game_stand", log)),
                _press(_callback(1, "game_stand", log)),
            )

        asyncio.run(run())
        assert env.settled == [1]
        assert log == [(1, "media", "result"), (1, "caption", t("no_game", "ko"))]

    def test_command_waits_for_button_animation(self, env):
        """HIT 연출 중 들어온 같은 사용자의 /stand는 HIT가 끝난 뒤 처리"""
        game = _start_game(1)
        log = []

        async def run():
            hit = asyncio.create_task(_press(_callback(1, "game_hit", log)))
            await asyncio.sleep(0)  # HIT가 잠금을 잡고 연출에 들어가도록
            await bj.cmd_stand(_command(1, log), None)
            await hit

        asyncio.run(run())
        assert len(game.player_hand) == 3  # HIT의 카드가 정산 전에 반영됨
        assert [entry[1] for entry in log] == ["media", "media", "photo"]
        assert env.settled == [1]

    def test_other_user_not_blocked_by_animation(self, env):
        """한 사용자의 HIT 연출 동안 다른 사용자의 액션은 기다리지 않음"""
        _start_game(1)
        _start_game(2)
        log = []

        async def run():
            await asyncio.gather(
                _press(_callback(1, "game_hit", log)),
                _press(_callback(2, "game_stand", log)),
            )

        asyncio.run(run())
        # 사용자 2의 결과가 사용자 1의 카드 공개보다 먼저 전송됨
        assert log.index((2, "media", "result")) < log.index(
            (1, "media", t("card_drawn", "ko"))
        )


class TestDealerPeek:
    """딜러 피크 — 업카드 10점 카드는 딜 직후, A는 인슈어런스 결정 후 공개"""

    @staticmethod
    def _rig_deck(monkeypatch, draw_order):
        """/deal이 만드는 게임의 덱을 draw_order 순서로 고정 (플레이어 2장 → 딜러 2장)"""

        def factory(user_id, bet):
            deck = Deck(num_decks=1)
            deck.cards = ["9C"] * 20 + list(reversed(draw_order))
            return BlackjackGame(user_id, bet, deck=deck)

        monkeypatch.setattr(bj, "BlackjackGame", factory)

    @staticmethod
    def _deal(user_id: int, log: list):
        update = _command(user_id, log)
        update.effective_chat.type = "private"
        asyncio.run(bj.cmd_deal(update, SimpleNamespace(args=["10"], bot=None)))

    @staticmethod
    def _peek_caption(lang: str = "ko") -> str:
        return f"{t('dealer_peek_blackjack', lang)}\nresult"

    def test_ten_upcard_blackjack_ends_at_deal(self, env, monkeypatch):
        self._rig_deck(monkeypatch, ["8S", "7H", "AS", "KH"])  # 딜러 홀 A, 업 K
        log = []
        self._deal(1, log)
        assert log == [(1, "photo", self._peek_caption())]
        assert env.settled == [1]
        assert 1 not in bj.game_sessions

    def test_ace_upcard_waits_for_insurance_decision(self, env, monkeypatch):
        self._rig_deck(monkeypatch, ["8S", "7H", "KS", "AH"])  # 딜러 홀 K, 업 A
        log = []
        self._deal(1, log)
        assert log == [(1, "photo", t("deal_caption", "ko", bet=10.0))]
        assert env.settled == []

    def test_declining_insurance_reveals_blackjack(self, env):
        game = _start_game(1)
        game.dealer_hand[:] = ["KS", "AH"]
        log = []
        asyncio.run(_press(_callback(1, "game_hit", log)))
        assert log == [(1, "media", self._peek_caption())]
        assert len(game.player_hand) == 2  # 히트 카드를 받기 전에 끝남
        assert env.settled == [1]

    def test_double_not_charged_against_blackjack(self, env):
        game = _start_game(1)
        game.dealer_hand[:] = ["KS", "AH"]
        wallet_before = _wallet(env, 1)
        log = []
        asyncio.run(_press(_callback(1, "game_double", log)))
        assert log == [(1, "media", self._peek_caption())]
        assert game.total_bet == 10.0
        assert _wallet(env, 1) == wallet_before  # 더블 추가 베팅 차감 없음

    def test_insurance_then_blackjack_ends_round(self, env):
        game = _start_game(1)
        game.dealer_hand[:] = ["KS", "AH"]
        log = []
        asyncio.run(_press(_callback(1, "game_insurance", log)))
        assert log == [(1, "media", self._peek_caption())]
        assert game.insurance_bet == 5.0
        assert env.settled == [1]

    def test_ace_upcard_without_blackjack_plays_on(self, env):
        game = _start_game(1)
        game.dealer_hand[:] = ["9S", "AH"]
        log = []
        asyncio.run(_press(_callback(1, "game_hit", log)))
        assert log[-1] == (1, "media", t("card_drawn", "ko"))
        assert len(game.player_hand) == 3
        assert env.settled == []
