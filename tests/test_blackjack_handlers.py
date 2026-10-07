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
    return SimpleNamespace(settled=settled)


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
