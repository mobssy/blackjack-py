"""
JackPy - 시작 및 기본 명령어 핸들러
/start, /help 명령어 처리
"""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import get_db, User
from bot.utils.i18n import t, get_user_lang

logger = logging.getLogger(__name__)


def _lang_select_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇰🇷 한국어", callback_data="lang_ko"),
                InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
            ]
        ]
    )


def _start_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("btn_game_start", lang), callback_data="start_game"
                ),
                InlineKeyboardButton(t("btn_help", lang), callback_data="help"),
            ],
            [
                InlineKeyboardButton(t("btn_daily", lang), callback_data="daily_check"),
                InlineKeyboardButton(
                    t("btn_profile", lang), callback_data="my_profile"
                ),
            ],
        ]
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 단체방에서 호출된 경우 DM 버튼만 전송
    if update.effective_chat.type in ("group", "supergroup"):
        with get_db() as db:
            user = (
                db.query(User)
                .filter(User.tg_user_id == update.effective_user.id)
                .first()
            )
            lang = get_user_lang(user)
        bot_username = context.bot.username
        keyboard = [
            [
                InlineKeyboardButton(
                    t("btn_start_dm", lang),
                    url=f"https://t.me/{bot_username}?start=play",
                )
            ]
        ]
        await update.message.reply_text(
            t("group_redirect", lang, name=update.effective_user.first_name),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # DM: 항상 언어 선택 먼저
    await update.message.reply_text(
        "🇰🇷 한국어 / 🇺🇸 English", reply_markup=_lang_select_keyboard()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tg_id = update.effective_user.id
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(user)
    await update.message.reply_text(t("help_text", lang))


_LANGUAGES = {"lang_ko": "ko", "lang_en": "en"}


def _back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("btn_back", lang), callback_data="back_to_start")]]
    )


def _find_user(db, user_tg_id: int) -> Optional[User]:
    return db.query(User).filter(User.tg_user_id == user_tg_id).first()


def _profile_text(user: User, lang: str) -> str:
    """시작 메뉴 프로필 버튼 문구"""
    stats = user.stats_json or {}
    total = stats.get("total_games", 0)
    wins = stats.get("wins", 0)
    return t(
        "menu_profile",
        lang,
        name=user.display_name,
        balance=float(user.wallet),
        games=total,
        wins=wins,
        losses=stats.get("losses", 0),
        win_rate=(wins / total * 100) if total > 0 else 0.0,
        total_bet=stats.get("total_bet", 0),
        total_profit=stats.get("total_profit", 0),
    )


async def _select_language(query, tg_user, lang: str) -> None:
    """언어 선택 — 처음이면 가입, 기존 사용자는 언어와 이름 갱신"""
    with get_db() as db:
        user = _find_user(db, tg_user.id)
        if not user:
            user = User.create_new(
                tg_user.id, tg_user.username, tg_user.first_name, language=lang
            )
            db.add(user)
            welcome = t("welcome_new", lang)
        else:
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.language = lang
            welcome = t("welcome_back", lang, name=user.display_name)
        db.commit()

    await query.edit_message_text(welcome, reply_markup=_start_menu_keyboard(lang))


async def _menu_start_game(query, user_tg_id: int, lang: str) -> None:
    await query.edit_message_text(
        t("start_game_msg", lang), reply_markup=_back_keyboard(lang)
    )


async def _menu_help(query, user_tg_id: int, lang: str) -> None:
    await query.edit_message_text(
        t("help_text", lang), reply_markup=_back_keyboard(lang)
    )


async def _menu_daily(query, user_tg_id: int, lang: str) -> None:
    """출석 체크 — /daily와 같은 로직 (출석 스트릭 반영)"""
    from bot.handlers.blackjack import claim_daily_reward

    with get_db() as db:
        user = _find_user(db, user_tg_id)
        message = claim_daily_reward(db, user, lang) if user else None

    if message is None:
        await query.edit_message_text(t("deal_no_user", lang))
        return
    await query.edit_message_text(message, reply_markup=_back_keyboard(lang))


async def _menu_profile(query, user_tg_id: int, lang: str) -> None:
    with get_db() as db:
        user = _find_user(db, user_tg_id)
        message = _profile_text(user, lang) if user else None

    if message is None:
        await query.edit_message_text(t("deal_no_user", lang))
        return
    await query.edit_message_text(message, reply_markup=_back_keyboard(lang))


async def _menu_back(query, user_tg_id: int, lang: str) -> None:
    with get_db() as db:
        user = _find_user(db, user_tg_id)
        welcome = (
            t("welcome_back", lang, name=user.display_name) if user else "JackPy\n\n"
        )

    await query.edit_message_text(welcome, reply_markup=_start_menu_keyboard(lang))


async def _menu_restart(query, user_tg_id: int, lang: str) -> None:
    """게임 결과 메시지의 "다시 하기" — 사진 메시지라 캡션을 수정"""
    await query.edit_message_caption(
        caption=t("start_game_msg", lang), reply_markup=_back_keyboard(lang)
    )


MenuAction = Callable[[Any, int, str], Awaitable[None]]

_MENU_ACTIONS: Dict[str, MenuAction] = {
    "start_game": _menu_start_game,
    "help": _menu_help,
    "daily_check": _menu_daily,
    "my_profile": _menu_profile,
    "back_to_start": _menu_back,
    "restart_game": _menu_restart,
}


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    시작 메뉴·언어 선택 버튼 콜백 (tbl_*, game_* 는 main.py에서 따로 등록)

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    query = update.callback_query
    await query.answer()

    if query.data in _LANGUAGES:
        await _select_language(query, update.effective_user, _LANGUAGES[query.data])
        return

    action = _MENU_ACTIONS.get(query.data)
    if action is None:
        return

    user_tg_id = update.effective_user.id
    with get_db() as db:
        lang = get_user_lang(_find_user(db, user_tg_id))
    await action(query, user_tg_id, lang)
