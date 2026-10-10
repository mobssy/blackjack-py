"""
JackPy - 전역 에러 핸들러
핸들러에서 처리되지 않은 예외를 기록하고, 사용자에게 짧은 안내를 보낸다
"""

import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from bot.handlers.common import user_lang
from bot.utils.i18n import get_user_lang, t

logger = logging.getLogger(__name__)


def _describe(update: object) -> str:
    """로그용 업데이트 요약 — 대화 내용은 남기지 않고 ID만 기록"""
    if not isinstance(update, Update):
        return repr(update)
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    return f"update={update.update_id}, user={user_id}, chat={chat_id}"


def _safe_lang(update: Update) -> str:
    """안내 문구 언어 — 조회 실패 시 기본 언어 (DB 장애가 원인일 수 있음)"""
    if update.effective_user is None:
        return get_user_lang(None)
    try:
        return user_lang(update.effective_user.id)
    except Exception:
        logger.warning("에러 안내용 언어 조회 실패 — 기본 언어 사용", exc_info=True)
        return get_user_lang(None)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    처리되지 않은 예외 기록 + 사용자 안내 (Application.add_error_handler로 등록)

    텔레그램 API 오류(메시지 수정 불가, 네트워크 등)는 안내를 보내도 실패하거나
    의미가 없으므로 기록만 한다.

    Args:
        update: 예외가 난 업데이트 (업데이트 밖의 작업이면 None일 수 있음)
        context: 컨텍스트 객체 (context.error에 예외)
    """
    logger.error(f"처리되지 않은 예외 ({_describe(update)})", exc_info=context.error)
    if isinstance(context.error, TelegramError):
        return
    if not isinstance(update, Update) or update.effective_message is None:
        return

    try:
        await update.effective_message.reply_text(
            t("error_generic", _safe_lang(update))
        )
    except TelegramError as e:
        logger.warning(f"에러 안내 전송 실패: {e}")
