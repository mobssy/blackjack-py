"""
JackPy - Group 모델
텔레그램 그룹 정보
"""

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
import enum
from models.base import Base, TimestampMixin


class PlanType(enum.Enum):
    """(레거시) 플랜 타입 — 기능은 제거됨, 기존 groups.plan 컬럼 타입 호환용"""

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
    """

    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    title = Column(String(256), nullable=True)

    # (레거시) 플랜/오너/설정 컬럼 — 기능은 제거됨. 기존 DB의 NOT NULL 컬럼이
    # 있어 신규 그룹 INSERT가 깨지지 않도록 정의만 유지한다.
    plan = Column(Enum(PlanType), default=PlanType.FREE, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    settings_json = Column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, title={self.title})>"
