"""
JackPy - 명령어 메뉴 동기화 테스트
스코프 구성과 sync_command_menu의 등록/실패 처리 검증 (가짜 Bot 사용)
"""

import asyncio

from telegram.error import TelegramError

from bot.handlers import menu as menu_module
from bot.utils.bot_commands import (
    ADMIN_COMMANDS,
    GROUP_COMMANDS,
    MENU_LANGS,
    PRIVATE_COMMANDS,
)


class FakeBot:
    """set_my_commands 호출을 기록하고, 지정한 스코프에서는 실패시킨다"""

    def __init__(self, fail_scope_type=None):
        self.calls = []
        self.fail_scope_type = fail_scope_type

    async def set_my_commands(self, commands, scope=None, language_code=None):
        if scope.type == self.fail_scope_type:
            raise TelegramError("Bad Request: chat not found")
        self.calls.append((scope, language_code, [c.command for c in commands]))
        return True


def _scope_map(monkeypatch, admins):
    monkeypatch.setattr(menu_module, "admin_ids", lambda: admins)
    return {scope.type: commands for scope, commands in menu_module._menu_scopes()}


class TestMenuScopes:
    def test_overrides_all_broad_scopes(self, monkeypatch):
        scopes = _scope_map(monkeypatch, [])
        # 예전 목록이 남으면 새 메뉴를 가리는 스코프까지 모두 덮어쓴다
        assert scopes["default"] == PRIVATE_COMMANDS
        assert scopes["all_private_chats"] == PRIVATE_COMMANDS
        assert scopes["all_group_chats"] == GROUP_COMMANDS
        assert scopes["all_chat_administrators"] == GROUP_COMMANDS
        assert "chat" not in scopes

    def test_admin_chat_scope_per_admin(self, monkeypatch):
        monkeypatch.setattr(menu_module, "admin_ids", lambda: [111, 222])
        admin_scopes = [
            (scope.chat_id, commands)
            for scope, commands in menu_module._menu_scopes()
            if scope.type == "chat"
        ]
        assert admin_scopes == [(111, ADMIN_COMMANDS), (222, ADMIN_COMMANDS)]


class TestSyncCommandMenu:
    def test_registers_every_scope_in_every_language(self, monkeypatch):
        monkeypatch.setattr(menu_module, "admin_ids", lambda: [111])
        bot = FakeBot()
        asyncio.run(menu_module.sync_command_menu(bot))

        scope_count = len(menu_module._menu_scopes())
        assert len(bot.calls) == scope_count * len(MENU_LANGS)
        # 기본 언어는 language_code 없이, 나머지는 언어 코드로 등록
        assert {code for _, code, _ in bot.calls} == {None, "en"}

    def test_failure_in_one_scope_does_not_stop_others(self, monkeypatch):
        monkeypatch.setattr(menu_module, "admin_ids", lambda: [111])
        bot = FakeBot(fail_scope_type="chat")
        asyncio.run(menu_module.sync_command_menu(bot))

        registered = {scope.type for scope, _, _ in bot.calls}
        assert "chat" not in registered
        assert {
            "default",
            "all_private_chats",
            "all_group_chats",
            "all_chat_administrators",
        } <= registered
