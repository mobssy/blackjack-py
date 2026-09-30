"""
JackPy - 텔레그램 명령어 메뉴 정의
채팅 종류(개인/그룹)와 권한(관리자)별로 `/` 메뉴에 노출할 명령어 목록.
설명은 i18n 키(cmd_desc_<명령어>)로 관리한다. 텔레그램 의존성 없음 —
실제 등록은 bot.handlers.menu.sync_command_menu가 봇 시작 시 수행한다.
"""

from typing import List, Tuple

from bot.utils.i18n import t

# 메뉴를 등록할 언어. 기본 언어는 language_code 없이 등록되어
# 그 외 언어 사용자에게도 표시된다.
MENU_LANGS: Tuple[str, ...] = ("ko", "en")
DEFAULT_MENU_LANG = "ko"

# 개인 채팅: 1인 게임 + 프로필
PRIVATE_COMMANDS: Tuple[str, ...] = (
    "start",
    "help",
    "deal",
    "hit",
    "stand",
    "double",
    "surrender",
    "split",
    "insurance",
    "wallet",
    "daily",
    "my",
    "stats",
    "history",
    "rank",
)

# 그룹 채팅: 멀티 테이블 중심 (/deal 등 1인 게임은 그룹에서 DM으로 유도만 하므로 제외)
GROUP_COMMANDS: Tuple[str, ...] = (
    "table",
    "join",
    "leave",
    "rank",
    "wallet",
    "daily",
    "my",
    "help",
)

# 관리자 전용 (관리자 본인의 개인 채팅에만 노출)
ADMIN_ONLY_COMMANDS: Tuple[str, ...] = ("admin", "add")
ADMIN_COMMANDS: Tuple[str, ...] = PRIVATE_COMMANDS + ADMIN_ONLY_COMMANDS


def description_key(command: str) -> str:
    """명령어 설명 i18n 키"""
    return f"cmd_desc_{command}"


def menu(commands: Tuple[str, ...], lang: str) -> List[Tuple[str, str]]:
    """
    명령어 목록을 (명령어, 설명) 쌍으로 변환

    Args:
        commands: 명령어 이름 목록
        lang: 설명 언어

    Returns:
        List[Tuple[str, str]]: (command, description) 리스트
    """
    return [(command, t(description_key(command), lang)) for command in commands]
