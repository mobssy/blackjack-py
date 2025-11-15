"""
JackPy - VIP and Business Plan 핸들러
/vip, /business, /confirm 명령어 처리
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import get_db, User, Approval, ApprovalType, ApprovalStatus

logger = logging.getLogger(__name__)

# 플랜 가격 설정
VIP_PRICE_30_DAYS = 30.0
VIP_PRICE_90_DAYS = 80.0
VIP_PRICE_365_DAYS = 250.0
BUSINESS_PRICE_MONTHLY = 300.0

# 입금 계좌 정보 (환경변수에서 로드)
BANK_ACCOUNT_INFO = os.getenv("BANK_ACCOUNT_INFO", "신한은행 110-490-935730 \n예금주: 신겸")


async def cmd_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /vip - VIP Plan 안내 및 신청

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user:
            await update.message.reply_text("❌ 등록되지 않은 사용자입니다. /start를 먼저 실행해주세요.")
            return

        # VIP 상태 확인
        if user.is_vip_active:
            expires_str = (
                user.vip_expires_at.strftime("%Y-%m-%d %H:%M")
                if user.vip_expires_at
                else "무제한"
            )
            message = (
                f"VIP 회원 정보\n\n"
                f"상태: ✅ 활성\n"
                f"만료일: {expires_str}\n\n"
                f"VIP 혜택:\n"
                f"광고 없음\n"
                f"일일 보상 2.5배 (500원)\n"
                f"특별 이벤트 참여\n"
                f"우선 지원\n\n"
                f"VIP 기간 연장을 원하시면 아래 안내를 참고하세요."
            )
        else:
            message = (
                f"VIP Plan 안내\n\n"
                f"VIP 혜택:\n"
                f"광고 없음\n"
                f"일일 보상 2.5배 (500원)\n"
                f"특별 이벤트 참여\n"
                f"우선 지원\n\n"
            )

        message += (
            f"가격:\n"
            f"• ${VIP_PRICE_30_DAYS:,.2f} / 30일\n\n"
            f"신청 방법:\n"
            f"1. 아래 계좌로 입금\n"
            f"{BANK_ACCOUNT_INFO}\n\n"
            f"2. 입금 후 명령어 입력:\n"
            f"/confirm [입금자명] [금액]\n\n"
            f"예: /confirm 홍길동 30\n\n"
            f"※ VIP 기간은 자동으로 30일로 설정됩니다."
        )

        await update.message.reply_text(message)


async def cmd_business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /business - Business Plan 안내

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    message = (
        f"Business Plan 안내\n\n"
        f"그룹 전용 프리미엄 플랜!\n\n"
        f"혜택:\n"
        f"• 완전한 브랜딩 커스터마이징\n"
        f"• 커스텀 로고 및 테마\n"
        f"• 광고 완전 제거\n"
        f"• 명령어 prefix 변경\n"
        f"• 전담 지원\n\n"
        f"가격: ${BUSINESS_PRICE_MONTHLY:,.2f}/mo\n\n"
        f"신청 방법:\n"
        f"1. 아래 계좌로 입금\n"
        f"{BANK_ACCOUNT_INFO}\n\n"
        f"2. 입금 후 명령어 입력:\n"
        f"/confirm_business [입금자명] [금액]\n\n"
        f"예: /confirm_business 회사명 300\n\n"
        f"승인 후 그룹 설정을 진행해드립니다."
    )

    await update.message.reply_text(message)


async def cmd_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /confirm [입금자명] [금액] - VIP 입금 확인 요청 (30일 고정)

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    # 인자 확인
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ 사용법: /confirm [입금자명] [금액]\n"
            "예: /confirm 홍길동 30\n\n"
            "VIP 기간은 자동으로 30일로 설정됩니다."
        )
        return

    depositor_name = context.args[0]
    try:
        amount = float(context.args[1])
        duration_days = 30  # 30일 고정
    except ValueError:
        await update.message.reply_text("❌ 금액은 숫자로 입력해주세요.")
        return

    # 사용자 조회
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user:
            await update.message.reply_text("❌ 등록되지 않은 사용자입니다. /start를 먼저 실행해주세요.")
            return

        # 승인 요청 생성
        approval = Approval(
            user_id=user.id,
            type=ApprovalType.VIP,
            depositor_name=depositor_name,
            amount=amount,
            duration_days=duration_days,
            status=ApprovalStatus.PENDING,
        )
        db.add(approval)
        db.commit()

        # 관리자에게 알림
        admin_ids = os.getenv("ADMIN_IDS", "").split(",")
        admin_message = (
            f"새로운 VIP 승인 요청\n\n"
            f"요청자: {user.display_name} (ID: {user.tg_user_id})\n"
            f"입금자명: {depositor_name}\n"
            f"금액: ${amount:,.2f}\n"
            f"기간: {duration_days}일\n\n"
            f"승인: /approve {user.tg_user_id} {duration_days}\n"
            f"거절: /reject {user.tg_user_id} [사유]"
        )

        for admin_id in admin_ids:
            if admin_id:
                try:
                    await context.bot.send_message(
                        chat_id=int(admin_id), text=admin_message
                    )
                except Exception as e:
                    logger.error(f"관리자 알림 전송 실패: {e}")

        # 사용자에게 확인 메시지
        await update.message.reply_text(
            f"VIP 승인 요청이 접수되었습니다.\n\n"
            f"입금자명: {depositor_name}\n"
            f"금액: ${amount:,.2f}\n"
            f"기간: 30일\n\n"
            f"관리자 확인 후 승인됩니다."
        )


async def cmd_confirm_business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /confirm_business [입금자명] [금액] - Business Plan 입금 확인 요청

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    # 인자 확인
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ 사용법: /confirm_business [입금자명] [금액]\n" "예: /confirm_business 회사명 300"
        )
        return

    depositor_name = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ 금액은 숫자로 입력해주세요.")
        return

    # 사용자 조회
    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user:
            await update.message.reply_text("❌ 등록되지 않은 사용자입니다. /start를 먼저 실행해주세요.")
            return

        # 승인 요청 생성
        approval = Approval(
            user_id=user.id,
            type=ApprovalType.BUSINESS,
            depositor_name=depositor_name,
            amount=amount,
            duration_days=30,  # 비즈니스는 월 단위
            status=ApprovalStatus.PENDING,
        )
        db.add(approval)
        db.commit()

        # 관리자에게 알림
        admin_ids = os.getenv("ADMIN_IDS", "").split(",")
        admin_message = (
            f"새로운 Business Plan 승인 요청\n\n"
            f"요청자: {user.display_name} (ID: {user.tg_user_id})\n"
            f"입금자명: {depositor_name}\n"
            f"금액: ${amount:,.2f}\n\n"
            f"승인: /approve_business {user.tg_user_id} [chat_id]\n"
            f"거절: /reject {user.tg_user_id} [사유]"
        )

        for admin_id in admin_ids:
            if admin_id:
                try:
                    await context.bot.send_message(
                        chat_id=int(admin_id), text=admin_message
                    )
                except Exception as e:
                    logger.error(f"관리자 알림 전송 실패: {e}")

        # 사용자에게 확인 메시지
        await update.message.reply_text(
            f"✅ Business Plan 승인 요청이 접수되었습니다!\n\n"
            f"입금자명: {depositor_name}\n"
            f"금액: ${amount:,.2f}\n\n"
            f"관리자 확인 후 그룹 설정을 진행해드립니다."
        )
