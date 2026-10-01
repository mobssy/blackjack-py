"""
시작 메뉴/언어 선택 버튼 콜백 테스트 (start.button_callback)
"""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.handlers import start
from bot.utils.i18n import t
from models.base import Base
from models.user import STARTING_WALLET, User


@pytest.fixture
def db_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    @contextmanager
    def fake_get_db():
        yield session

    monkeypatch.setattr(start, "get_db", fake_get_db)
    return session


def _press(data: str, user_id: int = 7, username: str = "neo"):
    edits = []

    async def answer(*args, **kwargs):
        pass

    async def edit_message_text(text, reply_markup=None):
        edits.append(text)

    async def edit_message_caption(caption, reply_markup=None):
        edits.append(caption)

    update = SimpleNamespace(
        callback_query=SimpleNamespace(
            data=data,
            answer=answer,
            edit_message_text=edit_message_text,
            edit_message_caption=edit_message_caption,
        ),
        effective_user=SimpleNamespace(id=user_id, username=username, first_name="Neo"),
    )
    asyncio.run(start.button_callback(update, None))
    return edits


class TestLanguageSelect:
    def test_first_selection_registers_user(self, db_session):
        edits = _press("lang_en")
        user = db_session.query(User).one()
        assert user.language == "en"
        assert float(user.wallet) == STARTING_WALLET
        assert edits == [t("welcome_new", "en")]

    def test_existing_user_updates_language_and_name(self, db_session):
        db_session.add(User.create_new(7, "old", "Old", language="en"))
        db_session.commit()

        edits = _press("lang_ko", username="neo")
        user = db_session.query(User).one()
        assert user.language == "ko"
        assert user.username == "neo"
        assert edits == [t("welcome_back", "ko", name="@neo")]


class TestMenu:
    def test_profile_uses_user_language(self, db_session):
        user = User.create_new(7, "neo", "Neo", language="en")
        user.stats_json = {"total_games": 4, "wins": 1, "losses": 3}
        db_session.add(user)
        db_session.commit()

        edits = _press("my_profile")
        assert edits[0].startswith("Profile")
        assert "Win rate: 25.0%" in edits[0]

    def test_profile_unknown_user(self, db_session):
        assert _press("my_profile") == [t("deal_no_user", "ko")]

    def test_restart_edits_caption(self, db_session):
        assert _press("restart_game") == [t("start_game_msg", "ko")]

    def test_unknown_data_ignored(self, db_session):
        assert _press("something_else") == []
