"""
JackPy - 게임 세션 영속화
봇 재시작 시 진행 중인 게임(이미 베팅이 차감된 상태)이 유실되지 않도록
1인 게임 세션과 멀티 테이블을 JSON 파일로 저장/복원한다.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, TypeVar

from bot.utils.blackjack_game import BlackjackGame
from bot.utils.table import BlackjackTable

logger = logging.getLogger(__name__)

SESSION_FILE = Path("game_sessions.json")
TABLE_FILE = Path("table_sessions.json")

T = TypeVar("T")


def _write(path: Path, items: Dict[int, Any]) -> None:
    """
    to_dict()를 가진 객체 매핑을 저장 (비어 있으면 파일 삭제)

    임시 파일에 다 쓴 뒤 os.replace로 교체한다 — 쓰는 도중 프로세스가 죽어도
    기존 파일이 반쯤 쓰인 상태로 남지 않는다 (복원 실패 = 차감된 베팅 유실 방지).
    """
    if not items:
        path.unlink(missing_ok=True)
        return
    data = {str(key): item.to_dict() for key, item in items.items()}
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _quarantine(path: Path) -> None:
    """복원에 실패한 파일을 .corrupt로 옮겨 수동 복구 여지를 남긴다"""
    if path.exists():
        os.replace(path, path.with_name(path.name + ".corrupt"))


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
    손상된 파일은 .corrupt로 옮겨 두므로 차감된 베팅을 수동으로 복구할 수 있다.

    Returns:
        Dict[int, BlackjackGame]: 복원된 세션
    """
    try:
        sessions = _read(SESSION_FILE, BlackjackGame.from_dict)
        if sessions:
            logger.info(f"진행 중이던 게임 세션 {len(sessions)}건 복원")
        return sessions
    except Exception:
        logger.exception(f"게임 세션 복원 실패 — {SESSION_FILE}.corrupt로 옮기고 초기화합니다")
        _quarantine(SESSION_FILE)
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
    저장된 멀티 테이블 복원 (실패 시 빈 dict — 손상된 파일은 .corrupt로 보관)

    Returns:
        Dict[int, BlackjackTable]: 복원된 테이블
    """
    try:
        tables = _read(TABLE_FILE, BlackjackTable.from_dict)
        if tables:
            logger.info(f"진행 중이던 테이블 {len(tables)}건 복원")
        return tables
    except Exception:
        logger.exception(f"테이블 세션 복원 실패 — {TABLE_FILE}.corrupt로 옮기고 초기화합니다")
        _quarantine(TABLE_FILE)
        return {}
