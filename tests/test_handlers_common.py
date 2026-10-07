"""
JackPy - 핸들러 공용 조회 테스트 (user_lang, User.find_by_tg_id)
"""

from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.handlers import common
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

    monkeypatch.setattr(common, "get_db", fake_get_db)
    return session


def test_find_by_tg_id(db_session):
    db_session.add(User.create_new(7, "neo", "Neo"))
    db_session.commit()
    assert User.find_by_tg_id(db_session, 7).username == "neo"
    assert User.find_by_tg_id(db_session, 8) is None


def test_user_lang_reads_saved_language(db_session):
    db_session.add(User.create_new(7, "neo", "Neo", language="en"))
    db_session.commit()
    assert common.user_lang(7) == "en"


def test_user_lang_defaults_to_ko_for_unknown_user(db_session):
    assert common.user_lang(999) == "ko"
