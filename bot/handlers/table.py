"""
JackPy - 멀티플레이 블랙잭 테이블 핸들러
그룹 채팅에서 여러 명이 한 딜러와 플레이: /table /join /leave 및 tbl_* 버튼

흐름: /table(오픈) → /join 금액(착석) → 호스트 버튼 또는 BETTING_SECONDS 후 딜
→ 좌석 순서대로 턴 (TURN_TIMEOUT_SECONDS 초과 시 자동 스탠드) → 일괄 정산
"""

import asyncio
import logging
from html import escape
from io import BytesIO
from typing import Awaitable, Callable, Dict, Optional

from telegram import (
    Bot,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from models import get_db, User
from bot.handlers.blackjack import get_game_keyboard
from bot.handlers.settlement import apply_settlement
from bot.utils.table_renderer import get_table_renderer
from bot.utils.betting import BetError, is_valid_amount, parse_bet
from bot.utils.deck import is_bust
from bot.utils.i18n import t, get_user_lang
from bot.utils.session_store import load_tables, save_tables
from bot.utils.table import (
    BETTING_SECONDS,
    TURN_TIMEOUT_SECONDS,
    BlackjackTable,
    Seat,
    SeatResults,
    TableAction,
    TableError,
    TablePhase,
)
from bot.utils.table_view import (
    betting_caption,
    result_text,
    seat_views,
    turn_caption,
)

logger = logging.getLogger(__name__)

# 채팅방별 멀티 테이블 (메모리 + JSON 영속화, 재시작 시 post_init에서 재개)
table_sessions: Dict[int, BlackjackTable] = load_tables()

# 채팅방별 타임아웃 타이머 (베팅 마감 / 턴 제한)와 상태 변경 직렬화 락
_timers: Dict[int, asyncio.Task] = {}
_locks: Dict[int, asyncio.Lock] = {}

# 추가 베팅이 필요한 액션의 잔액 부족 안내 키
_NO_BALANCE_KEYS = {
    TableAction.DOUBLE: "double_no_balance",
    TableAction.SPLIT: "split_no_balance",
    TableAction.INSURANCE: "insurance_no_balance",
}

# 텔레그램 사진 캡션 최대 길이
_CAPTION_LIMIT = 1024


# ── 공통 헬퍼 ──────────────────────────────────────────────────


def _persist_tables() -> None:
    """테이블 상태 변경 시점마다 파일에 반영"""
    save_tables(table_sessions)


def _lock(chat_id: int) -> asyncio.Lock:
    """
    채팅방별 락 — 명령어/버튼/타이머가 같은 테이블을 동시에 변경하지 않도록 한다.
    외부 진입점(핸들러, 타이머)에서만 획득하고 내부 함수에서는 획득하지 않는다.
    """
    return _locks.setdefault(chat_id, asyncio.Lock())


def _is_group(update: Update) -> bool:
    return update.effective_chat.type in ("group", "supergroup")


def _user_lang(user_tg_id: int) -> str:
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        return get_user_lang(user)


def _is_not_modified(error: BadRequest) -> bool:
    return "not modified" in str(error).lower()


async def _answer_quietly(query: CallbackQuery) -> None:
    """
    상태 변경 후의 콜백 응답 — 실패해도 진행을 막지 않는다.
    (앞선 요청이 Flood control로 대기하는 사이 쿼리가 만료될 수 있다)
    """
    try:
        await query.answer()
    except TelegramError as e:
        logger.warning(f"콜백 응답 실패 (무시): {e}")


# ── 타이머 ────────────────────────────────────────────────────


def _cancel_timer(chat_id: int) -> None:
    task = _timers.pop(chat_id, None)
    if task is not None and task is not asyncio.current_task():
        task.cancel()


def _schedule(
    chat_id: int, seconds: int, callback: Callable[[], Awaitable[None]]
) -> None:
    """chat_id의 기존 타이머를 취소하고 seconds 후 callback 실행 예약"""
    _cancel_timer(chat_id)

    async def run() -> None:
        await asyncio.sleep(seconds)
        if _timers.get(chat_id) is asyncio.current_task():
            _timers.pop(chat_id, None)
        try:
            async with _lock(chat_id):
                await callback()
        except Exception:
            logger.exception(f"테이블 타이머 처리 실패 (chat={chat_id})")

    _timers[chat_id] = asyncio.create_task(run())


def _arm_betting_timer(bot: Bot, table: BlackjackTable) -> None:
    """베팅 마감 시 자동 딜 (그 사이 호스트가 딜했으면 무시)"""

    async def on_timeout() -> None:
        if table_sessions.get(table.chat_id) is not table:
            return
        if table.phase is TablePhase.BETTING:
            await _start_round(bot, table)

    _schedule(table.chat_id, BETTING_SECONDS, on_timeout)


def _arm_turn_timer(bot: Bot, table: BlackjackTable) -> None:
    """차례 시간 초과 시 자동 스탠드 (예약 이후 상태가 바뀌었으면 무시)"""
    version = table.version

    async def on_timeout() -> None:
        if table_sessions.get(table.chat_id) is not table:
            return
        if table.version != version:
            return
        seat = table.timeout_stand()
        if seat is None:
            return
        _persist_tables()
        notice = t("table_timeout", table.lang, name=escape(seat.name))
        await _advance(bot, table, notice=notice, new_message=True)

    _schedule(table.chat_id, TURN_TIMEOUT_SECONDS, on_timeout)


# ── 메시지 표시 ────────────────────────────────────────────────


async def _clear_keyboard(bot: Bot, table: BlackjackTable) -> None:
    """이전 테이블 메시지의 버튼 제거 (실패는 무시)"""
    if table.message_id is None:
        return
    try:
        await bot.edit_message_reply_markup(
            chat_id=table.chat_id, message_id=table.message_id, reply_markup=None
        )
    except TelegramError:
        pass


async def _show_betting(
    bot: Bot, table: BlackjackTable, new_message: bool = False
) -> None:
    """베팅 단계 메시지 표시 (기존 메시지 수정 또는 새로 전송)"""
    text = betting_caption(table)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("btn_table_deal", table.lang), callback_data="tbl_deal"
                )
            ]
        ]
    )
    if not new_message and table.message_id is not None:
        try:
            await bot.edit_message_text(
                text,
                chat_id=table.chat_id,
                message_id=table.message_id,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
            return
        except BadRequest as e:
            if _is_not_modified(e):
                return
            logger.warning(f"베팅 메시지 수정 실패, 새로 전송: {e}")

    await _clear_keyboard(bot, table)
    message = await bot.send_message(
        table.chat_id, text, parse_mode=ParseMode.HTML, reply_markup=keyboard
    )
    table.message_id = message.message_id
    _persist_tables()


def _render_table_image(
    table: BlackjackTable, seat_results: Optional[SeatResults] = None
) -> bytes:
    """
    딜러 + 전체 좌석 이미지

    seat_results가 없으면 플레이 중(홀 카드 가림, 현재 차례 강조),
    있으면 결과 모드(홀 카드 공개, 좌석별 정산 결과)로 그린다.
    """
    current = table.current_seat
    if seat_results is not None:
        footer = t("img_table_result", table.lang)
    elif current is not None:
        footer = t("table_img_hint", table.lang, name=current.name)
    else:
        footer = ""
    return get_table_renderer().render(
        dealer_hand=table.dealer_hand,
        seats=seat_views(table, seat_results),
        hide_dealer_first=seat_results is None,
        dealer_label=t("img_table_dealer", table.lang),
        footer=footer,
    )


async def _show_turn(
    bot: Bot,
    table: BlackjackTable,
    notice: Optional[str] = None,
    new_message: bool = False,
) -> None:
    """
    현재 차례 표시

    같은 좌석의 연속 액션은 메시지를 수정하고, 차례가 바뀌면 새 메시지를
    보내 다음 플레이어에게 멘션 알림이 가도록 한다.
    """
    seat = table.current_seat
    if seat is None:
        return
    caption = turn_caption(table, notice)
    image_bytes = _render_table_image(table)
    game = seat.game
    keyboard = get_game_keyboard(
        first_turn=game.is_first_turn,
        can_split=game.can_split,
        can_insure=game.can_insure,
        prefix="tbl",
    )

    if not new_message and table.message_id is not None:
        try:
            await bot.edit_message_media(
                media=InputMediaPhoto(
                    media=BytesIO(image_bytes),
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                ),
                chat_id=table.chat_id,
                message_id=table.message_id,
                reply_markup=keyboard,
            )
            return
        except TelegramError as e:
            logger.warning(f"테이블 메시지 수정 실패, 새로 전송: {e}")

    await _clear_keyboard(bot, table)
    message = await bot.send_photo(
        table.chat_id,
        photo=BytesIO(image_bytes),
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )
    table.message_id = message.message_id
    _persist_tables()


# ── 라운드 진행 ────────────────────────────────────────────────


async def _open_or_resume(bot: Bot, chat_id: int, host_id: int, lang: str) -> None:
    """테이블이 없으면 새로 열고, 있으면 현재 상태를 다시 표시"""
    table = table_sessions.get(chat_id)
    if table is not None:
        await _resume(bot, table)
        return
    table = BlackjackTable(chat_id, host_id=host_id, lang=lang)
    table_sessions[chat_id] = table
    _persist_tables()
    try:
        await _show_betting(bot, table, new_message=True)
    finally:
        _arm_betting_timer(bot, table)


async def _resume(bot: Bot, table: BlackjackTable) -> None:
    """
    테이블 현재 상태를 새 메시지로 다시 표시하고, 타이머가 없으면 재예약
    (/table 재호출, 봇 재시작 후 복구 공용)
    """
    has_timer = table.chat_id in _timers
    if table.phase is TablePhase.BETTING:
        try:
            await _show_betting(bot, table, new_message=True)
        finally:
            if not has_timer:
                _arm_betting_timer(bot, table)
    elif table.is_round_over:
        await _finish_round(bot, table)
    else:
        try:
            await _show_turn(bot, table, new_message=True)
        finally:
            if not has_timer:
                _arm_turn_timer(bot, table)


async def _start_round(bot: Bot, table: BlackjackTable) -> None:
    """딜 시작 (착석자가 없으면 테이블 닫기)"""
    _cancel_timer(table.chat_id)
    if not table.seats:
        table_sessions.pop(table.chat_id, None)
        _persist_tables()
        await _clear_keyboard(bot, table)
        await bot.send_message(table.chat_id, t("table_closed_empty", table.lang))
        return

    table.deal()
    _persist_tables()
    await _clear_keyboard(bot, table)
    await _advance(bot, table, new_message=True)


async def _advance(
    bot: Bot,
    table: BlackjackTable,
    notice: Optional[str] = None,
    new_message: bool = False,
) -> None:
    """
    상태 변경 후 다음 단계로: 모든 좌석이 끝났으면 정산, 아니면 차례 표시

    메시지 전송이 실패해도(Flood control 등) 턴 타이머는 반드시 예약해
    시간 초과 시 자동 스탠드로 라운드가 계속 진행되게 한다.
    """
    if table.is_round_over:
        await _finish_round(bot, table, notice)
        return
    try:
        await _show_turn(bot, table, notice, new_message)
    finally:
        _arm_turn_timer(bot, table)


def _settle_table(table: BlackjackTable, seat_results: SeatResults) -> Dict[int, Dict]:
    """모든 좌석을 한 트랜잭션으로 정산 (일부만 반영되는 상황 방지)"""
    with get_db() as db:
        settle_infos = {}
        for seat, results in seat_results:
            user = db.query(User).filter(User.tg_user_id == seat.user_id).first()
            settle_infos[seat.user_id] = apply_settlement(
                db, user, seat.game, results, table.chat_id
            )
        db.commit()
        return settle_infos


async def _finish_round(
    bot: Bot, table: BlackjackTable, notice: Optional[str] = None
) -> None:
    """딜러 플레이 → 일괄 정산 → 테이블 제거 → 결과 전송"""
    _cancel_timer(table.chat_id)
    table.play_dealer()
    seat_results = table.results()

    # 정산 순서 불변식: DB 커밋 → 세션 pop → 메시지 전송
    settle_infos = _settle_table(table, seat_results)
    table_sessions.pop(table.chat_id, None)
    _persist_tables()

    await _clear_keyboard(bot, table)
    text = result_text(table, seat_results, settle_infos)
    if notice:
        text = f"{notice}\n\n{text}"
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("btn_table_new", table.lang), callback_data="tbl_new"
                )
            ]
        ]
    )
    image_bytes = _render_table_image(table, seat_results)

    # 캡션 한도를 넘으면(좌석이 많을 때) 이미지와 상세 결과를 나눠 보낸다
    if len(text) <= _CAPTION_LIMIT:
        await bot.send_photo(
            table.chat_id,
            photo=BytesIO(image_bytes),
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
        return
    await bot.send_photo(
        table.chat_id,
        photo=BytesIO(image_bytes),
        caption=t("table_result_title", table.lang),
    )
    await bot.send_message(
        table.chat_id, text, parse_mode=ParseMode.HTML, reply_markup=keyboard
    )


def _pay_action_cost(
    table: BlackjackTable, user_tg_id: int, action: TableAction, lang: str
) -> Optional[str]:
    """
    액션 검증 및 추가 베팅 차감

    Returns:
        Optional[str]: 잔액 부족 시 에러 메시지, 성공 시 None

    Raises:
        TableError: 차례가 아니거나 액션 조건 미달
    """
    cost = table.action_cost(user_tg_id, action)
    if cost <= 0:
        return None
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user or not user.deduct_wallet(cost):
            balance = float(user.wallet) if user else 0.0
            return t(_NO_BALANCE_KEYS[action], lang, balance=balance)
        db.commit()
    return None


def _action_notice(
    table: BlackjackTable, seat: Seat, action: TableAction, hand_index: int
) -> Optional[str]:
    """액션 결과를 테이블 전체에 알리는 한 줄 (없으면 None)"""
    lang = table.lang
    name = escape(seat.name)
    game = seat.game
    if action is TableAction.HIT and is_bust(game.hands[hand_index]):
        return t("table_action_bust", lang, name=name)
    if action is TableAction.DOUBLE:
        return t("table_action_double", lang, name=name, bet=game.total_bet)
    if action is TableAction.SURRENDER:
        return t("table_action_surrender", lang, name=name)
    if action is TableAction.SPLIT and game.split_rank == "A":
        return t("split_aces_note", lang)
    if action is TableAction.INSURANCE:
        return t("table_insured", lang, name=name, amount=game.insurance_bet)
    return None


# ── 명령어 ────────────────────────────────────────────────────


async def cmd_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /table - 그룹 멀티 테이블 열기 (이미 있으면 현재 상태 다시 표시)

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    lang = _user_lang(user_tg_id)
    if not _is_group(update):
        await update.message.reply_text(t("table_group_only", lang))
        return

    chat_id = update.effective_chat.id
    async with _lock(chat_id):
        await _open_or_resume(context.bot, chat_id, user_tg_id, lang)


async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /join [금액|all] - 테이블 착석 및 베팅

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    lang = _user_lang(user_tg_id)
    if not _is_group(update):
        await update.message.reply_text(t("table_group_only", lang))
        return
    if not context.args:
        await update.message.reply_text(t("table_join_usage", lang))
        return

    try:
        bet_request = parse_bet(context.args[0])
    except BetError as e:
        await update.message.reply_text(t(e.key, lang, **e.kwargs))
        return

    chat_id = update.effective_chat.id
    async with _lock(chat_id):
        table = table_sessions.get(chat_id)
        if table is None:
            await update.message.reply_text(t("table_none", lang))
            return
        try:
            table.check_can_join(user_tg_id)
        except TableError as e:
            await update.message.reply_text(t(e.key, lang, **e.kwargs))
            return

        # 잔액 차감 커밋 → 착석 (1인 게임과 동일한 순서)
        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            if not user:
                await update.message.reply_text(t("deal_no_user", lang))
                return
            bet_amount = bet_request.resolve(user.wallet)
            if not is_valid_amount(bet_amount) or not user.deduct_wallet(bet_amount):
                await update.message.reply_text(
                    t("deal_no_balance", lang, balance=float(user.wallet))
                )
                return
            db.commit()

        name = update.effective_user.first_name or str(user_tg_id)
        seat = table.join(user_tg_id, name, bet_amount)
        _persist_tables()

        await update.message.reply_text(
            t(
                "table_joined",
                table.lang,
                name=escape(seat.name),
                bet=bet_amount,
                n=len(table.seats),
            ),
            parse_mode=ParseMode.HTML,
        )
        await _show_betting(context.bot, table)


async def cmd_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /leave - 베팅 단계에서 퇴장 (베팅 반환)

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    lang = _user_lang(user_tg_id)
    if not _is_group(update):
        await update.message.reply_text(t("table_group_only", lang))
        return

    chat_id = update.effective_chat.id
    async with _lock(chat_id):
        table = table_sessions.get(chat_id)
        if table is None:
            await update.message.reply_text(t("table_none", lang))
            return
        seat = table.seat_of(user_tg_id)
        if seat is None:
            await update.message.reply_text(t("table_not_seated", lang))
            return
        if table.phase is not TablePhase.BETTING:
            await update.message.reply_text(t("table_leave_playing", lang))
            return

        # 환불 커밋 → 좌석 제거 (정산 순서 불변식과 동일)
        refund = seat.game.total_bet
        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            user.add_wallet(refund)
            db.commit()
        table.leave(user_tg_id)
        _persist_tables()

        await update.message.reply_text(
            t("table_left", table.lang, name=escape(seat.name), bet=refund),
            parse_mode=ParseMode.HTML,
        )
        await _show_betting(context.bot, table)


# ── 버튼 콜백 ─────────────────────────────────────────────────


async def table_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    멀티 테이블 버튼(tbl_*) 콜백 — 차례인 플레이어만 액션 가능

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    query = update.callback_query
    user_tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    lang = _user_lang(user_tg_id)
    command = query.data.removeprefix("tbl_")

    async with _lock(chat_id):
        if command == "new":
            await query.answer()
            await _open_or_resume(context.bot, chat_id, user_tg_id, lang)
            return

        table = table_sessions.get(chat_id)
        if table is None:
            await query.answer(t("table_none", lang), show_alert=True)
            return

        if command == "deal":
            if user_tg_id != table.host_id:
                await query.answer(t("table_host_only", lang), show_alert=True)
                return
            if table.phase is not TablePhase.BETTING:
                await query.answer()
                return
            await _answer_quietly(query)
            await _start_round(context.bot, table)
            return

        try:
            action = TableAction(command)
        except ValueError:
            await query.answer()
            return

        try:
            error = _pay_action_cost(table, user_tg_id, action, lang)
        except TableError as e:
            await query.answer(t(e.key, lang, **e.kwargs), show_alert=True)
            return
        if error:
            await query.answer(error, show_alert=True)
            return

        seat = table.current_seat
        hand_index = seat.game.active_index
        table.apply(user_tg_id, action)
        _cancel_timer(chat_id)
        _persist_tables()
        await _answer_quietly(query)

        notice = _action_notice(table, seat, action, hand_index)
        turn_moved = table.current_seat is not seat
        await _advance(context.bot, table, notice=notice, new_message=turn_moved)


# ── 재시작 복구 ───────────────────────────────────────────────


async def resume_tables(bot: Bot) -> None:
    """봇 시작 시 복원된 테이블의 메시지/타이머 재개 (post_init에서 호출)"""
    for table in list(table_sessions.values()):
        try:
            async with _lock(table.chat_id):
                await _resume(bot, table)
        except Exception:
            logger.exception(f"테이블 재개 실패 (chat={table.chat_id})")
