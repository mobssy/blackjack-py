"""
JackPy - 게임 세션 영속화
봇 재시작 시 진행 중인 게임(이미 베팅이 차감된 상태)이 유실되지 않도록
1인 게임 세션과 멀티 테이블을 JSON 파일로 저장/복원한다.
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, TypeVar

from bot.utils.blackjack_game import BlackjackGame
from bot.utils.table import BlackjackTable

logger = logging.getLogger(__name__)

SESSION_FILE = Path("game_sessions.json")
TABLE_FILE = Path("table_sessions.json")

T = TypeVar("T")


def _write(path: Path, items: Dict[int, Any]) -> None:
    """to_dict()를 가진 객체 매핑을 저장 (비어 있으면 파일 삭제)"""
    if not items:
        path.unlink(missing_ok=True)
        return
    data = {str(key): item.to_dict() for key, item in items.items()}
    path.write_text(json.dumps(data, ensure_ascii=False))


def _read(path: Path, factory: Callable[[dict], T]) -> Dict[int, T]:
    """저장된 매핑 복원 (파일 없으면 빈 dict)"""
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {int(key): factory(item) for key, item in data.items()}


def save_sessions(sessions: Dict[int, BlackjackGame]) -> None:
    """
    현재 게임 세션을 파일에 저장 (세션이 없으면 파일 삭제)

    Args:
        sessions: user_tg_id → BlackjackGame 매핑
    """
    try:
        _write(SESSION_FILE, sessions)
    except Exception:
        logger.exception("게임 세션 저장 실패")


def load_sessions() -> Dict[int, BlackjackGame]:
    """
    저장된 게임 세션 복원

    복원에 실패하면(파일 손상, 구조 변경 등) 빈 dict를 반환한다.
    이 경우 해당 세션의 베팅은 유실되므로 로그를 남긴다.

    Returns:
        Dict[int, BlackjackGame]: 복원된 세션
    """
    try:
        sessions = _read(SESSION_FILE, BlackjackGame.from_dict)
        if sessions:
            logger.info(f"진행 중이던 게임 세션 {len(sessions)}건 복원")
        return sessions
    except Exception:
        logger.exception("게임 세션 복원 실패 — 세션을 초기화합니다 (해당 베팅 유실)")
        SESSION_FILE.unlink(missing_ok=True)
        return {}


def save_tables(tables: Dict[int, BlackjackTable]) -> None:
    """
    현재 멀티 테이블을 파일에 저장 (테이블이 없으면 파일 삭제)

    Args:
        tables: chat_id → BlackjackTable 매핑
    """
    try:
        _write(TABLE_FILE, tables)
    except Exception:
        logger.exception("테이블 세션 저장 실패")


def load_tables() -> Dict[int, BlackjackTable]:
    """
    저장된 멀티 테이블 복원 (실패 시 빈 dict — 해당 베팅 유실 로그)

    Returns:
        Dict[int, BlackjackTable]: 복원된 테이블
    """
    try:
        tables = _read(TABLE_FILE, BlackjackTable.from_dict)
        if tables:
            logger.info(f"진행 중이던 테이블 {len(tables)}건 복원")
        return tables
    except Exception:
        logger.exception("테이블 세션 복원 실패 — 테이블을 초기화합니다 (해당 베팅 유실)")
        TABLE_FILE.unlink(missing_ok=True)
        return {}
