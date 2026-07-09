"""
JackPy - 게임 세션 영속화
봇 재시작 시 진행 중인 게임(이미 베팅이 차감된 상태)이 유실되지 않도록
게임 세션을 JSON 파일로 저장/복원한다.
"""

import json
import logging
from pathlib import Path
from typing import Dict

from bot.utils.blackjack_game import BlackjackGame

logger = logging.getLogger(__name__)

SESSION_FILE = Path("game_sessions.json")


def save_sessions(sessions: Dict[int, BlackjackGame]) -> None:
    """
    현재 게임 세션을 파일에 저장 (세션이 없으면 파일 삭제)

    Args:
        sessions: user_tg_id → BlackjackGame 매핑
    """
    try:
        if not sessions:
            SESSION_FILE.unlink(missing_ok=True)
            return
        data = {str(uid): game.to_dict() for uid, game in sessions.items()}
        SESSION_FILE.write_text(json.dumps(data, ensure_ascii=False))
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
    if not SESSION_FILE.exists():
        return {}
    try:
        data = json.loads(SESSION_FILE.read_text())
        sessions = {
            int(uid): BlackjackGame.from_dict(game_data)
            for uid, game_data in data.items()
        }
        if sessions:
            logger.info(f"진행 중이던 게임 세션 {len(sessions)}건 복원")
        return sessions
    except Exception:
        logger.exception("게임 세션 복원 실패 — 세션을 초기화합니다 (해당 베팅 유실)")
        SESSION_FILE.unlink(missing_ok=True)
        return {}
