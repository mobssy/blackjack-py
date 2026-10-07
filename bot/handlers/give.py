"""
JackPy - 칩 선물 핸들러
/give @username 금액, 또는 상대 메시지에 답장하며 /give 금액
"""

import logging
from html import escape
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from models import get_db, User
from bot.utils.gifting import GiveError, GiveRequest, parse_give_args, transfer_chips
from bot.utils.i18n import t, get_user_lang

logger = logging.getLogger(__name__)


def _find_recipient(db, update: Update, request: GiveRequest) -> Optional[User]:
    """
    받는 사람 조회 — @username이 있으면 그것으로(대소문자 무시), 없으면 답장 대상

    Raises:
        GiveError: 받는 사람을 지정하지 않았거나 봇에게 보내는 경우
    """
    if request.username:
        return User.find_by_username(db, request.username)

    reply = update.message.reply_to_message
    if reply is None or reply.from_user is None:
        raise GiveError("give_usage")
    if reply.from_user.is_bot:
        raise GiveError("give_bot")
    return User.find_by_tg_id(db, reply.from_user.id)


async def cmd_give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /give - 다른 플레이어에게 칩 선물

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    with get_db() as db:
        sender = User.find_by_tg_id(db, user_tg_id)
        lang = get_user_lang(sender)
        if sender is None:
            await update.message.reply_text(t("deal_no_user", lang))
            return

        try:
            request = parse_give_args(context.args or [])
            recipient = _find_recipient(db, update, request)
            if recipient is None:
                raise GiveError("give_unknown_user")
            transfer_chips(sender, recipient, request.amount)
        except GiveError as e:
            await update.message.reply_text(t(e.key, lang, **e.kwargs))
            return
        db.commit()

        logger.info(
            f"칩 선물: {sender.tg_user_id} → {recipient.tg_user_id} "
            f"${request.amount:,.2f}"
        )
        await update.message.reply_text(
            t(
                "give_done",
                lang,
                sender=escape(sender.first_name or sender.display_name),
                recipient=escape(recipient.first_name or recipient.display_name),
                amount=float(request.amount),
                balance=float(sender.wallet),
            ),
            parse_mode=ParseMode.HTML,
        )
