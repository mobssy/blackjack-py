"""
JackPy - AdSchedule 모델
그룹별 광고 스케줄 관리
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, DateTime
from models.base import Base, TimestampMixin


class AdSchedule(Base, TimestampMixin):
    """
    광고 스케줄 모델

    무료 플랜 그룹의 광고 발송 주기를 관리합니다.

    Attributes:
        id: Primary Key
        chat_id: 텔레그램 채팅 ID (고유)
        last_sent_at: 마지막 광고 발송 시각
        interval_minutes: 광고 발송 간격 (분)
    """

    __tablename__ = "ad_schedules"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # 광고 발송 관리
    last_sent_at = Column(DateTime, nullable=True)
    interval_minutes = Column(Integer, default=60, nullable=False)  # 기본 1시간

    def __repr__(self) -> str:
        return (
            f"<AdSchedule(chat_id={self.chat_id}, interval={self.interval_minutes}min)>"
        )

    def can_send_ad(self) -> bool:
        """
        광고 발송 가능 여부 확인

        Returns:
            bool: 광고 발송 가능 여부
        """
        if self.last_sent_at is None:
            return True

        now = datetime.now(timezone.utc)
        elapsed_minutes: float = (now - self.last_sent_at).total_seconds() / 60
        return bool(elapsed_minutes >= self.interval_minutes)

    def mark_sent(self) -> None:
        """광고 발송 기록"""
        self.last_sent_at = datetime.now(timezone.utc)
