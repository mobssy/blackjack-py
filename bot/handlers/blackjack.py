"""
JackPy - 블랙잭 게임 핸들러
/deal, /hit, /stand 명령어 처리
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from io import BytesIO
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import ContextTypes
from models import get_db, User, Group, Round, GameOutcome, PlanType
from bot.utils import (
    calculate_hand_value,
    is_blackjack,
    is_bust,
    PayoutCalculator,
    should_show_game_ad,
    get_ad_footer,
    t,
    get_user_lang,
)
from bot.utils.blackjack_game import BlackjackGame
from bot.utils.session_store import load_sessions, save_sessions
from bot.utils.casino_card_renderer import get_casino_renderer
from bot.utils.themes import ThemeManager

logger = logging.getLogger(__name__)

# 게임 상태 저장소 (메모리 + JSON 파일 영속화)
# 봇 재시작 시 진행 중이던 게임(차감된 베팅)이 유실되지 않도록 복원한다
game_sessions: Dict[int, BlackjackGame] = load_sessions()


def _persist_sessions() -> None:
    """게임 상태 변경 시점마다 세션을 파일에 반영"""
    save_sessions(game_sessions)


def _get_user_theme(user_tg_id: int, chat_id: int):
    """
    사용자 테마 가져오기

    Args:
        user_tg_id: 사용자 텔레그램 ID
        chat_id: 채팅 ID

    Returns:
        Theme: 사용자 테마
    """
    with get_db() as db:
        user_obj = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        group = db.query(Group).filter(Group.chat_id == chat_id).first()

        is_vip = user_obj.is_vip_active if user_obj else False
        is_business = group.plan == PlanType.BUSINESS if group else False

        return ThemeManager.get_theme_by_plan(is_vip, is_business)


def _get_game_keyboard(first_turn: bool = False, can_split: bool = False):
    """
    게임 진행 중 사용 가능한 인라인 키보드 생성

    Args:
        first_turn: 첫 턴(첫 2장) 여부 — 더블 다운/서렌더 버튼 표시 조건
        can_split: 스플릿 가능 여부 — SPLIT 버튼 표시 조건

    Returns:
        InlineKeyboardMarkup: 게임 명령어 버튼 키보드
    """
    keyboard = [
        [
            InlineKeyboardButton("HIT", callback_data="game_hit"),
            InlineKeyboardButton("STAND", callback_data="game_stand"),
        ]
    ]
    if first_turn:
        second_row = [
            InlineKeyboardButton("DOUBLE", callback_data="game_double"),
            InlineKeyboardButton("SURRENDER", callback_data="game_surrender"),
        ]
        if can_split:
            second_row.append(InlineKeyboardButton("SPLIT", callback_data="game_split"))
        keyboard.append(second_row)
    return InlineKeyboardMarkup(keyboard)


def _render_game_image(
    game: "BlackjackGame",
    theme,
    lang: str,
    message: str,
    reveal_dealer: bool = False,
    player_hand: Optional[List[str]] = None,
    player_value=None,
) -> bytes:
    """
    게임 상태 이미지 렌더링 (공통 헬퍼)

    Args:
        game: 게임 객체
        theme: 카드 테마
        lang: 언어 코드
        message: 이미지 하단 메시지
        reveal_dealer: 딜러 첫 카드 공개 여부
        player_hand: 플레이어 핸드 오버라이드 (애니메이션/스플릿 합산 표시용)
        player_value: 값 칩 표시 오버라이드 (스플릿 시 "18 / 21" 형태 문자열)

    Returns:
        bytes: 렌더링된 이미지
    """
    hand = player_hand if player_hand is not None else game.player_hand
    if player_value is None:
        player_value = calculate_hand_value(game.player_hand)
    dealer_value = calculate_hand_value(game.dealer_hand) if reveal_dealer else None
    return get_casino_renderer(theme).generate_game_image(
        player_hand=hand,
        dealer_hand=game.dealer_hand,
        player_value=player_value,
        dealer_value=dealer_value,
        hide_dealer_first=not reveal_dealer,
        message=message,
        dealer_label=t("img_dealer", lang),
        player_label=t("img_player", lang),
        value_label=t("img_total", lang),
    )


def _all_hands_results(game: BlackjackGame) -> List[Tuple[GameOutcome, float]]:
    """
    모든 핸드 플레이 종료 후 결과 계산

    버스트되지 않은 핸드가 하나라도 있으면 딜러가 플레이한 뒤
    핸드별 결과를 반환한다.

    Args:
        game: 게임 객체

    Returns:
        List[Tuple[GameOutcome, float]]: 핸드별 (outcome, payout)
    """
    if game.any_hand_alive():
        game.dealer_play()
    return game.get_results()


def _hand_progress_caption(game: BlackjackGame, lang: str) -> str:
    """현재 플레이 중인 핸드 안내 문구 (스플릿 진행용)"""
    return t("hand_playing", lang, n=game.hand_number, total=game.hand_count)


async def cmd_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /deal [금액] - 블랙잭 게임 시작

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # 사용자 언어 조회
    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 단체방에서 호출된 경우 DM으로 유도
    if update.effective_chat.type in ("group", "supergroup"):
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

    # 베팅 금액 파싱
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(t("deal_usage", lang))
        return

    try:
        bet_amount = float(context.args[0])
        if bet_amount <= 0:
            await update.message.reply_text(t("deal_positive", lang))
            return
    except ValueError:
        await update.message.reply_text(t("deal_invalid", lang))
        return

    # 사용자 조회
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user:
            await update.message.reply_text(t("deal_no_user", lang))
            return

        # 잔액 확인
        if user.wallet < bet_amount:
            await update.message.reply_text(
                t("deal_no_balance", lang, balance=float(user.wallet))
            )
            return

        # 이미 게임 중인지 확인
        if user_tg_id in game_sessions:
            await update.message.reply_text(t("deal_in_progress", lang))
            return

        # 잔액 차감
        user.deduct_wallet(bet_amount)
        db.commit()

    # 게임 시작
    game = BlackjackGame(user_tg_id, bet_amount)
    game.deal_initial()
    game_sessions[user_tg_id] = game
    _persist_sessions()

    # 블랙잭 체크
    if is_blackjack(game.player_hand):
        # 딜러도 블랙잭인지 확인
        if is_blackjack(game.dealer_hand):
            outcome = GameOutcome.PUSH
            payout = 0
        else:
            outcome = GameOutcome.BLACKJACK
            payout = PayoutCalculator.calculate(outcome, bet_amount)

        # 게임 종료
        await _finish_game(update, user_tg_id, game, [(outcome, payout)])
        return

    # 사용자 테마 가져오기 및 럭셔리 카드 이미지 생성
    theme = _get_user_theme(user_tg_id, chat_id)
    image_bytes = _render_game_image(game, theme, lang, t("hint_commands_first", lang))

    theme_name = f" [{theme.name}]" if theme.name != "Classic" else ""
    caption = t("deal_caption", lang, theme=theme_name, bet=bet_amount)
    await update.message.reply_photo(
        photo=BytesIO(image_bytes),
        caption=caption,
        reply_markup=_get_game_keyboard(first_turn=True, can_split=game.can_split),
    )


async def cmd_hit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /hit - 카드 한 장 추가

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 게임 세션 확인
    if user_tg_id not in game_sessions:
        await update.message.reply_text(t("no_game", lang))
        return

    game = game_sessions[user_tg_id]

    # 카드 추가
    game.player_hit()
    _persist_sessions()

    # 버스트 체크
    if is_bust(game.player_hand):
        busted_number = game.hand_number
        if game.advance_hand():
            _persist_sessions()
            # 스플릿: 다음 핸드로 진행
            caption = t(
                "hand_bust_next",
                lang,
                n=busted_number,
                next=game.hand_number,
                total=game.hand_count,
            )
            theme = _get_user_theme(user_tg_id, chat_id)
            image_bytes = _render_game_image(game, theme, lang, caption)
            await update.message.reply_photo(
                photo=BytesIO(image_bytes),
                caption=caption,
                reply_markup=_get_game_keyboard(),
            )
            return
        await _finish_game(update, user_tg_id, game, _all_hands_results(game))
        return

    theme = _get_user_theme(user_tg_id, chat_id)
    image_bytes = _render_game_image(game, theme, lang, t("hint_commands", lang))

    caption = t("card_drawn", lang)
    await update.message.reply_photo(
        photo=BytesIO(image_bytes),
        caption=caption,
        reply_markup=_get_game_keyboard(),
    )


async def cmd_stand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /stand - 멈춤 (다음 핸드 또는 딜러 차례)

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 게임 세션 확인
    if user_tg_id not in game_sessions:
        await update.message.reply_text(t("no_game", lang))
        return

    game = game_sessions[user_tg_id]

    # 스플릿: 다음 핸드가 남아 있으면 이동
    if game.advance_hand():
        _persist_sessions()
        caption = _hand_progress_caption(game, lang)
        theme = _get_user_theme(user_tg_id, chat_id)
        image_bytes = _render_game_image(game, theme, lang, caption)
        await update.message.reply_photo(
            photo=BytesIO(image_bytes),
            caption=caption,
            reply_markup=_get_game_keyboard(),
        )
        return

    # 모든 핸드 종료 → 딜러 플레이 및 게임 종료
    await _finish_game(update, user_tg_id, game, _all_hands_results(game))


def _try_double(user_tg_id: int, game: BlackjackGame, lang: str) -> Optional[str]:
    """
    더블 다운 검증 및 실행 (추가 베팅 차감 + 카드 1장)

    Args:
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        lang: 언어 코드

    Returns:
        Optional[str]: 실패 시 에러 메시지, 성공 시 None
    """
    if not game.is_first_turn:
        return t("double_only_first", lang)

    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user or not user.deduct_wallet(game.bet):
            balance = float(user.wallet) if user else 0.0
            return t("double_no_balance", lang, balance=balance)
        db.commit()

    game.player_double()
    _persist_sessions()
    return None


def _double_result(game: BlackjackGame) -> List[Tuple[GameOutcome, float]]:
    """
    더블 다운 이후 결과 계산 (버스트가 아니면 자동 스탠드)

    Args:
        game: 게임 객체

    Returns:
        List[Tuple[GameOutcome, float]]: 핸드별 (outcome, payout)
    """
    return _all_hands_results(game)


def _try_split(user_tg_id: int, game: BlackjackGame, lang: str) -> Optional[str]:
    """
    스플릿 검증 및 실행 (추가 베팅 차감 + 핸드 분리)

    Args:
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        lang: 언어 코드

    Returns:
        Optional[str]: 실패 시 에러 메시지, 성공 시 None
    """
    if not game.can_split:
        return t("split_not_allowed", lang)

    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user or not user.deduct_wallet(game.bet):
            balance = float(user.wallet) if user else 0.0
            return t("split_no_balance", lang, balance=balance)
        db.commit()

    game.split()
    _persist_sessions()
    return None


async def cmd_double(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /double - 더블 다운 (첫 두 장에서만, 베팅 2배 + 카드 1장 후 자동 스탠드)

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 게임 세션 확인
    if user_tg_id not in game_sessions:
        await update.message.reply_text(t("no_game", lang))
        return

    game = game_sessions[user_tg_id]

    error = _try_double(user_tg_id, game, lang)
    if error:
        await update.message.reply_text(error)
        return

    await _finish_game(update, user_tg_id, game, _double_result(game))


async def cmd_surrender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /surrender - 서렌더 (첫 두 장에서만, 베팅액 절반 회수)

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 게임 세션 확인
    if user_tg_id not in game_sessions:
        await update.message.reply_text(t("no_game", lang))
        return

    game = game_sessions[user_tg_id]

    if not game.is_first_turn:
        await update.message.reply_text(t("surrender_only_first", lang))
        return

    await _finish_game(update, user_tg_id, game, [game.surrender_result()])


async def cmd_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /split - 스플릿 (첫 두 장이 같은 랭크일 때, 두 핸드로 분리)

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 게임 세션 확인
    if user_tg_id not in game_sessions:
        await update.message.reply_text(t("no_game", lang))
        return

    game = game_sessions[user_tg_id]

    error = _try_split(user_tg_id, game, lang)
    if error:
        await update.message.reply_text(error)
        return

    # 에이스 스플릿: 각 핸드 카드 1장씩 받고 자동 스탠드
    if game.split_rank == "A":
        await update.message.reply_text(t("split_aces_note", lang))
        await _finish_game(update, user_tg_id, game, _all_hands_results(game))
        return

    # 핸드 1부터 플레이
    caption = _hand_progress_caption(game, lang)
    theme = _get_user_theme(user_tg_id, chat_id)
    image_bytes = _render_game_image(game, theme, lang, caption)
    await update.message.reply_photo(
        photo=BytesIO(image_bytes),
        caption=t("split_caption", lang, bet=game.bet) + "\n" + caption,
        reply_markup=_get_game_keyboard(),
    )


def _settle_game(
    user_tg_id: int,
    game: BlackjackGame,
    results: List[Tuple[GameOutcome, float]],
    chat_id: int,
) -> Dict:
    """
    게임 결과 DB 정산 (지갑 반영, 통계 갱신, 핸드별 라운드 기록)

    Args:
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        results: 핸드별 (outcome, payout) 리스트
        chat_id: 채팅 ID

    Returns:
        Dict: 렌더링에 필요한 정산 결과 정보
    """
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        group = db.query(Group).filter(Group.chat_id == chat_id).first()

        wins = losses = 0
        for (outcome, payout), hand, bet in zip(results, game.hands, game.bets):
            if outcome == GameOutcome.PUSH:
                user.add_wallet(bet)
            elif outcome == GameOutcome.SURRENDER:
                # 베팅액 절반 회수 (payout = -bet/2)
                user.add_wallet(bet + payout)
            elif payout > 0:
                user.add_wallet(bet + payout)

            if outcome in (GameOutcome.WIN, GameOutcome.BLACKJACK):
                wins += 1
            elif outcome in (GameOutcome.LOSS, GameOutcome.BUST, GameOutcome.SURRENDER):
                losses += 1

            db.add(
                Round(
                    user_id=user.id,
                    chat_id=chat_id,
                    bet=bet,
                    player_hand=hand,
                    dealer_hand=game.dealer_hand,
                    outcome=outcome,
                    payout=payout,
                )
            )

        user.update_stats(
            total_games=len(results),
            wins=wins,
            losses=losses,
            total_bet=float(game.total_bet),
            total_profit=float(sum(payout for _, payout in results)),
        )
        db.commit()

        return {
            "wallet": float(user.wallet),
            "is_free": group.plan == PlanType.FREE if group else True,
            "is_vip": user.is_vip_active,
            "is_business": group.plan == PlanType.BUSINESS if group else False,
        }


def _outcome_text(outcome: GameOutcome, lang: str) -> str:
    """결과 enum에 대응하는 번역 문자열"""
    outcome_key = {
        GameOutcome.BLACKJACK: "result_blackjack",
        GameOutcome.WIN: "result_win",
        GameOutcome.PUSH: "result_push",
        GameOutcome.LOSS: "result_lose",
        GameOutcome.BUST: "result_bust",
        GameOutcome.SURRENDER: "result_surrender",
    }.get(outcome, "result_lose")
    return t(outcome_key, lang)


def _render_game_result(
    game: BlackjackGame,
    results: List[Tuple[GameOutcome, float]],
    settle_info: Dict,
    lang: str = "ko",
) -> Tuple[bytes, str, InlineKeyboardMarkup]:
    """
    게임 결과 이미지/캡션/키보드 생성 (DB 접근 없음)

    Args:
        game: 게임 객체
        results: 핸드별 (outcome, payout) 리스트
        settle_info: _settle_game이 반환한 정산 결과 정보
        lang: 언어 코드

    Returns:
        Tuple[bytes, str, InlineKeyboardMarkup]: (이미지, 캡션, 키보드)
    """
    dealer_value = calculate_hand_value(game.dealer_hand)
    hand_values = [calculate_hand_value(hand) for hand in game.hands]
    total_payout = sum(payout for _, payout in results)
    payout_str = PayoutCalculator.format_payout(total_payout)

    if len(results) == 1:
        # 단일 핸드
        outcome, _ = results[0]
        outcome_msg = _outcome_text(outcome, lang)
        outcome_emoji = PayoutCalculator.get_result_emoji(outcome)
        header_line = f"{outcome_emoji} {t('result_label', lang)}: {outcome_msg}"
        player_lines = [f"{t('player_label', lang)}: {hand_values[0]}"]
        caption_head = outcome_msg
        image_hand = None  # 활성 핸드 (= 유일한 핸드)
        image_value = None
    else:
        # 스플릿: 핸드별 결과 표시
        hand_label = t("hand_label", lang)
        header_line = f"🃏 {t('result_label', lang)}"
        player_lines = []
        caption_parts = []
        for i, ((outcome, payout), value) in enumerate(zip(results, hand_values), 1):
            outcome_msg = _outcome_text(outcome, lang)
            emoji = PayoutCalculator.get_result_emoji(outcome)
            player_lines.append(
                f"{emoji} {hand_label}{i}: {value} — {outcome_msg} "
                f"({PayoutCalculator.format_payout(payout)})"
            )
            caption_parts.append(f"{hand_label}{i} {outcome_msg}")
        caption_head = " / ".join(caption_parts)
        image_hand = [card for hand in game.hands for card in hand]
        image_value = " / ".join(str(v) for v in hand_values)

    result_message = "\n".join(
        [
            "--------------------",
            header_line,
            "--------------------",
            "",
            *player_lines,
            f"{t('dealer_label', lang)}: {dealer_value}",
            "",
            f"{t('bet_label', lang)}: ${game.total_bet:,.2f}",
            f"{t('payout_label', lang)}: {payout_str}",
            f"{t('balance_label', lang)}: ${settle_info['wallet']:,.2f}",
            "--------------------",
        ]
    )

    if should_show_game_ad(settle_info["is_free"]):
        result_message += get_ad_footer(show_ad=True)

    theme = ThemeManager.get_theme_by_plan(
        settle_info["is_vip"], settle_info["is_business"]
    )
    image_bytes = _render_game_image(
        game,
        theme,
        lang,
        result_message,
        reveal_dealer=True,
        player_hand=image_hand,
        player_value=image_value,
    )

    theme_badge = f" [{theme.name}]" if theme.name != "Classic" else ""
    caption = f"{caption_head} {t('game_over_suffix', lang)}{theme_badge}"

    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("btn_play_again", lang), callback_data="restart_game"
                )
            ]
        ]
    )

    return image_bytes, caption, reply_markup


async def _finish_game(
    update: Update,
    user_tg_id: int,
    game: BlackjackGame,
    results: List[Tuple[GameOutcome, float]],
):
    """
    명령어를 통한 게임 종료 처리

    Args:
        update: 업데이트 객체
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        results: 핸드별 (outcome, payout) 리스트
    """
    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 정산이 커밋된 직후 세션 제거 (전송 실패 시 이중 정산 방지)
    settle_info = _settle_game(user_tg_id, game, results, update.effective_chat.id)
    game_sessions.pop(user_tg_id, None)
    _persist_sessions()

    image_bytes, caption, reply_markup = _render_game_result(
        game, results, settle_info, lang
    )
    await update.message.reply_photo(
        photo=BytesIO(image_bytes), caption=caption, reply_markup=reply_markup
    )


async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /wallet - 잔액 확인

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(user)
        if not user:
            await update.message.reply_text(t("deal_no_user", lang))
            return

        stats = user.stats_json or {}
        vip_status = t("vip_active" if user.is_vip_active else "vip_inactive", lang)
        message = t(
            "wallet_full",
            lang,
            balance=float(user.wallet),
            vip=vip_status,
            games=stats.get("total_games", 0),
            wins=stats.get("wins", 0),
            losses=stats.get("losses", 0),
            profit=stats.get("total_profit", 0),
        )
        await update.message.reply_text(message)


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /daily - 일일 보상

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(user)
        if not user:
            await update.message.reply_text(t("deal_no_user", lang))
            return

        # 일일 보상 수령 가능 여부 확인
        if not user.can_claim_daily():
            await update.message.reply_text(t("daily_already", lang))
            return

        # 보상 지급
        is_vip = user.is_vip_active
        reward = 500.0 if is_vip else 200.0
        user.add_wallet(reward)
        user.last_daily_at = datetime.now(timezone.utc)
        db.commit()

        bonus = t("daily_vip_bonus", lang) if is_vip else ""
        await update.message.reply_text(
            t(
                "daily_reward",
                lang,
                reward=reward,
                bonus=bonus,
                balance=float(user.wallet),
            )
        )


async def game_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    게임 버튼 클릭 콜백 핸들러

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    query = update.callback_query
    await query.answer()

    user_tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 게임 세션 확인
    if user_tg_id not in game_sessions:
        await query.edit_message_caption(caption=t("no_game", lang))
        return

    game = game_sessions[user_tg_id]

    # callback_data에 따라 적절한 명령어 실행
    if query.data == "game_hit":
        # 먼저 뒷면 카드가 추가된 이미지 표시 (카드 뒤집기 연출)
        theme = _get_user_theme(user_tg_id, chat_id)
        drawing_msg = t("drawing_card", lang)
        back_image_bytes = _render_game_image(
            game,
            theme,
            lang,
            drawing_msg,
            player_hand=game.player_hand + ["BACK"],
        )

        await query.edit_message_media(
            media=InputMediaPhoto(media=BytesIO(back_image_bytes), caption=drawing_msg),
            reply_markup=_get_game_keyboard(),
        )

        # 짧은 딜레이 (카드 뒤집기 효과)
        await asyncio.sleep(0.6)

        # 실제 카드 추가
        game.player_hit()
        _persist_sessions()

        # 버스트 체크
        if is_bust(game.player_hand):
            busted_number = game.hand_number
            if game.advance_hand():
                _persist_sessions()
                # 스플릿: 다음 핸드로 진행
                caption = t(
                    "hand_bust_next",
                    lang,
                    n=busted_number,
                    next=game.hand_number,
                    total=game.hand_count,
                )
                image_bytes = _render_game_image(game, theme, lang, caption)
                await query.edit_message_media(
                    media=InputMediaPhoto(media=BytesIO(image_bytes), caption=caption),
                    reply_markup=_get_game_keyboard(),
                )
                return
            await _finish_game_callback(
                query, user_tg_id, game, _all_hands_results(game), chat_id
            )
            return

        image_bytes = _render_game_image(game, theme, lang, t("hint_commands", lang))

        # 앞면 카드로 업데이트
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=BytesIO(image_bytes), caption=t("card_drawn", lang)
            ),
            reply_markup=_get_game_keyboard(),
        )

    elif query.data == "game_stand":
        # STAND 로직: 다음 핸드가 남아 있으면 이동, 아니면 게임 종료
        if game.advance_hand():
            _persist_sessions()
            caption = _hand_progress_caption(game, lang)
            theme = _get_user_theme(user_tg_id, chat_id)
            image_bytes = _render_game_image(game, theme, lang, caption)
            await query.edit_message_media(
                media=InputMediaPhoto(media=BytesIO(image_bytes), caption=caption),
                reply_markup=_get_game_keyboard(),
            )
            return
        await _finish_game_callback(
            query, user_tg_id, game, _all_hands_results(game), chat_id
        )

    elif query.data == "game_double":
        # DOUBLE 로직 (베팅 2배 + 카드 1장 후 자동 스탠드)
        error = _try_double(user_tg_id, game, lang)
        if error:
            await query.message.reply_text(error)
            return

        await _finish_game_callback(
            query, user_tg_id, game, _double_result(game), chat_id
        )

    elif query.data == "game_surrender":
        # SURRENDER 로직 (베팅액 절반 회수)
        if not game.is_first_turn:
            await query.message.reply_text(t("surrender_only_first", lang))
            return

        await _finish_game_callback(
            query, user_tg_id, game, [game.surrender_result()], chat_id
        )

    elif query.data == "game_split":
        # SPLIT 로직 (같은 랭크 2장을 두 핸드로 분리)
        error = _try_split(user_tg_id, game, lang)
        if error:
            await query.message.reply_text(error)
            return

        # 에이스 스플릿: 각 핸드 카드 1장씩 받고 자동 스탠드
        if game.split_rank == "A":
            await query.message.reply_text(t("split_aces_note", lang))
            await _finish_game_callback(
                query, user_tg_id, game, _all_hands_results(game), chat_id
            )
            return

        # 핸드 1부터 플레이
        caption = _hand_progress_caption(game, lang)
        theme = _get_user_theme(user_tg_id, chat_id)
        image_bytes = _render_game_image(game, theme, lang, caption)
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=BytesIO(image_bytes),
                caption=t("split_caption", lang, bet=game.bet) + "\n" + caption,
            ),
            reply_markup=_get_game_keyboard(),
        )


async def _finish_game_callback(
    query,
    user_tg_id: int,
    game: BlackjackGame,
    results: List[Tuple[GameOutcome, float]],
    chat_id: int,
):
    """
    인라인 버튼을 통한 게임 종료 처리

    Args:
        query: 콜백 쿼리 객체
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        results: 핸드별 (outcome, payout) 리스트
        chat_id: 채팅 ID
    """
    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 정산이 커밋된 직후 세션 제거 (전송 실패 시 이중 정산 방지)
    settle_info = _settle_game(user_tg_id, game, results, chat_id)
    game_sessions.pop(user_tg_id, None)
    _persist_sessions()

    image_bytes, caption, reply_markup = _render_game_result(
        game, results, settle_info, lang
    )
    await query.edit_message_media(
        media=InputMediaPhoto(media=BytesIO(image_bytes), caption=caption),
        reply_markup=reply_markup,
    )
