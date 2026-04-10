"""
JackPy - 관리자 핸들러
/admin, /approve, /reject, /revoke 명령어 처리
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from models import (
    get_db,
    User,
    Group,
    Approval,
    Round,
    ApprovalStatus,
    ApprovalType,
    PlanType,
)

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


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /admin [command] - 관리자 명령어

    서브 명령어:
    - pending: 대기 중인 승인 요청 조회
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
            "• /admin pending - 승인 대기 목록\n"
            "• /admin stats - 전체 통계\n"
            "• /approve [user_id] [days] - VIP 승인\n"
            "• /approve_business [user_id] [chat_id] - 비즈니스 승인\n"
            "• /reject [user_id] [사유] - 승인 거절\n"
            "• /revoke [user_id] - VIP 해제\n"
            "• /add_balance [user_id 또는 @username] [금액] - 잔액 추가"
        )
        await update.message.reply_text(message)
        return

    subcommand = context.args[0].lower()

    if subcommand == "pending":
        await _admin_pending(update, context)
    elif subcommand == "stats":
        await _admin_stats(update, context)
    else:
        await update.message.reply_text("알 수 없는 명령어입니다.")


async def _admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """승인 대기 목록 조회"""
    with get_db() as db:
        pending_approvals = (
            db.query(Approval)
            .filter(Approval.status == ApprovalStatus.PENDING)
            .order_by(Approval.created_at.desc())
            .all()
        )

        if not pending_approvals:
            await update.message.reply_text("대기 중인 승인 요청이 없습니다.")
            return

        message = "승인 대기 목록\n\n"
        for approval in pending_approvals:
            user = approval.user
            message += (
                f"ID: {approval.id}\n"
                f"유형: {approval.type.value}\n"
                f"사용자: {user.display_name} ({user.tg_user_id})\n"
                f"입금자: {approval.depositor_name}\n"
                f"금액: ${approval.amount:,.2f}\n"
                f"기간: {approval.duration_days}일\n"
                f"요청일: {approval.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            )

            if approval.type == ApprovalType.VIP:
                message += f"승인: /approve {user.tg_user_id} {approval.duration_days}\n"
            else:
                message += f"승인: /approve_business {user.tg_user_id} [chat_id]\n"

            message += f"거절: /reject {user.tg_user_id} [사유]\n"
            message += "───────────────\n\n"

        await update.message.reply_text(message)


async def _admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """전체 통계 조회"""
    with get_db() as db:
        total_users = db.query(User).count()
        vip_users = db.query(User).filter(User.is_vip == True).count()
        total_groups = db.query(Group).count()
        business_groups = (
            db.query(Group).filter(Group.plan == PlanType.BUSINESS).count()
        )
        total_rounds = db.query(Round).count()

        # 총 베팅액 및 정산액 계산
        from sqlalchemy import func

        bet_sum = db.query(func.sum(Round.bet)).scalar() or 0
        payout_sum = db.query(func.sum(Round.payout)).scalar() or 0

        message = (
            f"JackPy 전체 통계\n\n"
            f"사용자\n"
            f"• 총 사용자: {total_users:,}명\n"
            f"• VIP 사용자: {vip_users:,}명\n\n"
            f"그룹\n"
            f"• 총 그룹: {total_groups:,}개\n"
            f"• 비즈니스 그룹: {business_groups:,}개\n\n"
            f"게임\n"
            f"• 총 라운드: {total_rounds:,}회\n"
            f"• 총 베팅액: ${bet_sum:,.2f}\n"
            f"• 총 정산액: ${payout_sum:,.2f}\n"
            f"• 하우스 엣지: ${bet_sum - payout_sum:,.2f}"
        )

        await update.message.reply_text(message)


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /approve [user_id] [days] - VIP 승인

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    # 관리자 권한 확인
    if not is_admin(user_tg_id):
        await update.message.reply_text("❌ 관리자 권한이 필요합니다.")
        return

    # 인자 확인
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "[오류] 사용법: /approve [user_id] [days]\n" "예: /approve 123456789 30"
        )
        return

    try:
        target_user_id = int(context.args[0])
        duration_days = int(context.args[1])
    except ValueError:
        await update.message.reply_text("[오류] 올바른 숫자를 입력해주세요.")
        return

    with get_db() as db:
        # 사용자 조회
        user = db.query(User).filter(User.tg_user_id == target_user_id).first()
        if not user:
            await update.message.reply_text("[오류] 사용자를 찾을 수 없습니다.")
            return

        # VIP 부여
        user.is_vip = True
        if user.vip_expires_at and user.vip_expires_at > datetime.now(timezone.utc):
            # 기존 VIP 기간 연장
            user.vip_expires_at += timedelta(days=duration_days)
        else:
            # 새로운 VIP 기간 설정
            user.vip_expires_at = datetime.now(timezone.utc) + timedelta(
                days=duration_days
            )

        # 승인 요청 상태 업데이트
        approval = (
            db.query(Approval)
            .filter(
                Approval.user_id == user.id,
                Approval.type == ApprovalType.VIP,
                Approval.status == ApprovalStatus.PENDING,
            )
            .order_by(Approval.created_at.desc())
            .first()
        )

        if approval:
            approval.status = ApprovalStatus.APPROVED
            admin_user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            approval.approved_by = admin_user.id if admin_user else None
            approval.approved_at = datetime.now(timezone.utc)

        db.commit()

        # 사용자에게 알림
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"VIP 승인 완료!\n\n"
                    f"기간: {duration_days}일\n"
                    f"만료일: {user.vip_expires_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"VIP 혜택을 마음껏 즐기세요!"
                ),
            )
        except Exception as e:
            logger.error(f"사용자 알림 전송 실패: {e}")

        # 관리자에게 확인 메시지
        await update.message.reply_text(
            f"VIP 승인 완료\n\n"
            f"사용자: {user.display_name}\n"
            f"기간: {duration_days}일\n"
            f"만료일: {user.vip_expires_at.strftime('%Y-%m-%d %H:%M')}"
        )


async def cmd_approve_business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /approve_business [user_id] [chat_id] - Business Plan 승인

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    # 관리자 권한 확인
    if not is_admin(user_tg_id):
        await update.message.reply_text("❌ 관리자 권한이 필요합니다.")
        return

    # 인자 확인
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "[오류] 사용법: /approve_business [user_id] [chat_id]\n"
            "예: /approve_business 123456789 -100123456789"
        )
        return

    try:
        target_user_id = int(context.args[0])
        chat_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text("[오류] 올바른 숫자를 입력해주세요.")
        return

    with get_db() as db:
        # 사용자 조회
        user = db.query(User).filter(User.tg_user_id == target_user_id).first()
        if not user:
            await update.message.reply_text("[오류] 사용자를 찾을 수 없습니다.")
            return

        # 그룹 조회 또는 생성
        group = db.query(Group).filter(Group.chat_id == chat_id).first()
        if not group:
            group = Group(
                chat_id=chat_id,
                plan=PlanType.BUSINESS,
                owner_user_id=user.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            db.add(group)
        else:
            group.plan = PlanType.BUSINESS
            group.owner_user_id = user.id
            if group.expires_at and group.expires_at > datetime.now(timezone.utc):
                group.expires_at += timedelta(days=30)
            else:
                group.expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        # 승인 요청 상태 업데이트
        approval = (
            db.query(Approval)
            .filter(
                Approval.user_id == user.id,
                Approval.type == ApprovalType.BUSINESS,
                Approval.status == ApprovalStatus.PENDING,
            )
            .order_by(Approval.created_at.desc())
            .first()
        )

        if approval:
            approval.status = ApprovalStatus.APPROVED
            admin_user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
            approval.approved_by = admin_user.id if admin_user else None
            approval.approved_at = datetime.now(timezone.utc)

        db.commit()

        # 사용자에게 알림
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"Business Plan 승인 완료!\n\n"
                    f"그룹 Chat ID: {chat_id}\n"
                    f"만료일: {group.expires_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"커스터마이징 옵션은 별도 안내드립니다."
                ),
            )
        except Exception as e:
            logger.error(f"사용자 알림 전송 실패: {e}")

        # 관리자에게 확인 메시지
        await update.message.reply_text(
            f"Business Plan 승인 완료\n\n"
            f"사용자: {user.display_name}\n"
            f"그룹 Chat ID: {chat_id}\n"
            f"만료일: {group.expires_at.strftime('%Y-%m-%d %H:%M')}"
        )


async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /reject [user_id] [사유] - 승인 거절

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    # 관리자 권한 확인
    if not is_admin(user_tg_id):
        await update.message.reply_text("❌ 관리자 권한이 필요합니다.")
        return

    # 인자 확인
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "[오류] 사용법: /reject [user_id] [사유]\n" "예: /reject 123456789 입금 확인 불가"
        )
        return

    try:
        target_user_id = int(context.args[0])
        reason = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("[오류] 올바른 사용자 ID를 입력해주세요.")
        return

    with get_db() as db:
        # 사용자 조회
        user = db.query(User).filter(User.tg_user_id == target_user_id).first()
        if not user:
            await update.message.reply_text("[오류] 사용자를 찾을 수 없습니다.")
            return

        # 승인 요청 상태 업데이트
        approval = (
            db.query(Approval)
            .filter(
                Approval.user_id == user.id, Approval.status == ApprovalStatus.PENDING
            )
            .order_by(Approval.created_at.desc())
            .first()
        )

        if not approval:
            await update.message.reply_text("[오류] 대기 중인 승인 요청이 없습니다.")
            return

        approval.status = ApprovalStatus.REJECTED
        approval.rejection_reason = reason
        db.commit()

        # 사용자에게 알림
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"승인 거절\n\n"
                    f"유형: {approval.type.value}\n"
                    f"사유: {reason}\n\n"
                    f"문의사항이 있으시면 관리자에게 연락해주세요."
                ),
            )
        except Exception as e:
            logger.error(f"사용자 알림 전송 실패: {e}")

        # 관리자에게 확인 메시지
        await update.message.reply_text(
            f"승인 거절 완료\n\n" f"사용자: {user.display_name}\n" f"사유: {reason}"
        )


async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /revoke [user_id] - VIP 해제

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    # 관리자 권한 확인
    if not is_admin(user_tg_id):
        await update.message.reply_text("❌ 관리자 권한이 필요합니다.")
        return

    # 인자 확인
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "[오류] 사용법: /revoke [user_id]\n" "예: /revoke 123456789"
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("[오류] 올바른 사용자 ID를 입력해주세요.")
        return

    with get_db() as db:
        # 사용자 조회
        user = db.query(User).filter(User.tg_user_id == target_user_id).first()
        if not user:
            await update.message.reply_text("[오류] 사용자를 찾을 수 없습니다.")
            return

        # VIP 해제
        user.is_vip = False
        user.vip_expires_at = None
        db.commit()

        # 사용자에게 알림
        try:
            await context.bot.send_message(
                chat_id=target_user_id, text="[경고] VIP 멤버십이 해제되었습니다."
            )
        except Exception as e:
            logger.error(f"사용자 알림 전송 실패: {e}")

        # 관리자에게 확인 메시지
        await update.message.reply_text(f"VIP 해제 완료\n\n" f"사용자: {user.display_name}")


async def cmd_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /add_balance [user_id 또는 @username] [금액] - 사용자 잔액 추가

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
            "사용법: /add_balance [user_id 또는 @username] [금액]\n"
            "예: /add_balance 123456789 1000\n"
            "예: /add_balance @username 1000"
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
