"""
JackPy - 시작 및 기본 명령어 핸들러
/start, /help 명령어 처리
"""

import logging
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import get_db, User, Group, PlanType

logger = logging.getLogger(__name__)


def _get_start_menu_message(user_display_name: str = None, is_new: bool = False):
    """
    시작 메뉴 메시지 생성

    Args:
        user_display_name: 사용자 표시 이름
        is_new: 신규 사용자 여부

    Returns:
        str: 시작 메뉴 메시지
    """
    # 환영 메시지
    if is_new:
        welcome_message = (
            f"JackPy에 오신 것을 환영합니다!\n\n"
            f"텔레그램 최고의 블랙잭 카지노 봇입니다.\n\n"
            f"가입 축하 보너스: $1,000\n\n"
        )
    elif user_display_name:
        welcome_message = f"다시 오신 것을 환영합니다, {user_display_name}님!\n\n"
    else:
        welcome_message = "JackPy\n\n"

    return welcome_message


def _get_help_message() -> str:
    """도움말 메시지 반환"""
    return (
        "JackPy 도움말\n\n"
        "━━━━━━━━━━━━━━━\n"
        "게임 명령어\n"
        "━━━━━━━━━━━━━━━\n"
        "/deal [금액] - 블랙잭 시작\n"
        "  예: /deal 100\n"
        "/hit - 카드 추가\n"
        "/stand - 멈춤\n"
        "/wallet - 잔액 확인\n"
        "/daily - 일일 보상\n"
        "/rank - 랭킹 조회\n\n"
        "━━━━━━━━━━━━━━━\n"
        "사용자 명령어\n"
        "━━━━━━━━━━━━━━━\n"
        "/my - 내 프로필\n"
        "/start - 시작하기\n"
        "/help - 도움말\n\n"
        "━━━━━━━━━━━━━━━\n"
        "블랙잭 규칙\n"
        "━━━━━━━━━━━━━━━\n"
        "목표: 21에 가까운 숫자\n"
        "블랙잭: 3:2 배당\n"
        "일반 승리: 1:1 배당\n"
        "무승부: 베팅액 반환\n"
        "딜러: 17 이상까지 히트\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "Support: @jackpy_support"
    )


