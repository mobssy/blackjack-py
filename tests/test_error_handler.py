"""
전역 에러 핸들러 테스트
- 일반 예외는 사용자 언어로 안내, 텔레그램 API 오류는 기록만
- 언어 조회(DB)까지 실패해도 기본 언어로 안내
"""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from telegram import Chat, Message, Update
from telegram import User as TgUser
from telegram.error import BadRequest

from bot.handlers import errors
from bot.utils.i18n import t


@pytest.fixture
def sent(monkeypatch):
    """Message.reply_text로 보낸 문구 기록"""
    texts = []

    async def fake_reply_text(self, text, **kwargs):
        texts.append(text)

    monkeypatch.setattr(Message, "reply_text", fake_reply_text)
    return texts


def _update(with_message: bool = True) -> Update:
    if not with_message:
        return Update(update_id=7)
    message = Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=Chat(id=1, type=Chat.PRIVATE),
        from_user=TgUser(id=1, first_name="U", is_bot=False),
        text="/deal 10",
    )
    return Update(update_id=7, message=message)


def _run(update, error):
    asyncio.run(errors.error_handler(update, SimpleNamespace(error=error)))


def test_unexpected_error_notifies_user_in_their_language(monkeypatch, sent):
    monkeypatch.setattr(errors, "user_lang", lambda user_id: "en")
    _run(_update(), RuntimeError("boom"))
    assert sent == [t("error_generic", "en")]


def test_telegram_error_is_only_logged(monkeypatch, sent):
    monkeypatch.setattr(errors, "user_lang", lambda user_id: "en")
    _run(_update(), BadRequest("Message is not modified"))
    assert sent == []


def test_falls_back_to_default_language_when_lookup_fails(monkeypatch, sent):
    def broken_lookup(user_id):
        raise RuntimeError("db down")

    monkeypatch.setattr(errors, "user_lang", broken_lookup)
    _run(_update(), RuntimeError("db down"))
    assert sent == [t("error_generic", "ko")]


def test_update_without_message_is_ignored(sent):
    _run(_update(with_message=False), RuntimeError("boom"))
    assert sent == []


def test_non_update_object_is_only_logged(sent):
    _run(None, RuntimeError("job failed"))
    assert sent == []
