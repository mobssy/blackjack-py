"""
멀티 테이블 메시지 정리 테스트
채팅방에 테이블 메시지가 하나만 남도록 새 메시지 전송 후 이전 메시지를 삭제
"""

import asyncio
from types import SimpleNamespace

import pytest
from telegram.error import BadRequest

from bot.handlers import table as table_handlers
from bot.utils.table import BlackjackTable


class _FakeBot:
    """호출 순서를 기록하는 가짜 봇"""

    def __init__(self, delete_fails=False):
        self.calls = []
        self.delete_fails = delete_fails
        self._next_id = 100

    def _sent(self, kind):
        self._next_id += 1
        self.calls.append((kind, self._next_id))
        return SimpleNamespace(message_id=self._next_id)

    async def send_message(self, chat_id, text, **kwargs):
        return self._sent("send_message")

    async def send_photo(self, chat_id, photo, **kwargs):
        return self._sent("send_photo")

    async def delete_message(self, chat_id, message_id):
        if self.delete_fails:
            raise BadRequest("Message can't be deleted")
        self.calls.append(("delete", message_id))

    async def edit_message_reply_markup(self, chat_id, message_id, reply_markup):
        self.calls.append(("clear_keyboard", message_id))


@pytest.fixture(autouse=True)
def no_persist(monkeypatch):
    monkeypatch.setattr(table_handlers, "_persist_tables", lambda: None)


def _table(message_id=None):
    table = BlackjackTable(chat_id=-100, host_id=1)
    table.message_id = message_id
    return table


class TestRetireMessage:
    def test_deletes_old_message(self):
        bot = _FakeBot()
        asyncio.run(table_handlers._retire_message(bot, -100, 7))
        assert bot.calls == [("delete", 7)]

    def test_falls_back_to_clearing_buttons(self):
        bot = _FakeBot(delete_fails=True)
        asyncio.run(table_handlers._retire_message(bot, -100, 7))
        assert bot.calls == [("clear_keyboard", 7)]

    def test_nothing_to_retire(self):
        bot = _FakeBot()
        asyncio.run(table_handlers._retire_message(bot, -100, None))
        assert bot.calls == []


class TestSingleTableMessage:
    def test_betting_board_reposted_then_old_deleted(self):
        bot = _FakeBot()
        table = _table(message_id=7)
        table.join(user_id=1, name="P1", bet=10.0)

        asyncio.run(table_handlers._show_betting(bot, table))

        # 새 메시지를 먼저 보내고 나서 지운다 (전송 실패 시 화면이 비지 않도록)
        assert bot.calls == [("send_message", 101), ("delete", 7)]
        assert table.message_id == 101

    def test_new_turn_message_replaces_previous(self, monkeypatch):
        monkeypatch.setattr(
            table_handlers, "_render_table_image", lambda table, results=None: b""
        )
        bot = _FakeBot()
        table = _table(message_id=7)
        for user_id in (1, 2):
            table.join(user_id=user_id, name=f"P{user_id}", bet=10.0)
        table.deck.cards = ["5C", "6D"] * 20  # 블랙잭 없이 진행
        table.deal()

        asyncio.run(table_handlers._show_turn(bot, table, new_message=True))

        assert bot.calls == [("send_photo", 101), ("delete", 7)]
        assert table.message_id == 101

    def test_old_message_kept_if_new_message_fails(self):
        class _DownBot(_FakeBot):
            async def send_message(self, chat_id, text, **kwargs):
                raise BadRequest("boom")

        bot = _DownBot()
        table = _table(message_id=7)
        with pytest.raises(BadRequest):
            asyncio.run(table_handlers._show_betting(bot, table))
        assert bot.calls == []
        assert table.message_id == 7
