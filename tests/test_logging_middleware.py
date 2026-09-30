"""
JackPy - 로깅 미들웨어 테스트
일반 대화 내용은 기록하지 않고 명령어만 기록하는지 검증 (개인정보 보호)
"""

import asyncio
import logging
from types import SimpleNamespace

from bot.middleware.auth import logging_middleware


def _update(text, chat_id=-100, user_id=7):
    return SimpleNamespace(
        message=SimpleNamespace(text=text) if text is not None else None,
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
    )


def _logged(caplog, update) -> str:
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="bot.middleware.auth"):
        asyncio.run(logging_middleware(update, None))
    return caplog.text


class TestLoggingMiddleware:
    def test_command_is_logged(self, caplog):
        text = _logged(caplog, _update("/join 100"))
        assert "Command: user=7, chat=-100, text=/join 100" in text

    def test_plain_chat_is_not_logged(self, caplog):
        text = _logged(caplog, _update("오늘 저녁 뭐 먹지? 비밀번호는 1234"))
        assert text == ""

    def test_no_message(self, caplog):
        assert _logged(caplog, _update(None)) == ""
