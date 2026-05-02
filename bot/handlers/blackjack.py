"""
JackPy - 블랙잭 게임 핸들러
/deal, /hit, /stand 명령어 처리
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Tuple
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
    get_hand_display,
    determine_outcome,
    PayoutCalculator,
    should_show_game_ad,
    get_ad_footer,
    t,
    get_user_lang,
)
from bot.utils.card_image import get_card_generator
from bot.utils.enhanced_card_image import get_enhanced_card_generator
from bot.utils.casino_card_renderer import get_casino_renderer
from bot.utils.themes import ThemeManager
from bot.utils.card_animation import get_animation_generator

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

    # 단체방에서 호출된 경우 DM으로 유도
    if update.effective_chat.type in ("group", "supergroup"):
        bot_username = context.bot.username
        keyboard = [[InlineKeyboardButton(
            "BlackJack 시작하기",
            url=f"https://t.me/{bot_username}?start=play"
        )]]
        await update.message.reply_text(
            f"{update.effective_user.first_name}님, 게임은 개인 채팅에서 진행됩니다!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # 사용자 언어 조회
    with get_db() as db:
        _u = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(_u)

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

    # 초기 카드 표시
    player_value = calculate_hand_value(game.player_hand)

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
    card_gen = get_casino_renderer(theme)
    image_bytes = card_gen.generate_game_image(
        player_hand=game.player_hand,
        dealer_hand=game.dealer_hand,
        player_value=player_value,
        dealer_value=None,
        hide_dealer_first=True,
        message="명령어: /hit (카드 추가) | /stand (멈춤)",
    )

    # 이미지 전송
    theme_name = f" [{theme.name} 에디션]" if theme.name != "Classic" else ""
    caption = f"블랙잭 시작!{theme_name}\n베팅: ${bet_amount:,.2f}"
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
    player_value = calculate_hand_value(game.player_hand)

    # 버스트 체크
    if is_bust(game.player_hand):
        outcome = GameOutcome.BUST
        payout = PayoutCalculator.calculate(outcome, game.bet)
        await _finish_game(update, user_tg_id, game, outcome, payout)
        return

    theme = _get_user_theme(user_tg_id, chat_id)
    card_gen = get_casino_renderer(theme)
    hit_msg = "Hit: /hit | Stand: /stand" if lang == "en" else "명령어: /hit (카드 추가) | /stand (멈춤)"
    image_bytes = card_gen.generate_game_image(
        player_hand=game.player_hand,
        dealer_hand=game.dealer_hand,
        player_value=player_value,
        dealer_value=None,
        hide_dealer_first=True,
        message=hit_msg,
    )

    caption = "Card drawn!" if lang == "en" else "카드를 한 장 더 받았습니다!"
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


def _build_game_result(
    user_tg_id: int,
    game: BlackjackGame,
    outcome: GameOutcome,
    payout: float,
    chat_id: int,
    lang: str = "ko",
) -> Tuple[bytes, str, InlineKeyboardMarkup]:
    player_value = calculate_hand_value(game.player_hand)
    dealer_value = calculate_hand_value(game.dealer_hand)

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

        player_label = t("player_label", lang)
        dealer_label = t("dealer_label", lang)
        bet_label = "Bet" if lang == "en" else "베팅 금액"
        payout_label = "Payout" if lang == "en" else "정산 금액"
        balance_label = "Balance" if lang == "en" else "현재 잔액"
        result_label = "Result" if lang == "en" else "게임 결과"

        result_message = "\n".join([
            "--------------------",
            f"{outcome_emoji} {result_label}: {outcome_msg}",
            "--------------------",
            "",
            f"{player_label}: {player_value}",
            f"{dealer_label}: {dealer_value}",
            "",
            f"{bet_label}: ${game.bet:,.2f}",
            f"{payout_label}: {payout_str}",
            f"{balance_label}: ${user.wallet:,.2f}",
            "--------------------",
        ])

        is_free = group.plan == PlanType.FREE if group else True
        if should_show_game_ad(is_free):
            result_message += get_ad_footer(show_ad=True)

        is_vip = user.is_vip_active
        is_business = group.plan == PlanType.BUSINESS if group else False
        theme = ThemeManager.get_theme_by_plan(is_vip, is_business)

        image_bytes = get_casino_renderer(theme).generate_game_image(
            player_hand=game.player_hand,
            dealer_hand=game.dealer_hand,
            player_value=player_value,
            dealer_value=dealer_value,
            hide_dealer_first=False,
            message=result_message,
        )

        game_over_label = "Game Over" if lang == "en" else "게임 종료"
        theme_badge = f" [{theme.name}]" if theme.name != "Classic" else ""
        caption = f"{outcome_msg} {game_over_label}{theme_badge}"

        restart_label = "Play Again" if lang == "en" else "다시 시작"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(restart_label, callback_data="restart_game")]]
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
    image_bytes, caption, reply_markup = _build_game_result(
        user_tg_id, game, outcome, payout, update.effective_chat.id, lang
    )
    await update.message.reply_photo(
        photo=BytesIO(image_bytes), caption=caption, reply_markup=reply_markup
    )
    game_sessions.pop(user_tg_id, None)


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
        if not user:
            await update.message.reply_text("[오류] 등록되지 않은 사용자입니다. /start를 먼저 실행해주세요.")
            return

        stats = user.stats_json or {}
        message = (
            f"지갑 정보\n\n"
            f"잔액: ${user.wallet:,.2f}\n"
            f"VIP: {'[활성]' if user.is_vip_active else '[비활성]'}\n\n"
            f"통계\n"
            f"총 게임: {stats.get('total_games', 0):,}회\n"
            f"승리: {stats.get('wins', 0):,}회\n"
            f"패배: {stats.get('losses', 0):,}회\n"
            f"총 수익: ${stats.get('total_profit', 0):,.2f}"
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
        if not user:
            await update.message.reply_text("[오류] 등록되지 않은 사용자입니다. /start를 먼저 실행해주세요.")
            return

        # 일일 보상 수령 가능 여부 확인
        if not user.can_claim_daily():
            await update.message.reply_text(
                "일일 보상은 하루에 한 번만 받을 수 있습니다.\n내일 다시 시도해주세요!"
            )
            return

        # 보상 지급
        reward = 500.0 if user.is_vip_active else 200.0
        user.add_wallet(reward)
        user.last_daily_at = datetime.now(timezone.utc)
        db.commit()

        vip_bonus = " (VIP 보너스!)" if user.is_vip_active else ""
        await update.message.reply_text(
            f"일일 보상 수령!\n\n"
            f"받은 금액: ${reward:,.2f}{vip_bonus}\n"
            f"현재 잔액: ${user.wallet:,.2f}"
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
        # HIT 로직
        import asyncio

        # 먼저 뒷면 카드가 추가된 이미지 표시
        theme = _get_user_theme(user_tg_id, chat_id)
        card_gen = get_casino_renderer(theme)

        # 카드를 추가하기 전 상태 + 뒷면 카드 하나 추가
        temp_hand = game.player_hand + ["BACK"]  # 임시로 뒷면 카드 추가
        temp_value = calculate_hand_value(game.player_hand)

        back_image_bytes = card_gen.generate_game_image(
            player_hand=temp_hand,
            dealer_hand=game.dealer_hand,
            player_value=temp_value,
            dealer_value=None,
            hide_dealer_first=True,
            message="카드를 뽑는 중...",
        )

        # 뒷면 카드 이미지 먼저 표시
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=BytesIO(back_image_bytes), caption="카드를 뽑는 중..."
            ),
            reply_markup=_get_game_keyboard(),
        )

        # 짧은 딜레이 (카드 뒤집기 효과)
        await asyncio.sleep(0.6)

        # 실제 카드 추가
        game.player_hit()
        player_value = calculate_hand_value(game.player_hand)

        # 버스트 체크
        if is_bust(game.player_hand):
            outcome = GameOutcome.BUST
            payout = PayoutCalculator.calculate(outcome, game.bet)
            await _finish_game_callback(
                query, user_tg_id, game, outcome, payout, chat_id
            )
            return

        # 앞면 카드 이미지 생성
        image_bytes = card_gen.generate_game_image(
            player_hand=game.player_hand,
            dealer_hand=game.dealer_hand,
            player_value=player_value,
            dealer_value=None,
            hide_dealer_first=True,
            message="명령어: /hit (카드 추가) | /stand (멈춤)",
        )

        # 앞면 카드로 업데이트
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=BytesIO(image_bytes), caption="카드를 한 장 더 받았습니다!"
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
    image_bytes, caption, reply_markup = _build_game_result(
        user_tg_id, game, outcome, payout, chat_id, lang
    )
    await query.edit_message_media(
        media=InputMediaPhoto(media=BytesIO(image_bytes), caption=caption),
        reply_markup=reply_markup,
    )
    game_sessions.pop(user_tg_id, None)
