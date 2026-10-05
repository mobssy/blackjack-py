"""
JackPy - 블랙잭 게임 핸들러
/deal, /hit, /stand 명령어 처리
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List, Optional, Tuple
from io import BytesIO
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import ContextTypes
from models import get_db, User, GameOutcome
from bot.utils import (
    is_blackjack,
    is_bust,
    PayoutCalculator,
    t,
    get_user_lang,
)
from bot.utils.payouts import OUTCOME_I18N_KEYS
from bot.handlers.settlement import settle_game
from bot.utils.rewards import (
    RESCUE_AMOUNT,
    RESCUE_COOLDOWN_HOURS,
    can_rescue,
    daily_reward_amount,
    next_daily_streak,
    parse_stored_datetime,
)
from bot.utils.blackjack_game import BlackjackGame
from bot.utils.betting import BetError, is_valid_amount, parse_bet
from bot.utils.session_store import load_sessions, save_sessions
from bot.utils.game_renderer import get_game_renderer
from bot.utils.game_scene import play_scene, result_scene

logger = logging.getLogger(__name__)

# 게임 상태 저장소 (메모리 + JSON 파일 영속화)
# 봇 재시작 시 진행 중이던 게임(차감된 베팅)이 유실되지 않도록 복원한다
game_sessions: Dict[int, BlackjackGame] = load_sessions()


def _persist_sessions() -> None:
    """게임 상태 변경 시점마다 세션을 파일에 반영"""
    save_sessions(game_sessions)


# 사용자별 게임 액션 잠금
# 게임 버튼 콜백은 HIT 연출(sleep) 동안 다른 사용자를 막지 않도록 동시 실행
# (main.py에서 block=False)되므로, 같은 사용자의 버튼 연타·명령어가 한 게임을
# 동시에 바꾸거나 두 번 정산하지 않도록 사용자 단위로 직렬화한다.
_user_locks: Dict[int, asyncio.Lock] = {}


def _user_lock(user_tg_id: int) -> asyncio.Lock:
    """사용자별 게임 액션 잠금 (없으면 생성)"""
    return _user_locks.setdefault(user_tg_id, asyncio.Lock())


def _user_lang(user_tg_id: int) -> str:
    """사용자 언어 조회 (미등록 사용자는 기본 언어)"""
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        return get_user_lang(user)


def get_game_keyboard(
    first_turn: bool = False,
    can_split: bool = False,
    can_insure: bool = False,
    prefix: str = "game",
):
    """
    게임 진행 중 사용 가능한 인라인 키보드 생성

    Args:
        first_turn: 첫 턴(첫 2장) 여부 — 더블 다운/서렌더 버튼 표시 조건
        can_split: 스플릿 가능 여부 — SPLIT 버튼 표시 조건
        can_insure: 인슈어런스 가능 여부 — INSURANCE 버튼 표시 조건
        prefix: callback_data 접두사 (1인 게임 "game", 멀티 테이블 "tbl")

    Returns:
        InlineKeyboardMarkup: 게임 명령어 버튼 키보드
    """
    keyboard = [
        [
            InlineKeyboardButton("HIT", callback_data=f"{prefix}_hit"),
            InlineKeyboardButton("STAND", callback_data=f"{prefix}_stand"),
        ]
    ]
    if first_turn:
        second_row = [
            InlineKeyboardButton("DOUBLE", callback_data=f"{prefix}_double"),
            InlineKeyboardButton("SURRENDER", callback_data=f"{prefix}_surrender"),
        ]
        if can_split:
            second_row.append(
                InlineKeyboardButton("SPLIT", callback_data=f"{prefix}_split")
            )
        keyboard.append(second_row)
        if can_insure:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "INSURANCE (2:1)", callback_data=f"{prefix}_insurance"
                    )
                ]
            )
    return InlineKeyboardMarkup(keyboard)


def _render_game_image(game: BlackjackGame, lang: str, drawing: bool = False) -> bytes:
    """
    진행 중 게임 이미지 (딜러 홀 카드 가림)

    Args:
        game: 게임 객체
        lang: 언어 코드
        drawing: HIT 연출 — 받을 카드를 뒷면으로 먼저 보여줌
    """
    return get_game_renderer().render(play_scene(game, lang, drawing=drawing))


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


def _maybe_grant_rescue(db, user: User, lang: str) -> Optional[str]:
    """
    잔액 부족 시 파산 구제금 지급 시도

    잔액이 임계값 미만이고 쿨다운이 지났으면 구제금을 지급한다.

    Args:
        db: DB 세션
        user: 사용자 객체
        lang: 언어 코드

    Returns:
        Optional[str]: 지급 시 안내 메시지, 조건 미달 시 None
    """
    stats = user.stats_json or {}
    last_rescue_at = parse_stored_datetime(stats.get("last_rescue_at"))
    if not can_rescue(float(user.wallet), last_rescue_at):
        return None

    user.add_wallet(RESCUE_AMOUNT)
    new_stats = dict(stats)
    new_stats["last_rescue_at"] = datetime.now(timezone.utc).isoformat()
    user.stats_json = new_stats
    db.commit()

    return t(
        "rescue_granted",
        lang,
        amount=RESCUE_AMOUNT,
        balance=float(user.wallet),
        hours=RESCUE_COOLDOWN_HOURS,
    )


async def cmd_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /deal [금액] - 블랙잭 게임 시작

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    async with _user_lock(update.effective_user.id):
        await _deal(update, context)


async def _deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/deal 본체 (사용자 잠금 안에서 실행)"""
    user_tg_id = update.effective_user.id
    lang = _user_lang(user_tg_id)

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

    # 베팅 금액 파싱 ("all" / "올인"은 전액 베팅)
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(t("deal_usage", lang))
        return

    try:
        bet_request = parse_bet(context.args[0])
    except BetError as e:
        await update.message.reply_text(t(e.key, lang, **e.kwargs))
        return

    # 사용자 조회
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user:
            await update.message.reply_text(t("deal_no_user", lang))
            return

        bet_amount = bet_request.resolve(user.wallet)

        # 잔액 확인 (부족 시 파산 구제 시도, 올인 금액도 최소 베팅 이상이어야 함)
        if not is_valid_amount(bet_amount) or user.wallet < bet_amount:
            rescue_message = _maybe_grant_rescue(db, user, lang)
            await update.message.reply_text(
                rescue_message or t("deal_no_balance", lang, balance=float(user.wallet))
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
        turn = _Turn(
            CommandView(update.message),
            user_tg_id,
            update.effective_chat.id,
            game,
            lang,
        )
        await _finish(turn, [(outcome, payout)])
        return

    # 사용자 테마 가져오기 및 럭셔리 카드 이미지 생성
    image_bytes = _render_game_image(game, lang)

    caption = t("deal_caption", lang, bet=bet_amount)
    await update.message.reply_photo(
        photo=BytesIO(image_bytes),
        caption=caption,
        reply_markup=get_game_keyboard(
            first_turn=True, can_split=game.can_split, can_insure=game.can_insure
        ),
    )


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


def _try_insurance(user_tg_id: int, game: BlackjackGame, lang: str) -> Optional[str]:
    """
    인슈어런스 검증 및 실행 (베팅액 절반 차감)

    Args:
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        lang: 언어 코드

    Returns:
        Optional[str]: 실패 시 에러 메시지, 성공 시 None
    """
    if not game.can_insure:
        return t("insurance_not_allowed", lang)

    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user or not user.deduct_wallet(game.insurance_cost):
            balance = float(user.wallet) if user else 0.0
            return t("insurance_no_balance", lang, balance=balance)
        db.commit()

    game.take_insurance()
    _persist_sessions()
    return None


# ── 화면 출력 방식 ────────────────────────────────────────────
# 액션 로직은 하나로 두고, 명령어(새 메시지 전송)와 버튼(기존 메시지 수정)의
# 차이는 GameView 구현체가 맡는다.

# 버튼 HIT: 뒷면 카드를 먼저 보여준 뒤 앞면을 공개하기까지의 연출 간격 (초)
HIT_REVEAL_DELAY = 0.6


class GameView(ABC):
    """게임 화면 출력 방식"""

    @abstractmethod
    async def show(
        self, image: bytes, caption: str, markup: InlineKeyboardMarkup
    ) -> None:
        """게임 이미지 표시"""

    @abstractmethod
    async def show_text(
        self, text: str, markup: Optional[InlineKeyboardMarkup] = None
    ) -> None:
        """이미지 없이 문구로 게임 화면 갱신"""

    @abstractmethod
    async def notify(self, text: str) -> None:
        """게임 화면은 그대로 두고 별도 안내 (오류 등)"""

    async def animate_draw(self, render: Callable[[], bytes], caption: str) -> None:
        """카드 뽑기 연출 (기본: 없음)"""


class CommandView(GameView):
    """/hit 등 명령어 — 매번 새 메시지로 응답"""

    def __init__(self, message):
        self._message = message

    async def show(self, image, caption, markup):
        await self._message.reply_photo(
            photo=BytesIO(image), caption=caption, reply_markup=markup
        )

    async def show_text(self, text, markup=None):
        await self._message.reply_text(text, reply_markup=markup)

    async def notify(self, text):
        await self._message.reply_text(text)


class CallbackView(GameView):
    """인라인 버튼 — 버튼이 달린 게임 메시지를 제자리에서 수정"""

    def __init__(self, query):
        self._query = query

    async def show(self, image, caption, markup):
        await self._query.edit_message_media(
            media=InputMediaPhoto(media=BytesIO(image), caption=caption),
            reply_markup=markup,
        )

    async def show_text(self, text, markup=None):
        await self._query.edit_message_caption(caption=text, reply_markup=markup)

    async def notify(self, text):
        await self._query.message.reply_text(text)

    async def animate_draw(self, render, caption):
        await self.show(render(), caption, get_game_keyboard())
        await asyncio.sleep(HIT_REVEAL_DELAY)


@dataclass
class _Turn:
    """액션 하나를 처리하는 데 필요한 문맥"""

    view: GameView
    user_tg_id: int
    chat_id: int
    game: BlackjackGame
    lang: str


# ── 게임 액션 (명령어/버튼 공용) ───────────────────────────────


async def _finish(turn: _Turn, results: List[Tuple[GameOutcome, float]]) -> None:
    """
    게임 종료 처리 — 정산 커밋 → 세션 제거 → 결과 전송

    정산이 커밋된 직후 세션을 제거해, 전송이 실패해도 이중 정산이 없도록 한다.
    """
    settle_info = settle_game(turn.user_tg_id, turn.game, results, turn.chat_id)
    game_sessions.pop(turn.user_tg_id, None)
    _persist_sessions()

    image_bytes, caption, reply_markup = _render_game_result(
        turn.game, results, settle_info, turn.lang
    )
    await turn.view.show(image_bytes, caption, reply_markup)


async def _show_progress(turn: _Turn, caption: str, header: str = "") -> None:
    """다음 핸드/카드 진행 화면 (메시지 캡션은 header+caption)"""
    image_bytes = _render_game_image(turn.game, turn.lang)
    await turn.view.show(image_bytes, header + caption, get_game_keyboard())


async def _act_hit(turn: _Turn) -> None:
    """HIT — 카드 한 장 추가, 버스트면 다음 핸드 또는 게임 종료"""
    game, lang = turn.game, turn.lang
    drawing_msg = t("drawing_card", lang)
    await turn.view.animate_draw(
        lambda: _render_game_image(game, lang, drawing=True), drawing_msg
    )

    game.player_hit()
    _persist_sessions()

    if not is_bust(game.player_hand):
        image_bytes = _render_game_image(game, lang)
        await turn.view.show(image_bytes, t("card_drawn", lang), get_game_keyboard())
        return

    busted_number = game.hand_number
    if game.advance_hand():
        # 스플릿: 다음 핸드로 진행
        _persist_sessions()
        caption = t(
            "hand_bust_next",
            lang,
            n=busted_number,
            next=game.hand_number,
            total=game.hand_count,
        )
        await _show_progress(turn, caption)
        return
    await _finish(turn, _all_hands_results(game))


async def _act_stand(turn: _Turn) -> None:
    """STAND — 다음 핸드가 남아 있으면 이동, 아니면 딜러 플레이 후 종료"""
    if turn.game.advance_hand():
        _persist_sessions()
        await _show_progress(turn, _hand_progress_caption(turn.game, turn.lang))
        return
    await _finish(turn, _all_hands_results(turn.game))


async def _act_double(turn: _Turn) -> None:
    """DOUBLE — 베팅 2배 + 카드 1장 후 자동 스탠드"""
    error = _try_double(turn.user_tg_id, turn.game, turn.lang)
    if error:
        await turn.view.notify(error)
        return
    await _finish(turn, _double_result(turn.game))


async def _act_surrender(turn: _Turn) -> None:
    """SURRENDER — 첫 두 장에서만, 베팅액 절반 회수"""
    if not turn.game.is_first_turn:
        await turn.view.notify(t("surrender_only_first", turn.lang))
        return
    await _finish(turn, [turn.game.surrender_result()])


async def _act_insurance(turn: _Turn) -> None:
    """INSURANCE — 베팅액 절반, 딜러 블랙잭 시 2:1"""
    game, lang = turn.game, turn.lang
    error = _try_insurance(turn.user_tg_id, game, lang)
    if error:
        await turn.view.notify(error)
        return

    # 딜러 블랙잭이면 즉시 게임 종료 (보험 2:1 지급은 정산에서 처리)
    if game.dealer_has_blackjack:
        await _finish(turn, game.get_results())
        return

    # 보험금 소멸, 게임 계속 (인슈어런스 버튼만 제거)
    await turn.view.show_text(
        t("insurance_no_bj", lang, amount=game.insurance_bet),
        get_game_keyboard(first_turn=True, can_split=game.can_split),
    )


async def _act_split(turn: _Turn) -> None:
    """SPLIT — 같은 랭크 2장을 두 핸드로 분리"""
    game, lang = turn.game, turn.lang
    error = _try_split(turn.user_tg_id, game, lang)
    if error:
        await turn.view.notify(error)
        return

    # 에이스 스플릿: 각 핸드 카드 1장씩 받고 자동 스탠드
    if game.split_rank == "A":
        await turn.view.notify(t("split_aces_note", lang))
        await _finish(turn, _all_hands_results(game))
        return

    # 핸드 1부터 플레이
    await _show_progress(
        turn,
        _hand_progress_caption(game, lang),
        header=t("split_caption", lang, bet=game.bet) + "\n",
    )


_ACTIONS: Dict[str, Callable[[_Turn], Awaitable[None]]] = {
    "hit": _act_hit,
    "stand": _act_stand,
    "double": _act_double,
    "surrender": _act_surrender,
    "insurance": _act_insurance,
    "split": _act_split,
}


async def _run_action(action: str, update: Update, view: GameView) -> None:
    """
    진행 중인 게임에 액션 적용 (사용자 잠금 안에서 세션을 다시 조회)

    Args:
        action: _ACTIONS 키
        update: 업데이트 객체
        view: 응답 방식 (명령어/버튼)
    """
    user_tg_id = update.effective_user.id
    lang = _user_lang(user_tg_id)
    async with _user_lock(user_tg_id):
        game = game_sessions.get(user_tg_id)
        if game is None:
            await view.show_text(t("no_game", lang))
            return
        turn = _Turn(view, user_tg_id, update.effective_chat.id, game, lang)
        await _ACTIONS[action](turn)


async def cmd_hit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/hit - 카드 한 장 추가"""
    await _run_action("hit", update, CommandView(update.message))


async def cmd_stand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stand - 멈춤 (다음 핸드 또는 딜러 차례)"""
    await _run_action("stand", update, CommandView(update.message))


async def cmd_double(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/double - 더블 다운 (첫 두 장에서만, 베팅 2배 + 카드 1장 후 자동 스탠드)"""
    await _run_action("double", update, CommandView(update.message))


async def cmd_surrender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/surrender - 서렌더 (첫 두 장에서만, 베팅액 절반 회수)"""
    await _run_action("surrender", update, CommandView(update.message))


async def cmd_insurance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/insurance - 인슈어런스 (딜러 업카드 A일 때 베팅액 절반, 딜러 블랙잭 시 2:1)"""
    await _run_action("insurance", update, CommandView(update.message))


async def cmd_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/split - 스플릿 (첫 두 장이 같은 랭크일 때, 두 핸드로 분리)"""
    await _run_action("split", update, CommandView(update.message))


async def game_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    게임 버튼(game_*) 콜백 — main.py에서 block=False로 등록

    HIT 연출(sleep) 동안 다른 사용자의 업데이트 처리가 멈추지 않도록 동시 실행되며,
    같은 사용자의 액션은 _run_action의 사용자 잠금으로 직렬화된다.

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    query = update.callback_query
    await query.answer()
    action = query.data.removeprefix("game_")
    if action in _ACTIONS:
        await _run_action(action, update, CallbackView(query))


def _outcome_text(outcome: GameOutcome, lang: str) -> str:
    """결과 enum에 대응하는 번역 문자열"""
    return t(OUTCOME_I18N_KEYS.get(outcome, "result_lose"), lang)


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
    if len(results) == 1:
        caption_head = _outcome_text(results[0][0], lang)
    else:
        hand_label = t("hand_label", lang)
        caption_head = " / ".join(
            f"{hand_label}{i} {_outcome_text(outcome, lang)}"
            for i, (outcome, _) in enumerate(results, 1)
        )

    image_bytes = get_game_renderer().render(
        result_scene(game, results, settle_info, lang)
    )
    caption = f"{caption_head} {t('game_over_suffix', lang)}"

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
        message = t(
            "wallet_full",
            lang,
            balance=float(user.wallet),
            games=stats.get("total_games", 0),
            wins=stats.get("wins", 0),
            losses=stats.get("losses", 0),
            streak=stats.get("win_streak", 0),
            profit=stats.get("total_profit", 0),
        )
        await update.message.reply_text(message)


def claim_daily_reward(db, user: User, lang: str) -> str:
    """
    일일 보상 지급 (출석 스트릭 반영) 후 안내 메시지 반환

    /daily 명령어와 시작 메뉴의 출석 체크 버튼이 공유한다.

    Args:
        db: DB 세션
        user: 사용자 객체
        lang: 언어 코드

    Returns:
        str: 지급 안내 메시지 (오늘 이미 받았으면 안내 문구)
    """
    if not user.can_claim_daily():
        return t("daily_already", lang)

    stats = user.stats_json or {}
    streak = next_daily_streak(user.last_daily_at, stats.get("daily_streak", 0))
    base_reward, streak_bonus_amount = daily_reward_amount(streak)
    reward = base_reward + streak_bonus_amount

    user.add_wallet(reward)
    user.last_daily_at = datetime.now(timezone.utc)
    new_stats = dict(stats)
    new_stats["daily_streak"] = streak
    user.stats_json = new_stats
    db.commit()

    message = t("daily_reward", lang, reward=reward, balance=float(user.wallet))
    if streak_bonus_amount > 0:
        message += t("daily_streak_line", lang, n=streak, bonus=streak_bonus_amount)
    return message


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
        message = claim_daily_reward(db, user, lang)

    await update.message.reply_text(message)
