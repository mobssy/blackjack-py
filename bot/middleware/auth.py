"""
JackPy - 인증 미들웨어
사용자 및 그룹 자동 등록/조회
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from models import get_db, User, Group, PlanType

logger = logging.getLogger(__name__)


async def user_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    사용자 자동 등록/조회 미들웨어

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    if not update.effective_user:
        return

    user_tg_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name

    try:
        with get_db() as db:
            user = db.query(User).filter(User.tg_user_id == user_tg_id).first()

            if not user:
                # /start가 아닌 명령어로 첫 접속한 경우 자동 등록
                user = User(
                    tg_user_id=user_tg_id,
                    username=username,
                    first_name=first_name,
                    wallet=1000.0,
                    stats_json={
                        "total_games": 0,
                        "wins": 0,
                        "losses": 0,
                        "total_bet": 0,
                        "total_profit": 0
                    }
                )
                db.add(user)
                db.commit()
                logger.info(f"신규 사용자 자동 등록: {username} ({user_tg_id})")
            else:
                # 기존 사용자 정보 업데이트
                if user.username != username or user.first_name != first_name:
                    user.username = username
                    user.first_name = first_name
                    db.commit()

            # 컨텍스트에 사용자 정보 저장
            context.user_data["user_id"] = user.id
            context.user_data["user_tg_id"] = user_tg_id
            context.user_data["is_vip"] = user.is_vip_active

    except Exception as e:
        logger.error(f"사용자 미들웨어 오류: {e}")


async def group_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    그룹 자동 등록/조회 미들웨어

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    if not update.effective_chat or update.effective_chat.type == "private":
        return

    chat_id = update.effective_chat.id
    title = update.effective_chat.title

    try:
        with get_db() as db:
            group = db.query(Group).filter(Group.chat_id == chat_id).first()

            if not group:
                # 그룹 자동 등록 (무료 플랜)
                group = Group(
                    chat_id=chat_id,
                    title=title,
                    plan=PlanType.FREE
                )
                db.add(group)
                db.commit()
                logger.info(f"신규 그룹 자동 등록: {title} ({chat_id})")
            else:
                # 그룹 정보 업데이트
                if group.title != title:
                    group.title = title
                    db.commit()

            # 컨텍스트에 그룹 정보 저장
            context.chat_data["group_id"] = group.id
            context.chat_data["chat_id"] = chat_id
            context.chat_data["plan"] = group.plan.value
            context.chat_data["is_business"] = group.is_business

    except Exception as e:
        logger.error(f"그룹 미들웨어 오류: {e}")


async def logging_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    로깅 미들웨어

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    if update.message and update.message.text:
        user_id = update.effective_user.id if update.effective_user else "unknown"
        chat_id = update.effective_chat.id if update.effective_chat else "unknown"
        text = update.message.text

        logger.info(f"Message: user={user_id}, chat={chat_id}, text={text}")
