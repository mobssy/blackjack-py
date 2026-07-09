"""
JackPy - 프로필 핸들러
/my, /rank 명령어 처리
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from models import get_db, User, Round
from sqlalchemy import func, desc

logger = logging.getLogger(__name__)


async def cmd_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /my - 내 프로필 카드

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user:
            await update.message.reply_text(
                "[오류] 등록되지 않은 사용자입니다. /start를 먼저 실행해주세요."
            )
            return

        # 통계 조회
        stats = user.stats_json or {}
        total_games = stats.get("total_games", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        total_bet = stats.get("total_bet", 0)
        total_profit = stats.get("total_profit", 0)

        # 승률 계산
        win_rate = (wins / total_games * 100) if total_games > 0 else 0

        # VIP 상태
        vip_status = "[활성]" if user.is_vip_active else "[비활성]"
        vip_expires = (
            user.vip_expires_at.strftime("%Y-%m-%d") if user.vip_expires_at else "N/A"
        )

        # 프로필 카드 (텍스트 기반)
        profile_card = (
            f"┏━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃  프로필 카드       ┃\n"
            f"┗━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"사용자: {user.display_name}\n"
            f"VIP: {vip_status}\n"
        )

        if user.is_vip_active:
            profile_card += f"만료일: {vip_expires}\n"

        profile_card += (
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"재무 정보\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"잔액: ${user.wallet:,.2f}\n"
            f"총 베팅: ${total_bet:,.2f}\n"
            f"총 수익: ${total_profit:,.2f}\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"게임 통계\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"총 게임: {total_games:,}회\n"
            f"승리: {wins:,}회\n"
            f"패배: {losses:,}회\n"
            f"승률: {win_rate:.1f}%\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"빠른 액션\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"/deal [금액] - 게임 시작\n"
            f"/daily - 일일 보상\n"
            f"/rank - 랭킹 조회\n"
        )

        await update.message.reply_text(profile_card)


async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /rank - 랭킹 조회

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    with get_db() as db:
        # 현재 사용자
        current_user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not current_user:
            await update.message.reply_text(
                "[오류] 등록되지 않은 사용자입니다. /start를 먼저 실행해주세요."
            )
            return

        # 수익 순위 (상위 10명)
        top_users = db.query(User).order_by(desc(User.wallet)).limit(10).all()

        # 랭킹 메시지 생성
        rank_message = (
            f"JackPy 랭킹\n" f"━━━━━━━━━━━━━━━━━━━\n\n" f"잔액 순위 (Top 10)\n\n"
        )

        current_user_rank = None
        for idx, user in enumerate(top_users, 1):
            # 현재 사용자 표시
            marker = "> " if user.id == current_user.id else "   "
            vip_badge = "[VIP]" if user.is_vip_active else ""

            rank_message += (
                f"{marker}{idx}. {user.display_name} {vip_badge}\n"
                f"    잔액: ${user.wallet:,.2f}\n"
            )

            if user.id == current_user.id:
                current_user_rank = idx

        # 현재 사용자가 Top 10에 없는 경우
        if current_user_rank is None:
            # 현재 사용자 순위 계산
            higher_users = (
                db.query(User).filter(User.wallet > current_user.wallet).count()
            )
            current_user_rank = higher_users + 1

            rank_message += (
                f"\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"당신의 순위: {current_user_rank}위\n"
                f"잔액: ${current_user.wallet:,.2f}\n"
            )

        rank_message += f"\n" f"━━━━━━━━━━━━━━━━━━━\n" f"더 높은 순위를 노려보세요!"

        await update.message.reply_text(rank_message)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /stats - 내 상세 통계

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        if not user:
            await update.message.reply_text(
                "[오류] 등록되지 않은 사용자입니다. /start를 먼저 실행해주세요."
            )
            return

        # 라운드별 통계 조회
        total_rounds = db.query(Round).filter(Round.user_id == user.id).count()
        total_bet = (
            db.query(func.sum(Round.bet)).filter(Round.user_id == user.id).scalar() or 0
        )
        total_payout = (
            db.query(func.sum(Round.payout)).filter(Round.user_id == user.id).scalar()
            or 0
        )

        # 최대 베팅 및 최대 승리
        max_bet_round = (
            db.query(Round)
            .filter(Round.user_id == user.id)
            .order_by(desc(Round.bet))
            .first()
        )

        max_win_round = (
            db.query(Round)
            .filter(Round.user_id == user.id, Round.payout > 0)
            .order_by(desc(Round.payout))
            .first()
        )

        max_bet = max_bet_round.bet if max_bet_round else 0
        max_win = max_win_round.payout if max_win_round else 0

        # 통계 메시지
        stats_message = (
            f"상세 통계\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"게임 기록\n"
            f"총 라운드: {total_rounds:,}회\n"
            f"총 베팅: ${total_bet:,.2f}\n"
            f"총 정산: ${total_payout:,.2f}\n"
            f"순이익: ${total_payout:,.2f}\n\n"
            f"최고 기록\n"
            f"최대 베팅: ${max_bet:,.2f}\n"
            f"최대 승리: ${max_win:,.2f}\n\n"
            f"현재 잔액\n"
            f"${user.wallet:,.2f}"
        )

        await update.message.reply_text(stats_message)
