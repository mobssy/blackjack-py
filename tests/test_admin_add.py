"""
관리자 /add 테스트 — 금액 검증(nan/inf/센트 미만 거부)과 username 대소문자 무시 조회,
ADMIN_IDS 파싱
"""

import asyncio
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.handlers import admin as admin_handlers
from bot.utils.i18n import t
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

    monkeypatch.setattr(admin_handlers, "get_db", fake_get_db)
    monkeypatch.setattr(admin_handlers, "is_admin", lambda user_id: user_id == 1)
    yield session
    session.close()


def _user(db, tg_user_id, username=None, wallet="100") -> User:
    user = User(
        tg_user_id=tg_user_id,
        username=username,
        wallet=Decimal(wallet),
        stats_json={},
    )
    db.add(user)
    db.commit()
    return user


def _run(args, admin_id=1, sent=None):
    replies = []

    async def reply_text(text, **kwargs):
        replies.append(text)

    async def send_message(chat_id, text, **kwargs):
        if sent is not None:
            sent.append((chat_id, text))

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=admin_id),
        message=SimpleNamespace(reply_text=reply_text),
    )
    context = SimpleNamespace(args=args, bot=SimpleNamespace(send_message=send_message))
    asyncio.run(admin_handlers.cmd_add_balance(update, context))
    return replies


class TestFindByUsername:
    def test_case_insensitive(self, db_session):
        _user(db_session, 2, username="Alice")
        assert User.find_by_username(db_session, "aLiCe").tg_user_id == 2
        assert User.find_by_username(db_session, "bob") is None


class TestAddBalance:
    def test_adds_by_username_ignoring_case(self, db_session):
        user = _user(db_session, 2, username="Alice")
        _run(["@alice", "1000"])
        assert user.wallet == Decimal("1100")

    def test_adds_by_numeric_id(self, db_session):
        user = _user(db_session, 2)
        _run(["2", "50.25"])
        assert user.wallet == Decimal("150.25")

    @pytest.mark.parametrize("amount", ["nan", "inf", "-5", "0", "0.001", "all"])
    def test_rejects_bad_amount(self, db_session, amount):
        user = _user(db_session, 2, username="Alice")
        replies = _run(["@Alice", amount])
        assert user.wallet == Decimal("100")
        assert "소수점 둘째 자리" in replies[0]

    def test_non_admin_rejected(self, db_session):
        user = _user(db_session, 2, username="Alice")
        replies = _run(["@Alice", "1000"], admin_id=2)
        assert user.wallet == Decimal("100")
        assert "관리자" in replies[0]

    def test_recipient_notified_in_own_language(self, db_session):
        user = _user(db_session, 2, username="Alice")
        user.language = "en"
        db_session.commit()
        sent = []
        _run(["@Alice", "10"], sent=sent)
        assert sent == [(2, t("add_received", "en", amount=10.0, balance=110.0))]

    def test_invalid_identifier(self, db_session):
        replies = _run(["alice", "10"])
        assert "올바른 사용자 ID" in replies[0]

    def test_unknown_user(self, db_session):
        replies = _run(["@nobody", "10"])
        assert "찾을 수 없습니다" in replies[0]


class TestParseAdminIds:
    """ADMIN_IDS 파싱 — is_admin과 관리자 메뉴가 같은 목록을 써야 함"""

    def test_spaces_after_commas(self):
        assert admin_handlers.parse_admin_ids("111, 222") == {111, 222}

    def test_ignores_blank_and_non_numeric(self):
        assert admin_handlers.parse_admin_ids(" 111 ,,abc, ") == {111}

    def test_empty(self):
        assert admin_handlers.parse_admin_ids("") == frozenset()

    def test_is_admin_matches_admin_ids(self, monkeypatch):
        ids = admin_handlers.parse_admin_ids("111, 222")
        monkeypatch.setattr(admin_handlers, "_ADMIN_IDS", ids)
        assert admin_handlers.admin_ids() == [111, 222]
        assert all(admin_handlers.is_admin(uid) for uid in admin_handlers.admin_ids())
        assert not admin_handlers.is_admin(333)
