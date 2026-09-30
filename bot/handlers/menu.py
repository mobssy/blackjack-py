"""
JackPy - 텔레그램 명령어 메뉴 동기화
봇 시작 시 bot_commands 정의대로 `/` 메뉴를 채팅 종류·권한·언어별로 등록한다.
"""

import logging
from typing import List, Optional, Tuple

from telegram import (
    Bot,
    BotCommand,
    BotCommandScope,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)
from telegram.error import TelegramError

from bot.handlers.admin import admin_ids
from bot.utils.bot_commands import (
    ADMIN_COMMANDS,
    DEFAULT_MENU_LANG,
    GROUP_COMMANDS,
    MENU_LANGS,
    PRIVATE_COMMANDS,
    menu,
)

logger = logging.getLogger(__name__)


def _menu_scopes() -> List[Tuple[BotCommandScope, Tuple[str, ...]]]:
    """
    (스코프, 명령어 목록) 목록

    텔레그램은 좁은 스코프를 우선 적용하므로(AllPrivateChats > Default,
    AllChatAdministrators > AllGroupChats), 예전에 등록된 목록이 남아 새 메뉴를
    가리지 않도록 넓은 스코프까지 모두 명시적으로 덮어쓴다.
    봇 관리자는 본인 개인 채팅(chat_id == user_id)에만 관리자 명령어가 보인다.
    """
    scopes: List[Tuple[BotCommandScope, Tuple[str, ...]]] = [
        (BotCommandScopeDefault(), PRIVATE_COMMANDS),
        (BotCommandScopeAllPrivateChats(), PRIVATE_COMMANDS),
        (BotCommandScopeAllGroupChats(), GROUP_COMMANDS),
        (BotCommandScopeAllChatAdministrators(), GROUP_COMMANDS),
    ]
    scopes += [
        (BotCommandScopeChat(chat_id=admin_id), ADMIN_COMMANDS)
        for admin_id in admin_ids()
    ]
    return scopes


async def sync_command_menu(bot: Bot) -> None:
    """
    명령어 메뉴 등록 (post_init에서 호출)

    실패해도 봇 기동을 막지 않도록 스코프별로 로그만 남긴다.
    (예: 관리자가 봇과 대화를 시작한 적이 없으면 chat 스코프 등록이 실패한다)
    """
    for scope, commands in _menu_scopes():
        for lang in MENU_LANGS:
            language_code: Optional[str] = None if lang == DEFAULT_MENU_LANG else lang
            bot_commands = [
                BotCommand(command, description)
                for command, description in menu(commands, lang)
            ]
            try:
                await bot.set_my_commands(
                    bot_commands, scope=scope, language_code=language_code
                )
            except TelegramError as e:
                logger.warning(f"명령어 메뉴 등록 실패 ({scope.type}, {lang}): {e}")
    logger.info("✅ 명령어 메뉴 동기화 완료")
