"""
JackPy - 프로필 핸들러
/my, /rank, /stats, /history 명령어 처리
"""

import logging
from datetime import timezone

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import desc, func

from models import get_db, User, Round, GroupMember
from models.user import KST
from bot.utils import t, get_user_lang, PayoutCalculator
from bot.utils.payouts import OUTCOME_I18N_KEYS

logger = logging.getLogger(__name__)

# /history 조회 라운드 수
HISTORY_LIMIT = 10


def _format_kst(dt) -> str:
    """naive UTC datetime을 KST 표시 문자열로 변환"""
    return dt.replace(tzinfo=timezone.utc).astimezone(KST).strftime("%m-%d %H:%M")


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
        lang = get_user_lang(user)
        if not user:
            await update.message.reply_text(t("deal_no_user", lang))
            return

        stats = user.stats_json or {}
        total_games = stats.get("total_games", 0)
        wins = stats.get("wins", 0)
        win_rate = (wins / total_games * 100) if total_games > 0 else 0

        vip_status = t("vip_active" if user.is_vip_active else "vip_inactive", lang)

        lines = [
            t("profile_title", lang),
            "",
            t("profile_user", lang, name=user.display_name),
            t("profile_vip", lang, vip=vip_status),
        ]
        if user.is_vip_active and user.vip_expires_at:
            lines.append(
                t(
                    "profile_vip_expires",
                    lang,
                    date=user.vip_expires_at.strftime("%Y-%m-%d"),
                )
            )
        lines += [
            "",
            t(
                "profile_finance",
                lang,
                balance=float(user.wallet),
                total_bet=stats.get("total_bet", 0),
                total_profit=stats.get("total_profit", 0),
            ),
            "",
            t(
                "profile_stats",
                lang,
                games=total_games,
                wins=wins,
                losses=stats.get("losses", 0),
                win_rate=win_rate,
            ),
            "",
            t("profile_actions", lang),
        ]

        await update.message.reply_text("\n".join(lines))


async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /rank - 랭킹 조회

    개인 채팅: 전역 잔액 순위 Top 10
    그룹 채팅: 해당 그룹에서 봇을 사용한 멤버끼리의 순위

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    user_tg_id = update.effective_user.id
    chat = update.effective_chat

    with get_db() as db:
        current_user = db.query(User).filter(User.tg_user_id == user_tg_id).first()
        lang = get_user_lang(current_user)
        if not current_user:
            await update.message.reply_text(t("deal_no_user", lang))
            return

        if chat.type in ("group", "supergroup"):
            user_query = (
                db.query(User)
                .join(GroupMember, GroupMember.user_id == User.id)
                .filter(GroupMember.chat_id == chat.id)
            )
            title = t("rank_group_title", lang, title=chat.title or "")
        else:
            user_query = db.query(User)
            title = t("rank_title", lang)

        message = _build_rank_message(user_query, current_user, lang, title)
        await update.message.reply_text(message)


def _build_rank_message(user_query, current_user, lang: str, title: str) -> str:
    """
    랭킹 목록 메시지 생성 (전역/그룹 공용)

    Args:
        user_query: 랭킹 대상 User 쿼리 (필터 적용 상태)
        current_user: 현재 사용자
        lang: 언어 코드
        title: 랭킹 제목

    Returns:
        str: 랭킹 메시지
    """
    top_users = user_query.order_by(desc(User.wallet)).limit(10).all()
    lines = [title]

    current_user_rank = None
    for idx, user in enumerate(top_users, 1):
        marker = "> " if user.id == current_user.id else "   "
        vip_badge = "[VIP]" if user.is_vip_active else ""
        lines.append(
            t(
                "rank_entry",
                lang,
                marker=marker,
                idx=idx,
                name=user.display_name,
                vip=vip_badge,
                balance=float(user.wallet),
            )
        )
        if user.id == current_user.id:
            current_user_rank = idx

    if current_user_rank is None:
        higher_users = user_query.filter(User.wallet > current_user.wallet).count()
        lines.append(
            t(
                "rank_your_rank",
                lang,
                rank=higher_users + 1,
                balance=float(current_user.wallet),
            )
        )

    lines.append(t("rank_footer", lang))
    return "\n".join(lines)


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
        lang = get_user_lang(user)
        if not user:
            await update.message.reply_text(t("deal_no_user", lang))
            return

        total_rounds = db.query(Round).filter(Round.user_id == user.id).count()
        total_bet = (
            db.query(func.sum(Round.bet)).filter(Round.user_id == user.id).scalar() or 0
        )
        # Round.payout은 라운드별 순손익(승리 +, 패배 -)이므로 합계가 곧 순이익
        net_profit = (
            db.query(func.sum(Round.payout)).filter(Round.user_id == user.id).scalar()
            or 0
        )

        max_bet = (
            db.query(func.max(Round.bet)).filter(Round.user_id == user.id).scalar() or 0
        )
        max_win = (
            db.query(func.max(Round.payout))
            .filter(Round.user_id == user.id, Round.payout > 0)
            .scalar()
            or 0
        )

        message = t(
            "stats_message",
            lang,
            rounds=total_rounds,
            total_bet=float(total_bet),
            net_profit=PayoutCalculator.format_payout(float(net_profit)),
            max_bet=float(max_bet),
            max_win=float(max_win),
            balance=float(user.wallet),
        )
        await update.message.reply_text(message)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /history - 최근 게임 기록 조회

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

        rounds = (
            db.query(Round)
            .filter(Round.user_id == user.id)
            .order_by(desc(Round.id))
            .limit(HISTORY_LIMIT)
            .all()
        )

        if not rounds:
            await update.message.reply_text(t("history_empty", lang))
            return

        lines = [t("history_title", lang, n=len(rounds))]
        for game_round in rounds:
            outcome_text = t(
                OUTCOME_I18N_KEYS.get(game_round.outcome, "result_lose"), lang
            )
            lines.append(
                t(
                    "history_entry",
                    lang,
                    emoji=PayoutCalculator.get_result_emoji(game_round.outcome),
                    date=_format_kst(game_round.created_at),
                    outcome=outcome_text,
                    bet=float(game_round.bet),
                    payout=PayoutCalculator.format_payout(float(game_round.payout)),
                    player=game_round.player_hand_str,
                    dealer=game_round.dealer_hand_str,
                )
            )

        await update.message.reply_text("\n".join(lines))
