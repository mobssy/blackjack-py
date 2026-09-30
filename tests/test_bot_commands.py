"""
JackPy - 명령어 메뉴 정의 테스트
메뉴 명령어가 실제 등록된 핸들러와 일치하는지, 설명 i18n/텔레그램 제약을 지키는지 검증
"""

import re
from pathlib import Path

import pytest

from bot.utils.bot_commands import (
    ADMIN_COMMANDS,
    ADMIN_ONLY_COMMANDS,
    DEFAULT_MENU_LANG,
    GROUP_COMMANDS,
    MENU_LANGS,
    PRIVATE_COMMANDS,
    description_key,
    menu,
)
from bot.utils.i18n import STRINGS

MAIN_PY = Path(__file__).resolve().parent.parent / "bot" / "main.py"
ALL_MENU_COMMANDS = set(PRIVATE_COMMANDS) | set(GROUP_COMMANDS) | set(ADMIN_COMMANDS)


def _registered_commands() -> set:
    """bot/main.py에 CommandHandler로 등록된 명령어 (main은 토큰 없이 import 불가)"""
    return set(re.findall(r'CommandHandler\("([a-z0-9_]+)"', MAIN_PY.read_text()))


class TestMenuMatchesHandlers:
    """메뉴 ↔ 등록된 핸들러 일치 (없는 명령어가 메뉴에 남는 문제 방지)"""

    def test_every_menu_command_is_registered(self):
        assert ALL_MENU_COMMANDS - _registered_commands() == set()

    def test_every_registered_command_is_in_some_menu(self):
        assert _registered_commands() - ALL_MENU_COMMANDS == set()


class TestMenuScopes:
    """스코프별 구성"""

    def test_admin_commands_hidden_from_public_menus(self):
        for command in ADMIN_ONLY_COMMANDS:
            assert command not in PRIVATE_COMMANDS
            assert command not in GROUP_COMMANDS

    def test_admin_menu_extends_private_menu(self):
        assert ADMIN_COMMANDS[: len(PRIVATE_COMMANDS)] == PRIVATE_COMMANDS
        assert set(ADMIN_ONLY_COMMANDS) <= set(ADMIN_COMMANDS)

    def test_group_menu_has_table_not_solo_game(self):
        assert {"table", "join", "leave"} <= set(GROUP_COMMANDS)
        assert not {"deal", "hit", "stand"} & set(GROUP_COMMANDS)

    def test_no_duplicates(self):
        for commands in (PRIVATE_COMMANDS, GROUP_COMMANDS, ADMIN_COMMANDS):
            assert len(commands) == len(set(commands))

    def test_default_lang_is_menu_lang(self):
        assert DEFAULT_MENU_LANG in MENU_LANGS


class TestMenuDescriptions:
    """설명 i18n 및 텔레그램 제약 (명령어 1-32자 소문자/숫자/_, 설명 1-256자)"""

    @pytest.mark.parametrize("lang", MENU_LANGS)
    def test_descriptions_exist_in_every_language(self, lang):
        missing = [
            c for c in ALL_MENU_COMMANDS if description_key(c) not in STRINGS[lang]
        ]
        assert missing == []

    @pytest.mark.parametrize("lang", MENU_LANGS)
    def test_telegram_limits(self, lang):
        for command, description in menu(tuple(ALL_MENU_COMMANDS), lang):
            assert re.fullmatch(r"[a-z0-9_]{1,32}", command)
            assert 1 <= len(description) <= 256

    def test_menu_keeps_order(self):
        assert [c for c, _ in menu(GROUP_COMMANDS, "ko")] == list(GROUP_COMMANDS)
