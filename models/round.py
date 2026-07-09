"""
JackPy - Round 모델
블랙잭 게임 라운드 기록
"""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, JSON, Enum
from sqlalchemy.orm import relationship
import enum
from models.base import Base, TimestampMixin


class GameOutcome(enum.Enum):
    """게임 결과"""

    WIN = "WIN"
    LOSS = "LOSS"
    PUSH = "PUSH"
    BLACKJACK = "BLACKJACK"
    BUST = "BUST"
    SURRENDER = "SURRENDER"


class Round(Base, TimestampMixin):
    """
    블랙잭 게임 라운드 모델

    Attributes:
        id: Primary Key
        user_id: 사용자 ID
        chat_id: 채팅 ID (선택)
        bet: 베팅 금액
        player_hand: 플레이어 패 (JSON 배열)
        dealer_hand: 딜러 패 (JSON 배열)
        outcome: 게임 결과
        payout: 정산 금액 (양수: 획득, 음수: 손실)
    """

    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chat_id = Column(Integer, nullable=True)  # 그룹 채팅 ID (선택)

    # 게임 정보
    bet = Column(Numeric(precision=15, scale=2), nullable=False)
    player_hand = Column(JSON, nullable=False)  # 예: ["AS", "KH"]
    dealer_hand = Column(JSON, nullable=False)  # 예: ["7D", "9C"]
    outcome = Column(Enum(GameOutcome), nullable=False)
    payout = Column(Numeric(precision=15, scale=2), nullable=False)

    # Relationships
    user = relationship("User", backref="rounds")

    def __repr__(self) -> str:
        return f"<Round(id={self.id}, user_id={self.user_id}, outcome={self.outcome.value}, payout={self.payout})>"

    @property
    def player_hand_str(self) -> str:
        """플레이어 패 문자열"""
        return " ".join(self.player_hand)

    @property
    def dealer_hand_str(self) -> str:
        """딜러 패 문자열"""
        return " ".join(self.dealer_hand)

    @property
    def is_win(self) -> bool:
        """승리 여부"""
        return self.outcome in (GameOutcome.WIN, GameOutcome.BLACKJACK)

    @property
    def is_push(self) -> bool:
        """푸시 여부"""
        return self.outcome == GameOutcome.PUSH
