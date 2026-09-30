"""
JackPy - 관리자 핸들러
/admin (전체 통계), /add (잔액 지급) 명령어 처리
"""

import logging
import os
from typing import List
from telegram import Update
from telegram.ext import ContextTypes
from models import get_db, User, Group, Round

logger = logging.getLogger(__name__)

# 모듈 로드 시 한 번만 파싱
_ADMIN_IDS: set = set(filter(None, os.getenv("ADMIN_IDS", "").split(",")))


def is_admin(user_id: int) -> bool:
    """
    관리자 여부 확인

    Args:
        user_id: 텔레그램 사용자 ID

    Returns:
        bool: 관리자 여부
    """
    return str(user_id) in _ADMIN_IDS


def admin_ids() -> List[int]:
    """
    설정된 관리자 텔레그램 ID 목록 (숫자가 아닌 항목은 무시)

    Returns:
        List[int]: 관리자 ID (정렬됨)
    """
    return sorted(int(uid) for uid in _ADMIN_IDS if uid.strip().isdigit())


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /admin [command] - 관리자 명령어

    서브 명령어:
    - stats: 전체 통계 조회

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    # 관리자 권한 확인
    if not is_admin(user_tg_id):
        await update.message.reply_text("[오류] 관리자 권한이 필요합니다.")
        return

    # 서브 명령어 확인
    if not context.args or len(context.args) == 0:
        message = (
            "관리자 명령어\n\n"
            "• /admin stats - 전체 통계\n"
            "• /add [user_id 또는 @username] [금액] - 잔액 추가"
        )
        await update.message.reply_text(message)
        return

    subcommand = context.args[0].lower()

    if subcommand == "stats":
        await _admin_stats(update, context)
    else:
        await update.message.reply_text("알 수 없는 명령어입니다.")


async def _admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """전체 통계 조회"""
    with get_db() as db:
        total_users = db.query(User).count()
        total_groups = db.query(Group).count()
        total_rounds = db.query(Round).count()

        # 총 베팅액 및 플레이어 순손익 (Round.payout은 플레이어 기준 순손익)
        from sqlalchemy import func

        bet_sum = db.query(func.sum(Round.bet)).scalar() or 0
        payout_sum = db.query(func.sum(Round.payout)).scalar() or 0

        message = (
            f"JackPy 전체 통계\n\n"
            f"사용자\n"
            f"• 총 사용자: {total_users:,}명\n\n"
            f"그룹\n"
            f"• 총 그룹: {total_groups:,}개\n\n"
            f"게임\n"
            f"• 총 라운드: {total_rounds:,}회\n"
            f"• 총 베팅액: ${bet_sum:,.2f}\n"
            f"• 플레이어 순손익: ${payout_sum:,.2f}\n"
            f"• 하우스 수익: ${-payout_sum:,.2f}"
        )

        await update.message.reply_text(message)


async def cmd_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /add [user_id 또는 @username] [금액] - 사용자 잔액 추가

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    # 관리자 권한 확인
    if not is_admin(user_tg_id):
        await update.message.reply_text("[오류] 관리자 권한이 필요합니다.")
        return

    # 인자 확인
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "사용법: /add [user_id 또는 @username] [금액]\n"
            "예: /add 123456789 1000\n"
            "예: /add @username 1000"
        )
        return

    # 사용자 식별자 파싱
    user_identifier = context.args[0]

    # 금액 파싱
    try:
        amount = float(context.args[1])
        if amount <= 0:
            await update.message.reply_text("금액은 0보다 커야 합니다.")
            return
    except ValueError:
        await update.message.reply_text("올바른 금액을 입력해주세요.")
        return

    with get_db() as db:
        # 사용자 조회
        user = None

        # @ 기호로 시작하면 username으로 검색
        if user_identifier.startswith("@"):
            username = user_identifier[1:]  # @ 제거
            user = db.query(User).filter(User.username == username).first()
        else:
            # 숫자면 user_id로 검색
            try:
                target_user_id = int(user_identifier)
                user = db.query(User).filter(User.tg_user_id == target_user_id).first()
            except ValueError:
                await update.message.reply_text("올바른 사용자 ID 또는 username을 입력해주세요.")
                return

        if not user:
            await update.message.reply_text(f"사용자를 찾을 수 없습니다: {user_identifier}")
            return

        # 이전 잔액 저장
        old_balance = user.wallet

        # 잔액 추가
        user.add_wallet(amount)
        db.commit()

        # 사용자에게 알림
        try:
            await context.bot.send_message(
                chat_id=user.tg_user_id,
                text=f"잔액이 충전되었습니다!\n\n"
                f"충전 금액: ${amount:,.2f}\n"
                f"현재 잔액: ${user.wallet:,.2f}",
            )
        except Exception as e:
            logger.error(f"사용자 알림 전송 실패: {e}")

        # 관리자에게 확인 메시지
        await update.message.reply_text(
            f"잔액 추가 완료\n\n"
            f"사용자: {user.display_name}\n"
            f"이전 잔액: ${old_balance:,.2f}\n"
            f"추가 금액: ${amount:,.2f}\n"
            f"현재 잔액: ${user.wallet:,.2f}"
        )