def _get_start_menu_keyboard():
    """
    시작 메뉴 키보드 생성

    Returns:
        InlineKeyboardMarkup: 시작 메뉴 키보드
    """
    keyboard = [
        [
            InlineKeyboardButton("게임 시작", callback_data="start_game"),
            InlineKeyboardButton("도움말", callback_data="help"),
        ],
        [
            InlineKeyboardButton("출석 체크", callback_data="daily_check"),
            InlineKeyboardButton("프로필", callback_data="my_profile"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start - 봇 시작 및 플랜 안내

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name

    # 사용자 등록 또는 조회
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()

        if not user:
            # 신규 사용자 등록
            user = User(
                tg_user_id=user_tg_id,
                username=username,
                first_name=first_name,
                wallet=1000.0,  # 초기 잔액
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
            is_new = True
            user_display_name = user.display_name  # 세션 내에서 로드
        else:
            # 기존 사용자 정보 업데이트
            user.username = username
            user.first_name = first_name
            db.commit()
            is_new = False
            user_display_name = user.display_name  # 세션 내에서 로드

    # 메시지 및 키보드 생성
    message = _get_start_menu_message(user_display_name, is_new)
    keyboard = _get_start_menu_keyboard()

    await update.message.reply_text(message, reply_markup=keyboard)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /help - 도움말

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    await update.message.reply_text(_get_help_message())


# 인라인 버튼 콜백 핸들러
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    인라인 버튼 콜백 처리

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    query = update.callback_query
    await query.answer()

    if query.data == "start_game":
        keyboard = [[InlineKeyboardButton("뒤로가기", callback_data="back_to_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "게임 시작\n\n" "/deal [금액] 명령어로 블랙잭을 시작하세요.\n" "예: /deal 100",
            reply_markup=reply_markup,
        )

    elif query.data == "help":
        keyboard = [[InlineKeyboardButton("뒤로가기", callback_data="back_to_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(_get_help_message(), reply_markup=reply_markup)

    elif query.data == "daily_check":
        # 출석 체크 버튼
        user_tg_id = update.effective_user.id

        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            if not user:
                await query.edit_message_text("등록되지 않은 사용자입니다. /start를 먼저 실행해주세요.")
                return

            # 일일 보상 수령 가능 여부 확인
            if not user.can_claim_daily():
                keyboard = [
                    [InlineKeyboardButton("뒤로가기", callback_data="back_to_start")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "일일 보상은 하루에 한 번만 받을 수 있습니다.\n" "내일 다시 시도해주세요!",
                    reply_markup=reply_markup,
                )
                return

            # 보상 지급
            reward = 500.0 if user.is_vip_active else 200.0
            user.add_wallet(reward)
            user.last_daily_at = datetime.now(timezone.utc)
            db.commit()

            vip_bonus = " (VIP 보너스!)" if user.is_vip_active else ""

            # 뒤로가기 버튼 추가
            keyboard = [[InlineKeyboardButton("뒤로가기", callback_data="back_to_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"일일 보상 수령!\n\n"
                f"받은 금액: ${reward:,.2f}{vip_bonus}\n"
                f"현재 잔액: ${user.wallet:,.2f}",
                reply_markup=reply_markup,
            )

    elif query.data == "my_profile":
        # 프로필 버튼
        user_tg_id = update.effective_user.id
        chat_id = update.effective_chat.id

        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            if not user:
                await query.edit_message_text("등록되지 않은 사용자입니다. /start를 먼저 실행해주세요.")
                return

            # 통계 및 프로필 정보
            stats = user.stats_json or {}
            win_rate = (
                (stats.get("wins", 0) / stats.get("total_games", 1)) * 100
                if stats.get("total_games", 0) > 0
                else 0.0
            )

            # VIP 상태
            vip_status = "활성" if user.is_vip_active else "비활성"
            vip_expires = ""
            if user.is_vip_active and user.vip_expires_at:
                days_left = (user.vip_expires_at - datetime.now(timezone.utc)).days
                vip_expires = f" ({days_left}일 남음)"

            # 그룹 플랜 확인
            group = db.query(Group).filter(Group.chat_id == chat_id).first()
            group_plan = group.plan.value if group else "없음"

            profile_message = (
                f"프로필\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"사용자 정보\n"
                f"━━━━━━━━━━━━━━━\n"
                f"이름: {user.display_name}\n"
                f"잔액: ${user.wallet:,.2f}\n"
                f"VIP: {vip_status}{vip_expires}\n"
                f"그룹 플랜: {group_plan}\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"게임 통계\n"
                f"━━━━━━━━━━━━━━━\n"
                f"총 게임: {stats.get('total_games', 0):,}회\n"
                f"승리: {stats.get('wins', 0):,}회\n"
                f"패배: {stats.get('losses', 0):,}회\n"
                f"승률: {win_rate:.1f}%\n"
                f"총 베팅: ${stats.get('total_bet', 0):,.2f}\n"
                f"총 수익: ${stats.get('total_profit', 0):,.2f}\n"
                f"━━━━━━━━━━━━━━━"
            )

            # 뒤로가기 버튼 추가
            keyboard = [[InlineKeyboardButton("뒤로가기", callback_data="back_to_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(profile_message, reply_markup=reply_markup)

    elif query.data in ("game_hit", "game_stand"):
        # 게임 버튼 - blackjack 핸들러로 위임
        from bot.handlers.blackjack import game_button_callback

        await game_button_callback(update, context)

    elif query.data == "back_to_start":
        # 뒤로가기 - 시작 메뉴로 돌아가기
        user_tg_id = update.effective_user.id

        # 사용자 정보 조회
        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            user_display_name = user.display_name if user else None

        # 시작 메뉴 메시지 및 키보드 생성
        message = _get_start_menu_message(user_display_name, is_new=False)
        keyboard = _get_start_menu_keyboard()

        await query.edit_message_text(message, reply_markup=keyboard)

    elif query.data == "restart_game":
        # 다시 시작 - 게임 시작 안내
        keyboard = [[InlineKeyboardButton("뒤로가기", callback_data="back_to_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(
            caption="게임 시작\n\n" "/deal [금액] 명령어로 블랙잭을 시작하세요.\n" "예: /deal 100",
            reply_markup=reply_markup,
        )
