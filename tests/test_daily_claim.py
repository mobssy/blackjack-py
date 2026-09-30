"""
JackPy - 일일 보상 지급 테스트
/daily와 출석 체크 버튼이 공유하는 claim_daily_reward 검증 (인메모리 DB)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.handlers.blackjack import claim_daily_reward
from bot.utils.i18n import t
from bot.utils.rewards import DAILY_BASE_REWARD, DAILY_STREAK_BONUS_PER_DAY
from models.base import Base
from models.user import User


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _user(db, **kwargs) -> User:
    user = User(tg_user_id=1, wallet=Decimal("100"), stats_json={}, **kwargs)
    db.add(user)
    db.commit()
    return user


class TestClaimDailyReward:
    def test_first_claim_pays_base_reward(self, db_session):
        user = _user(db_session)
        message = claim_daily_reward(db_session, user, "ko")

        assert float(user.wallet) == 100 + DAILY_BASE_REWARD
        assert user.stats_json["daily_streak"] == 1
        assert user.last_daily_at is not None
        assert f"${DAILY_BASE_REWARD:,.2f}" in message

    def test_second_claim_same_day_rejected(self, db_session):
        user = _user(db_session)
        claim_daily_reward(db_session, user, "ko")
        balance = float(user.wallet)

        message = claim_daily_reward(db_session, user, "ko")
        assert message == t("daily_already", "ko")
        assert float(user.wallet) == balance

    def test_consecutive_day_adds_streak_bonus(self, db_session):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        user = _user(db_session, last_daily_at=yesterday)
        user.stats_json = {"daily_streak": 2}
        db_session.commit()

        message = claim_daily_reward(db_session, user, "en")

        # 3일차: 기본 + 2일치 보너스
        expected = DAILY_BASE_REWARD + 2 * DAILY_STREAK_BONUS_PER_DAY
        assert float(user.wallet) == 100 + expected
        assert user.stats_json["daily_streak"] == 3
        assert "3-day attendance streak" in message

    def test_legacy_vip_flag_has_no_effect(self, db_session):
        """제거된 VIP 기능: 기존 DB에 is_vip=True가 남아 있어도 기본 보상"""
        user = _user(db_session, is_vip=True)
        claim_daily_reward(db_session, user, "ko")
        assert float(user.wallet) == 100 + DAILY_BASE_REWARD
