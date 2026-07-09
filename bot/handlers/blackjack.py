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
    InputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import ContextTypes
from models import get_db, User, Group, Round, GameOutcome, PlanType
from bot.utils import (
    Deck,
    calculate_hand_value,
    is_blackjack,
    is_bust,
    determine_outcome,
    PayoutCalculator,
    should_show_game_ad,
    get_ad_footer,
    t,
    get_user_lang,
)
from bot.utils.casino_card_renderer import get_casino_renderer
from bot.utils.themes import ThemeManager

logger = logging.getLogger(__name__)

# 게임 상태 저장소 (메모리 기반)
# 실전에서는 Redis 등 사용 권장
game_sessions: Dict[int, Dict] = {}


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


def _get_game_keyboard():
    """
    게임 진행 중 사용 가능한 인라인 키보드 생성

    Returns:
        InlineKeyboardMarkup: 게임 명령어 버튼 키보드
    """
    keyboard = [
        [
            InlineKeyboardButton("HIT", callback_data="game_hit"),
            InlineKeyboardButton("STAND", callback_data="game_stand"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def _render_game_image(
    game: "BlackjackGame",
    theme,
    lang: str,
    message: str,
    reveal_dealer: bool = False,
    player_hand: Optional[List[str]] = None,
) -> bytes:
    """
    게임 상태 이미지 렌더링 (공통 헬퍼)

    Args:
        game: 게임 객체
        theme: 카드 테마
        lang: 언어 코드
        message: 이미지 하단 메시지
        reveal_dealer: 딜러 첫 카드 공개 여부
        player_hand: 플레이어 핸드 오버라이드 (애니메이션용, 예: 뒷면 카드 추가)

    Returns:
        bytes: 렌더링된 이미지
    """
    hand = player_hand if player_hand is not None else game.player_hand
    dealer_value = (
        calculate_hand_value(game.dealer_hand) if reveal_dealer else None
    )
    return get_casino_renderer(theme).generate_game_image(
        player_hand=hand,
        dealer_hand=game.dealer_hand,
        player_value=calculate_hand_value(game.player_hand),
        dealer_value=dealer_value,
        hide_dealer_first=not reveal_dealer,
        message=message,
        dealer_label=t("img_dealer", lang),
        player_label=t("img_player", lang),
        value_label=t("img_total", lang),
    )


class BlackjackGame:
    """블랙잭 게임 로직 클래스"""

    def __init__(self, user_id: int, bet: float):
        """
        게임 초기화

        Args:
            user_id: 사용자 ID
            bet: 베팅 금액
        """
        self.user_id = user_id
        self.bet = bet
        self.deck = Deck(num_decks=6)  # 6덱 사용
        self.player_hand = []
        self.dealer_hand = []
        self.is_finished = False

    def deal_initial(self):
        """초기 카드 2장씩 딜"""
        self.player_hand = self.deck.draw_multiple(2)
        self.dealer_hand = self.deck.draw_multiple(2)

    def player_hit(self):
        """플레이어 히트"""
        card = self.deck.draw()
        self.player_hand.append(card)

    def dealer_play(self):
        """딜러 자동 플레이 (17 이상까지)"""
        while calculate_hand_value(self.dealer_hand) < 17:
            card = self.deck.draw()
            self.dealer_hand.append(card)

    def get_result(self) -> tuple:
        """
        게임 결과 계산

        Returns:
            tuple: (outcome, payout)
        """
        player_value = calculate_hand_value(self.player_hand)
        dealer_value = calculate_hand_value(self.dealer_hand)
        player_blackjack = is_blackjack(self.player_hand)
        dealer_blackjack = is_blackjack(self.dealer_hand)
        player_bust = is_bust(self.player_hand)
        dealer_bust = is_bust(self.dealer_hand)

        outcome = determine_outcome(
            player_value,
            dealer_value,
            player_blackjack,
            dealer_blackjack,
            player_bust,
            dealer_bust,
        )

        payout = PayoutCalculator.calculate(outcome, self.bet)
        return outcome, payout


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
        keyboard = [[InlineKeyboardButton(
            t("btn_start_dm", lang),
            url=f"https://t.me/{bot_username}?start=play"
        )]]
        await update.message.reply_text(
            t("group_redirect", lang, name=update.effective_user.first_name),
            reply_markup=InlineKeyboardMarkup(keyboard)
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
            await update.message.reply_text(t("deal_no_balance", lang, balance=float(user.wallet)))
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
        await _finish_game(update, user_tg_id, game, outcome, payout)
        return

    # 사용자 테마 가져오기 및 럭셔리 카드 이미지 생성
    theme = _get_user_theme(user_tg_id, chat_id)
    image_bytes = _render_game_image(game, theme, lang, t("hint_commands", lang))

    theme_name = f" [{theme.name}]" if theme.name != "Classic" else ""
    caption = t("deal_caption", lang, theme=theme_name, bet=bet_amount)
    await update.message.reply_photo(
        photo=BytesIO(image_bytes), caption=caption, reply_markup=_get_game_keyboard()
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

    # 버스트 체크
    if is_bust(game.player_hand):
        outcome = GameOutcome.BUST
        payout = PayoutCalculator.calculate(outcome, game.bet)
        await _finish_game(update, user_tg_id, game, outcome, payout)
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
    /stand - 멈춤 (딜러 차례)

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

    # 딜러 플레이
    game.dealer_play()

    # 결과 계산
    outcome, payout = game.get_result()

    # 게임 종료
    await _finish_game(update, user_tg_id, game, outcome, payout)


def _settle_game(
    user_tg_id: int,
    game: BlackjackGame,
    outcome: GameOutcome,
    payout: float,
    chat_id: int,
) -> Dict:
    """
    게임 결과 DB 정산 (지갑 반영, 통계 갱신, 라운드 기록)

    Args:
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        outcome: 게임 결과
        payout: 정산 금액
        chat_id: 채팅 ID

    Returns:
        Dict: 렌더링에 필요한 정산 결과 정보
    """
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        group = db.query(Group).filter(Group.chat_id == chat_id).first()

        if outcome == GameOutcome.PUSH:
            user.add_wallet(game.bet)
        elif payout > 0:
            user.add_wallet(game.bet + payout)

        user.update_stats(
            total_games=1,
            wins=1 if outcome in (GameOutcome.WIN, GameOutcome.BLACKJACK) else 0,
            losses=1 if outcome in (GameOutcome.LOSS, GameOutcome.BUST) else 0,
            total_bet=float(game.bet),
            total_profit=float(payout),
        )

        db.add(Round(
            user_id=user.id,
            chat_id=chat_id,
            bet=game.bet,
            player_hand=game.player_hand,
            dealer_hand=game.dealer_hand,
            outcome=outcome,
            payout=payout,
        ))
        db.commit()

        return {
            "wallet": float(user.wallet),
            "is_free": group.plan == PlanType.FREE if group else True,
            "is_vip": user.is_vip_active,
            "is_business": group.plan == PlanType.BUSINESS if group else False,
        }


def _render_game_result(
    game: BlackjackGame,
    outcome: GameOutcome,
    payout: float,
    settle_info: Dict,
    lang: str = "ko",
) -> Tuple[bytes, str, InlineKeyboardMarkup]:
    """
    게임 결과 이미지/캡션/키보드 생성 (DB 접근 없음)

    Args:
        game: 게임 객체
        outcome: 게임 결과
        payout: 정산 금액
        settle_info: _settle_game이 반환한 정산 결과 정보
        lang: 언어 코드

    Returns:
        Tuple[bytes, str, InlineKeyboardMarkup]: (이미지, 캡션, 키보드)
    """
    player_value = calculate_hand_value(game.player_hand)
    dealer_value = calculate_hand_value(game.dealer_hand)

    outcome_emoji = PayoutCalculator.get_result_emoji(outcome)
    outcome_key = {
        GameOutcome.BLACKJACK: "result_blackjack",
        GameOutcome.WIN: "result_win",
        GameOutcome.PUSH: "result_push",
        GameOutcome.LOSS: "result_lose",
        GameOutcome.BUST: "result_bust",
    }.get(outcome, "result_lose")
    outcome_msg = t(outcome_key, lang)
    payout_str = PayoutCalculator.format_payout(payout)

    result_message = "\n".join([
        "--------------------",
        f"{outcome_emoji} {t('result_label', lang)}: {outcome_msg}",
        "--------------------",
        "",
        f"{t('player_label', lang)}: {player_value}",
        f"{t('dealer_label', lang)}: {dealer_value}",
        "",
        f"{t('bet_label', lang)}: ${game.bet:,.2f}",
        f"{t('payout_label', lang)}: {payout_str}",
        f"{t('balance_label', lang)}: ${settle_info['wallet']:,.2f}",
        "--------------------",
    ])

    if should_show_game_ad(settle_info["is_free"]):
        result_message += get_ad_footer(show_ad=True)

    theme = ThemeManager.get_theme_by_plan(
        settle_info["is_vip"], settle_info["is_business"]
    )
    image_bytes = _render_game_image(
        game, theme, lang, result_message, reveal_dealer=True
    )

    theme_badge = f" [{theme.name}]" if theme.name != "Classic" else ""
    caption = f"{outcome_msg} {t('game_over_suffix', lang)}{theme_badge}"

    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("btn_play_again", lang), callback_data="restart_game")]]
    )

    return image_bytes, caption, reply_markup


async def _finish_game(
    update: Update,
    user_tg_id: int,
    game: BlackjackGame,
    outcome: GameOutcome,
    payout: float,
):
    """
    /hit, /stand 명령어를 통한 게임 종료 처리

    Args:
        update: 업데이트 객체
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        outcome: 게임 결과
        payout: 정산 금액
    """
    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 정산이 커밋된 직후 세션 제거 (전송 실패 시 이중 정산 방지)
    settle_info = _settle_game(
        user_tg_id, game, outcome, payout, update.effective_chat.id
    )
    game_sessions.pop(user_tg_id, None)

    image_bytes, caption, reply_markup = _render_game_result(
        game, outcome, payout, settle_info, lang
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
            t("daily_reward", lang, reward=reward, bonus=bonus, balance=float(user.wallet))
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
            media=InputMediaPhoto(
                media=BytesIO(back_image_bytes), caption=drawing_msg
            ),
            reply_markup=_get_game_keyboard(),
        )

        # 짧은 딜레이 (카드 뒤집기 효과)
        await asyncio.sleep(0.6)

        # 실제 카드 추가
        game.player_hit()

        # 버스트 체크
        if is_bust(game.player_hand):
            outcome = GameOutcome.BUST
            payout = PayoutCalculator.calculate(outcome, game.bet)
            await _finish_game_callback(
                query, user_tg_id, game, outcome, payout, chat_id
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
        # STAND 로직
        game.dealer_play()
        outcome, payout = game.get_result()
        await _finish_game_callback(query, user_tg_id, game, outcome, payout, chat_id)


async def _finish_game_callback(
    query,
    user_tg_id: int,
    game: BlackjackGame,
    outcome: GameOutcome,
    payout: float,
    chat_id: int,
):
    """
    인라인 버튼을 통한 게임 종료 처리

    Args:
        query: 콜백 쿼리 객체
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        outcome: 게임 결과
        payout: 정산 금액
        chat_id: 채팅 ID
    """
    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

    # 정산이 커밋된 직후 세션 제거 (전송 실패 시 이중 정산 방지)
    settle_info = _settle_game(user_tg_id, game, outcome, payout, chat_id)
    game_sessions.pop(user_tg_id, None)

    image_bytes, caption, reply_markup = _render_game_result(
        game, outcome, payout, settle_info, lang
    )
    await query.edit_message_media(
        media=InputMediaPhoto(media=BytesIO(image_bytes), caption=caption),
        reply_markup=reply_markup,
    )
