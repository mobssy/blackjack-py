"""
칩 선물(/give) 테스트
- parse_give_args: 인자 형식/금액 검증
- transfer_chips: 잔액 이체 규칙 (인메모리 DB)
- cmd_give: 받는 사람 지정(@username, 답장)과 커밋
"""

import asyncio
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.handlers import give as give_handlers
from bot.utils.gifting import GiveError, parse_give_args, transfer_chips
from bot.utils.i18n import t
from models.base import Base
from models.user import User


class TestParseGiveArgs:
    @pytest.mark.parametrize(
        "args",
        [["@Alice", "100"], ["100", "@Alice"]],
    )
    def test_username_and_amount_any_order(self, args):
        request = parse_give_args(args)
        assert request.username == "Alice"
        assert request.amount == Decimal("100")

    def test_amount_only_for_reply(self):
        request = parse_give_args(["12.50"])
        assert request.username is None
        assert request.amount == Decimal("12.50")

    @pytest.mark.parametrize(
        "args",
        [[], ["@Alice"], ["@Alice", "@Bob", "10"], ["10", "20"], ["@", "10"]],
    )
    def test_bad_usage(self, args):
        with pytest.raises(GiveError) as e:
            parse_give_args(args)
        assert e.value.key == "give_usage"

    @pytest.mark.parametrize("amount", ["0", "-5", "0.5", "1.005", "abc", "nan", "all"])
    def test_bad_amount(self, amount):
        with pytest.raises(GiveError) as e:
            parse_give_args(["@Alice", amount])
        assert e.value.key == "give_invalid_amount"


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _user(db, tg_user_id, wallet, username=None, first_name=None) -> User:
    user = User(
        tg_user_id=tg_user_id,
        username=username,
        first_name=first_name,
        wallet=Decimal(wallet),
        stats_json={},
    )
    db.add(user)
    db.commit()
    return user


class TestTransferChips:
    def test_moves_chips(self, db_session):
        sender = _user(db_session, 1, "100")
        recipient = _user(db_session, 2, "5")
        transfer_chips(sender, recipient, Decimal("30.25"))
        assert sender.wallet == Decimal("69.75")
        assert recipient.wallet == Decimal("35.25")

    def test_not_enough_balance(self, db_session):
        sender = _user(db_session, 1, "10")
        recipient = _user(db_session, 2, "5")
        with pytest.raises(GiveError) as e:
            transfer_chips(sender, recipient, Decimal("10.01"))
        assert e.value.key == "give_no_balance"
        assert sender.wallet == Decimal("10")
        assert recipient.wallet == Decimal("5")

    def test_cannot_send_to_self(self, db_session):
        sender = _user(db_session, 1, "100")
        with pytest.raises(GiveError) as e:
            transfer_chips(sender, sender, Decimal("10"))
        assert e.value.key == "give_self"
        assert sender.wallet == Decimal("100")


def _update(user_id, reply_from=None):
    replies = []

    async def reply_text(text, **kwargs):
        replies.append(text)

    reply_to = SimpleNamespace(from_user=reply_from) if reply_from is not None else None
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(reply_text=reply_text, reply_to_message=reply_to),
    )
    return update, replies


class TestCmdGive:
    @pytest.fixture(autouse=True)
    def use_test_db(self, monkeypatch, db_session):
        @contextmanager
        def fake_get_db():
            yield db_session

        monkeypatch.setattr(give_handlers, "get_db", fake_get_db)

    def _run(self, update, args):
        asyncio.run(give_handlers.cmd_give(update, SimpleNamespace(args=args)))

    def test_give_by_username_case_insensitive(self, db_session):
        _user(db_session, 1, "100", first_name="David")
        _user(db_session, 2, "0", username="Alice", first_name="Alice")
        update, replies = _update(1)

        self._run(update, ["@alice", "40"])

        sender, recipient = db_session.query(User).order_by(User.tg_user_id).all()
        assert sender.wallet == Decimal("60")
        assert recipient.wallet == Decimal("40")
        assert "🎁" in replies[0]

    def test_give_by_reply(self, db_session):
        _user(db_session, 1, "100")
        _user(db_session, 2, "0")
        update, _ = _update(1, reply_from=SimpleNamespace(id=2, is_bot=False))

        self._run(update, ["15"])

        recipient = db_session.query(User).filter(User.tg_user_id == 2).one()
        assert recipient.wallet == Decimal("15")

    def test_reply_to_bot_rejected(self, db_session):
        _user(db_session, 1, "100")
        update, replies = _update(1, reply_from=SimpleNamespace(id=99, is_bot=True))

        self._run(update, ["15"])

        assert replies == [t("give_bot", "ko")]

    def test_unknown_recipient(self, db_session):
        _user(db_session, 1, "100")
        update, replies = _update(1)

        self._run(update, ["@nobody", "10"])

        assert replies == [t("give_unknown_user", "ko")]
        assert db_session.query(User).one().wallet == Decimal("100")

    def test_amount_without_recipient_shows_usage(self, db_session):
        _user(db_session, 1, "100")
        update, replies = _update(1)

        self._run(update, ["10"])

        assert replies == [t("give_usage", "ko")]
