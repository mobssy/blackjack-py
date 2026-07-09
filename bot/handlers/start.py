"""
JackPy - 시작 및 기본 명령어 핸들러
/start, /help 명령어 처리
"""

import logging
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import get_db, User, Group, PlanType
from bot.utils.i18n import t, get_user_lang

logger = logging.getLogger(__name__)


def _lang_select_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇰🇷 한국어", callback_data="lang_ko"),
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
    ]])


def _start_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_game_start", lang), callback_data="start_game"),
            InlineKeyboardButton(t("btn_help", lang), callback_data="help"),
        ],
        [
            InlineKeyboardButton(t("btn_daily", lang), callback_data="daily_check"),
            InlineKeyboardButton(t("btn_profile", lang), callback_data="my_profile"),
        ],
    ])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 단체방에서 호출된 경우 DM 버튼만 전송
    if update.effective_chat.type in ("group", "supergroup"):
        with get_db() as db:
            user = db.query(User).filter(
                User.tg_user_id == update.effective_user.id
            ).first()
            lang = get_user_lang(user)
        bot_username = context.bot.username
        keyboard = [[InlineKeyboardButton(
            t("btn_start_dm", lang),
            url=f"https://t.me/{bot_username}?start=play"
        )]]
        await update.message.reply_text(
            t("group_redirect", lang, name=update.effective_user.first_name),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # DM: 항상 언어 선택 먼저
    await update.message.reply_text(
        "🇰🇷 한국어 / 🇺🇸 English",
        reply_markup=_lang_select_keyboard()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tg_id = update.effective_user.id
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(user)
    await update.message.reply_text(t("help_text", lang))


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_tg_id = update.effective_user.id

    # ── 언어 선택 ──────────────────────────────────────────────
    if query.data in ("lang_ko", "lang_en"):
        lang = "ko" if query.data == "lang_ko" else "en"
        username = update.effective_user.username
        first_name = update.effective_user.first_name

        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            if not user:
                user = User(
                    tg_user_id=user_tg_id,
                    username=username,
                    first_name=first_name,
                    wallet=1000.0,
                    language=lang,
                    stats_json={
                        "total_games": 0,
                        "wins": 0,
                        "losses": 0,
                        "total_bet": 0,
                        "total_profit": 0,
                    },
                )
                db.add(user)
                db.commit()
                welcome = t("welcome_new", lang)
            else:
                user.username = username
                user.first_name = first_name
                user.language = lang
                db.commit()
                welcome = t("welcome_back", lang, name=user.display_name)

        await query.edit_message_text(
            welcome,
            reply_markup=_start_menu_keyboard(lang)
        )
        return

    # 이후 콜백은 언어 필요 → DB 조회
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(user)

    # ── 게임 시작 안내 ──────────────────────────────────────────
    if query.data == "start_game":
        back = [[InlineKeyboardButton(t("btn_back", lang), callback_data="back_to_start")]]
        await query.edit_message_text(
            t("start_game_msg", lang), reply_markup=InlineKeyboardMarkup(back)
        )

    # ── 도움말 ─────────────────────────────────────────────────
    elif query.data == "help":
        back = [[InlineKeyboardButton(t("btn_back", lang), callback_data="back_to_start")]]
        await query.edit_message_text(t("help_text", lang), reply_markup=InlineKeyboardMarkup(back))

    # ── 출석 체크 ───────────────────────────────────────────────
    elif query.data == "daily_check":
        back = [[InlineKeyboardButton(t("btn_back", lang), callback_data="back_to_start")]]
        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            if not user:
                await query.edit_message_text(t("deal_no_user", lang))
                return

            if not user.can_claim_daily():
                await query.edit_message_text(
                    t("daily_already", lang),
                    reply_markup=InlineKeyboardMarkup(back)
                )
                return

            is_vip = user.is_vip_active
            reward = 500.0 if is_vip else 200.0
            user.add_wallet(reward)
            user.last_daily_at = datetime.now(timezone.utc)
            db.commit()
            balance = float(user.wallet)

        bonus = t("daily_vip_bonus", lang) if is_vip else ""
        await query.edit_message_text(
            t("daily_reward", lang, reward=reward, bonus=bonus, balance=balance),
            reply_markup=InlineKeyboardMarkup(back)
        )

    # ── 프로필 ─────────────────────────────────────────────────
    elif query.data == "my_profile":
        back = [[InlineKeyboardButton(t("btn_back", lang), callback_data="back_to_start")]]
        chat_id = update.effective_chat.id

        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            if not user:
                await query.edit_message_text(t("deal_no_user", lang))
                return

            stats = user.stats_json or {}
            total = stats.get("total_games", 0)
            wins = stats.get("wins", 0)
            win_rate = (wins / total * 100) if total > 0 else 0.0
            group = db.query(Group).filter(Group.chat_id == chat_id).first()

            if lang == "en":
                msg = (
                    f"Profile\n\n"
                    f"Name: {user.display_name}\n"
                    f"Balance: ${user.wallet:,.2f}\n\n"
                    f"Games: {total:,}\n"
                    f"Wins: {wins:,}\n"
                    f"Losses: {stats.get('losses', 0):,}\n"
                    f"Win rate: {win_rate:.1f}%\n"
                    f"Total bet: ${stats.get('total_bet', 0):,.2f}\n"
                    f"Total profit: ${stats.get('total_profit', 0):,.2f}"
                )
            else:
                msg = (
                    f"프로필\n\n"
                    f"이름: {user.display_name}\n"
                    f"잔액: ${user.wallet:,.2f}\n\n"
                    f"총 게임: {total:,}회\n"
                    f"승리: {wins:,}회\n"
                    f"패배: {stats.get('losses', 0):,}회\n"
                    f"승률: {win_rate:.1f}%\n"
                    f"총 베팅: ${stats.get('total_bet', 0):,.2f}\n"
                    f"총 수익: ${stats.get('total_profit', 0):,.2f}"
                )

        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(back))

    # ── 게임 버튼 (hit/stand/double/surrender/split) ────────────
    elif query.data in (
        "game_hit", "game_stand", "game_double", "game_surrender", "game_split"
    ):
        from bot.handlers.blackjack import game_button_callback
        await game_button_callback(update, context)

    # ── 뒤로가기 ────────────────────────────────────────────────
    elif query.data == "back_to_start":
        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            lang = get_user_lang(user)
            welcome = t("welcome_back", lang, name=user.display_name) if user else "JackPy\n\n"

        await query.edit_message_text(welcome, reply_markup=_start_menu_keyboard(lang))

    # ── 게임 재시작 안내 ─────────────────────────────────────────
    elif query.data == "restart_game":
        back = [[InlineKeyboardButton(t("btn_back", lang), callback_data="back_to_start")]]
        await query.edit_message_caption(
            caption=t("start_game_msg", lang), reply_markup=InlineKeyboardMarkup(back)
        )
