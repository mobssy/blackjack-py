"""
JackPy - Approval 모델
VIP/비즈니스 플랜 승인 요청 관리
"""
from sqlalchemy import (
    Column, Integer, ForeignKey, String,
    Enum, Numeric, DateTime
)
from sqlalchemy.orm import relationship
import enum
from models.base import Base, TimestampMixin


class ApprovalType(enum.Enum):
    """승인 타입"""
    VIP = "VIP"
    BUSINESS = "BUSINESS"


class ApprovalStatus(enum.Enum):
    """승인 상태"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Approval(Base, TimestampMixin):
    """
    승인 요청 모델

    Attributes:
        id: Primary Key
        user_id: 요청 사용자 ID
        type: 승인 타입 (VIP/BUSINESS)
        status: 승인 상태
        depositor_name: 입금자명
        amount: 입금 금액
        duration_days: 요청 기간 (일)
        approved_by: 승인자 User ID
        approved_at: 승인일시
        rejection_reason: 거절 사유
    """
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 요청 정보
    type = Column(Enum(ApprovalType), nullable=False)
    status = Column(
        Enum(ApprovalStatus),
        default=ApprovalStatus.PENDING,
        nullable=False,
        index=True
    )

    # 입금 정보
    depositor_name = Column(String(128), nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    duration_days = Column(Integer, nullable=False)  # VIP 요청 기간

    # 승인 정보
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(512), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="approval_requests")
    approver = relationship("User", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<Approval(id={self.id}, user_id={self.user_id}, type={self.type.value}, status={self.status.value})>"

    @property
    def is_pending(self) -> bool:
        """대기 중 여부"""
        return self.status == ApprovalStatus.PENDING

    @property
    def is_approved(self) -> bool:
        """승인됨 여부"""
        return self.status == ApprovalStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        """거절됨 여부"""
        return self.status == ApprovalStatus.REJECTED
