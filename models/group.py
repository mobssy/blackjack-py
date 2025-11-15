"""
JackPy - Group 모델
텔레그램 그룹 및 플랜 관리
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
import enum
from models.base import Base, TimestampMixin


class PlanType(enum.Enum):
    """플랜 타입"""

    FREE = "FREE"
    VIP = "VIP"
    BUSINESS = "BUSINESS"


class Group(Base, TimestampMixin):
    """
    텔레그램 그룹 모델

    Attributes:
        id: Primary Key
        chat_id: 텔레그램 채팅 ID (고유)
        title: 그룹 이름
        plan: 플랜 타입 (FREE/VIP/BUSINESS)
        expires_at: 플랜 만료일
        owner_user_id: 그룹 오너 User ID
        settings_json: 커스텀 설정 (JSON)
    """

    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    title = Column(String(256), nullable=True)

    # 플랜 관리
    plan = Column(Enum(PlanType), default=PlanType.FREE, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # 오너 정보
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 커스텀 설정 (비즈니스 플랜용)
    # 예: {"logo_url": "...", "prefix": "/", "ad_enabled": false, "theme": "dark"}
    settings_json = Column(JSON, default=dict, nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_user_id])

    def __repr__(self):
        return f"<Group(id={self.id}, title={self.title}, plan={self.plan.value})>"

    @property
    def is_plan_active(self) -> bool:
        """플랜 활성 상태 확인"""
        if self.plan == PlanType.FREE:
            return True
        if self.expires_at is None:
            return True  # 무제한
        return datetime.now(timezone.utc) < self.expires_at

    @property
    def is_business(self) -> bool:
        """비즈니스 플랜 여부"""
        return self.plan == PlanType.BUSINESS and self.is_plan_active

    @property
    def is_vip(self) -> bool:
        """VIP 플랜 여부"""
        return self.plan == PlanType.VIP and self.is_plan_active

    @property
    def ad_enabled(self) -> bool:
        """광고 활성화 여부"""
        if self.is_business or self.is_vip:
            return False  # 유료 플랜은 광고 없음
        return self.settings_json.get("ad_enabled", True)

    def get_prefix(self) -> str:
        """커맨드 prefix 가져오기"""
        return self.settings_json.get("prefix", "/")
