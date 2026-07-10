"""
JackPy - GroupMember 모델
그룹 채팅에서 봇과 상호작용한 사용자 기록 (그룹별 랭킹용)

텔레그램 API는 그룹 멤버 열거를 지원하지 않으므로,
그룹에서 메시지를 보낸 사용자를 관찰해 멤버십을 기록한다.
"""

from sqlalchemy import Column, Integer, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base, TimestampMixin


class GroupMember(Base, TimestampMixin):
    """
    그룹 멤버 관측 기록

    Attributes:
        id: Primary Key
        chat_id: 텔레그램 그룹 채팅 ID
        user_id: 사용자 ID (users.id)
    """

    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_group_member"),)

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    user = relationship("User", backref="group_memberships")

    def __repr__(self) -> str:
        return f"<GroupMember(chat_id={self.chat_id}, user_id={self.user_id})>"
