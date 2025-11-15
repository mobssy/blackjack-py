"""
JackPy - 스케줄러
VIP 만료 체크 및 자동 알림
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from models import get_db, User, Group, PlanType

logger = logging.getLogger(__name__)


class JackPyScheduler:
    """
    JackPy 스케줄러

    주요 작업:
    - VIP 만료 체크 및 알림
    - 그룹 플랜 만료 체크
    - 통계 집계
    """

    def __init__(self, bot: Bot):
        """
        스케줄러 초기화

        Args:
            bot: 텔레그램 봇 인스턴스
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """스케줄러 시작"""
        # 매일 자정에 VIP 만료 체크
        self.scheduler.add_job(
            self.check_vip_expiration,
            CronTrigger(hour=0, minute=0),
            id="check_vip_expiration",
            replace_existing=True
        )

        # 매일 자정에 그룹 플랜 만료 체크
        self.scheduler.add_job(
            self.check_group_plan_expiration,
            CronTrigger(hour=0, minute=0),
            id="check_group_plan_expiration",
            replace_existing=True
        )

        # 매주 월요일 오전 9시 통계 리포트
        self.scheduler.add_job(
            self.weekly_stats_report,
            CronTrigger(day_of_week=0, hour=9, minute=0),
            id="weekly_stats_report",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("✅ 스케줄러 시작됨")

    def stop(self):
        """스케줄러 중지"""
        self.scheduler.shutdown()
        logger.info("⏹ 스케줄러 중지됨")

    async def check_vip_expiration(self):
        """
        VIP 만료 체크 및 알림

        만료 3일 전, 1일 전, 당일에 알림 발송
        """
        logger.info("🔍 VIP 만료 체크 시작")

        try:
            with get_db() as db:
                now = datetime.now(timezone.utc)

                # 만료 예정 사용자 조회
                expiring_users = db.query(User).filter(
                    User.is_vip == True,
                    User.vip_expires_at.isnot(None),
                    User.vip_expires_at > now,
                    User.vip_expires_at <= now + timedelta(days=3)
                ).all()

                for user in expiring_users:
                    days_left = (user.vip_expires_at - now).days

                    if days_left == 3:
                        message = (
                            f"⏰ VIP 만료 알림\n\n"
                            f"안녕하세요, {user.display_name}님!\n"
                            f"VIP 멤버십이 3일 후 만료됩니다.\n\n"
                            f"계속 VIP 혜택을 누리시려면 /vip 명령어로 갱신해주세요."
                        )
                        await self._send_notification(user.tg_user_id, message)
                    elif days_left == 1:
                        message = (
                            f"⚠️ VIP 만료 임박\n\n"
                            f"안녕하세요, {user.display_name}님!\n"
                            f"VIP 멤버십이 내일 만료됩니다.\n\n"
                            f"지금 바로 /vip 명령어로 갱신해주세요!"
                        )
                        await self._send_notification(user.tg_user_id, message)
                    elif days_left == 0:
                        message = (
                            f"⏰ VIP 만료\n\n"
                            f"안녕하세요, {user.display_name}님!\n"
                            f"VIP 멤버십이 오늘 만료됩니다.\n\n"
                            f"/vip 명령어로 갱신하시면 계속 이용하실 수 있습니다."
                        )
                        await self._send_notification(user.tg_user_id, message)

                # 만료된 사용자 VIP 상태 해제
                expired_users = db.query(User).filter(
                    User.is_vip == True,
                    User.vip_expires_at.isnot(None),
                    User.vip_expires_at <= now
                ).all()

                for user in expired_users:
                    user.is_vip = False
                    logger.info(f"VIP 만료: {user.display_name}")

                db.commit()
                logger.info(f"✅ VIP 만료 체크 완료 (알림: {len(expiring_users)}, 만료: {len(expired_users)})")

        except Exception as e:
            logger.error(f"❌ VIP 만료 체크 오류: {e}")

    async def check_group_plan_expiration(self):
        """그룹 플랜 만료 체크"""
        logger.info("🔍 그룹 플랜 만료 체크 시작")

        try:
            with get_db() as db:
                now = datetime.now(timezone.utc)

                # 만료된 그룹 조회
                expired_groups = db.query(Group).filter(
                    Group.plan.in_([PlanType.VIP, PlanType.BUSINESS]),
                    Group.expires_at.isnot(None),
                    Group.expires_at <= now
                ).all()

                for group in expired_groups:
                    # 무료 플랜으로 변경
                    old_plan = group.plan.value
                    group.plan = PlanType.FREE
                    logger.info(f"그룹 플랜 만료: {group.title} ({old_plan} -> FREE)")

                    # 오너에게 알림
                    if group.owner_user_id:
                        message = (
                            f"⏰ 그룹 플랜 만료\n\n"
                            f"그룹 '{group.title}'의 {old_plan} 플랜이 만료되었습니다.\n"
                            f"계속 이용하시려면 /business 명령어로 갱신해주세요."
                        )
                        await self._send_notification(group.owner.tg_user_id, message)

                db.commit()
                logger.info(f"✅ 그룹 플랜 만료 체크 완료 (만료: {len(expired_groups)})")

        except Exception as e:
            logger.error(f"❌ 그룹 플랜 만료 체크 오류: {e}")

    async def weekly_stats_report(self):
        """주간 통계 리포트 (관리자용)"""
        logger.info("📊 주간 통계 리포트 생성")
        # TODO: 구현 (관리자에게 주간 통계 발송)

    async def _send_notification(self, user_id: int, message: str):
        """
        사용자에게 알림 발송

        Args:
            user_id: 텔레그램 사용자 ID
            message: 메시지 내용
        """
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"알림 발송 실패 (user_id={user_id}): {e}")
