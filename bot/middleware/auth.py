"""
JackPy - 인증 미들웨어
사용자 및 그룹 자동 등록/조회
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from models import get_db, User, Group, GroupMember

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
                user = User.create_new(user_tg_id, username, first_name)
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
                # 그룹 자동 등록
                group = Group(chat_id=chat_id, title=title)
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

            # 그룹 멤버십 기록 (그룹별 랭킹용)
            _record_group_member(db, chat_id, update)

    except Exception as e:
        logger.error(f"그룹 미들웨어 오류: {e}")


def _record_group_member(db, chat_id: int, update: Update) -> None:
    """그룹에서 메시지를 보낸 사용자를 GroupMember로 기록 (중복 무시)"""
    if not update.effective_user:
        return

    user = db.query(User).filter(User.tg_user_id == update.effective_user.id).first()
    if not user:
        # user_middleware가 아직 등록하지 못한 경우 다음 메시지에서 기록
        return

    exists = (
        db.query(GroupMember)
        .filter(GroupMember.chat_id == chat_id, GroupMember.user_id == user.id)
        .first()
    )
    if not exists:
        db.add(GroupMember(chat_id=chat_id, user_id=user.id))
        db.commit()


async def logging_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    명령어 로깅 미들웨어

    봇이 그룹의 일반 대화까지 수신할 수 있으므로(개인정보), 대화 내용은 기록하지
    않고 `/`로 시작하는 명령어만 기록한다.

    Args:
        update: 업데이트 객체
        context: 컨텍스트 객체
    """
    message = update.message
    if not message or not message.text or not message.text.startswith("/"):
        return

    user_id = update.effective_user.id if update.effective_user else "unknown"
    chat_id = update.effective_chat.id if update.effective_chat else "unknown"
    logger.info(f"Command: user={user_id}, chat={chat_id}, text={message.text}")
