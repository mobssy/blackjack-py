"""
JackPy - 핸들러 공용 조회
"""

from bot.utils.i18n import get_user_lang
from models import User, get_db


def user_lang(user_tg_id: int) -> str:
    """사용자 언어 조회 (미등록 사용자는 기본 언어)"""
    with get_db() as db:
        return get_user_lang(User.find_by_tg_id(db, user_tg_id))
