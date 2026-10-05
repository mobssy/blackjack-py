"""
JackPy - 사용자 자동 등록 미들웨어 테스트
첫 접속 시 텔레그램 앱 언어로 기본 언어를 정하는지 확인
"""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.middleware import auth
from bot.utils.i18n import lang_from_telegram
from models.base import Base
from models.user import User


@pytest.fixture
def db_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    @contextmanager
    def fake_get_db():
        yield session

    monkeypatch.setattr(auth, "get_db", fake_get_db)
    return session


def _message_from(user_id: int, language_code):
    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=user_id,
            username="neo",
            first_name="Neo",
            language_code=language_code,
        )
    )
    context = SimpleNamespace(user_data={})
    asyncio.run(auth.user_middleware(update, context))


def _language_of(session, user_id: int) -> str:
    return session.query(User).filter(User.tg_user_id == user_id).one().language


class TestLangFromTelegram:
    @pytest.mark.parametrize("code", ["ko", "ko-KR", "KO"])
    def test_korean_app_is_ko(self, code):
        assert lang_from_telegram(code) == "ko"

    @pytest.mark.parametrize("code", ["en", "en-US", "ja", "pt-br", "zh-hans"])
    def test_other_languages_fall_back_to_en(self, code):
        assert lang_from_telegram(code) == "en"

    @pytest.mark.parametrize("code", [None, ""])
    def test_missing_code_is_bot_default_ko(self, code):
        assert lang_from_telegram(code) == "ko"


class TestUserMiddlewareLanguage:
    def test_new_user_gets_telegram_language(self, db_session):
        _message_from(1, "en-US")
        _message_from(2, "ko")
        _message_from(3, None)
        assert _language_of(db_session, 1) == "en"
        assert _language_of(db_session, 2) == "ko"
        assert _language_of(db_session, 3) == "ko"

    def test_existing_user_language_is_not_overwritten(self, db_session):
        # 이미 /start에서 언어를 고른 사용자는 앱 언어가 달라도 유지
        db_session.add(User.create_new(1, "neo", "Neo", language="ko"))
        db_session.commit()
        _message_from(1, "en")
        assert _language_of(db_session, 1) == "ko"
