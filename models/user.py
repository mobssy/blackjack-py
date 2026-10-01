"""
JackPy - User 모델
사용자 정보, 지갑, 통계 관리
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    DateTime,
    JSON,
    Numeric,
    func,
)
from models.base import Base, TimestampMixin

# 일일 보상 리셋 기준 시간대 (한국 표준시)
KST = timezone(timedelta(hours=9))

# 신규 사용자 시작 잔액
STARTING_WALLET = 1000.0


class User(Base, TimestampMixin):
    """
    텔레그램 사용자 모델

    Attributes:
        id: Primary Key
        tg_user_id: 텔레그램 사용자 ID (고유)
        username: 텔레그램 사용자명
        first_name: 이름
        wallet: 잔액 (Decimal)
        last_daily_at: 마지막 데일리 보상 수령일
        stats_json: 통계 정보 (JSON)
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tg_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(64), nullable=True)
    first_name = Column(String(128), nullable=True)

    # 게임 관련
    wallet = Column(
        Numeric(precision=15, scale=2), default=STARTING_WALLET, nullable=False
    )
    # (레거시) VIP 컬럼 — 기능은 제거됨. 기존 DB의 NOT NULL 컬럼이라
    # 신규 사용자 INSERT가 깨지지 않도록 정의만 유지한다.
    is_vip = Column(Boolean, default=False, nullable=False)
    vip_expires_at = Column(DateTime, nullable=True)

    # 데일리 보상
    last_daily_at = Column(DateTime, nullable=True)

    # 언어 설정 ('ko' 또는 'en')
    language = Column(String(2), default="ko", nullable=False, server_default="ko")

    # 통계 (JSON 형태)
    # 예: {"total_games": 0, "wins": 0, "losses": 0, "total_bet": 0, "total_profit": 0}
    stats_json = Column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"

    @property
    def display_name(self) -> str:
        """표시용 이름"""
        if self.username:
            return f"@{self.username}"
        elif self.first_name:
            return self.first_name
        else:
            return f"User#{self.tg_user_id}"

    @classmethod
    def create_new(
        cls,
        tg_user_id: int,
        username: Optional[str],
        first_name: Optional[str],
        language: str = "ko",
    ) -> "User":
        """신규 사용자 생성 (시작 잔액·빈 통계 — 등록 경로가 달라도 같은 초기값)"""
        return cls(
            tg_user_id=tg_user_id,
            username=username,
            first_name=first_name,
            wallet=STARTING_WALLET,
            language=language,
            stats_json={
                "total_games": 0,
                "wins": 0,
                "losses": 0,
                "total_bet": 0,
                "total_profit": 0,
            },
        )

    @classmethod
    def find_by_username(cls, db, username: str) -> Optional["User"]:
        """@ 없는 username으로 조회 (텔레그램 username은 대소문자를 구분하지 않음)"""
        return (
            db.query(cls).filter(func.lower(cls.username) == username.lower()).first()
        )

    def add_wallet(self, amount: float):
        """잔액 추가"""
        self.wallet += Decimal(str(amount))

    def deduct_wallet(self, amount: float) -> bool:
        """
        잔액 차감

        Returns:
            bool: 차감 성공 여부
        """
        amount_decimal = Decimal(str(amount))
        if self.wallet >= amount_decimal:
            self.wallet -= amount_decimal
            return True
        return False

    def update_stats(self, **kwargs: Any) -> None:
        """통계 업데이트"""
        if self.stats_json is None:
            self.stats_json = {}

        # 새로운 딕셔너리를 만들어서 할당 (SQLAlchemy가 변경 감지하도록)
        new_stats: Dict[str, Any] = dict(self.stats_json)
        for key, value in kwargs.items():
            if key in new_stats:
                new_stats[key] += value
            else:
                new_stats[key] = value

        # 새로운 딕셔너리로 교체 (이렇게 해야 SQLAlchemy가 변경을 감지함)
        self.stats_json = new_stats

    def can_claim_daily(self) -> bool:
        """데일리 보상 수령 가능 여부 (KST 자정 기준 리셋)"""
        if self.last_daily_at is None:
            return True
        last = self.last_daily_at
        if last.tzinfo is None:
            # DB에서 naive datetime으로 조회되는 경우 UTC로 간주
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return last.astimezone(KST).date() < now.astimezone(KST).date()
