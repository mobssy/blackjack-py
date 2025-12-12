"""
JackPy - Models 테스트
User, Group, Round, Approval 모델 테스트
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models.user import User
from models.group import Group, PlanType
from models.round import Round, GameOutcome
from models.approval import Approval, ApprovalType, ApprovalStatus
from models.ad_schedule import AdSchedule


@pytest.fixture
def db_session():
    """테스트용 데이터베이스 세션"""
    # In-memory SQLite 사용
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestUserModel:
    """User 모델 테스트"""

    def test_create_user(self, db_session):
        """사용자 생성 테스트"""
        user = User(
            tg_user_id=123456789,
            username="testuser",
            first_name="Test",
            wallet=1000.0,
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.tg_user_id == 123456789
        assert user.username == "testuser"
        assert user.wallet == Decimal("1000.0")
        assert user.is_vip is False

    def test_display_name_with_username(self, db_session):
        """사용자명이 있는 경우 표시 이름"""
        user = User(tg_user_id=123, username="john")
        assert user.display_name == "@john"

    def test_display_name_with_first_name(self, db_session):
        """이름만 있는 경우 표시 이름"""
        user = User(tg_user_id=123, first_name="John")
        assert user.display_name == "John"

    def test_display_name_fallback(self, db_session):
        """아무것도 없는 경우 표시 이름"""
        user = User(tg_user_id=123)
        assert user.display_name == "User#123"

    def test_vip_active_status(self, db_session):
        """VIP 활성 상태 확인"""
        user = User(tg_user_id=123, is_vip=True)

        # VIP이지만 만료일 없음 (무제한)
        assert user.is_vip_active is True

        # VIP이고 미래 만료일
        user.vip_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        assert user.is_vip_active is True

        # VIP이지만 만료됨
        user.vip_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert user.is_vip_active is False

    def test_add_wallet(self, db_session):
        """잔액 추가 테스트"""
        user = User(tg_user_id=123, wallet=Decimal("1000.0"))
        user.add_wallet(500.0)
        assert user.wallet == Decimal("1500.0")

    def test_deduct_wallet_success(self, db_session):
        """잔액 차감 성공"""
        user = User(tg_user_id=123, wallet=Decimal("1000.0"))
        result = user.deduct_wallet(300.0)
        assert result is True
        assert user.wallet == Decimal("700.0")

    def test_deduct_wallet_insufficient(self, db_session):
        """잔액 부족으로 차감 실패"""
        user = User(tg_user_id=123, wallet=Decimal("100.0"))
        result = user.deduct_wallet(500.0)
        assert result is False
        assert user.wallet == Decimal("100.0")  # 변경 없음

    def test_update_stats(self, db_session):
        """통계 업데이트 테스트"""
        user = User(tg_user_id=123, stats_json={"wins": 5, "losses": 3})
        user.update_stats(wins=1, losses=1, total_profit=100.0)

        assert user.stats_json["wins"] == 6
        assert user.stats_json["losses"] == 4
        assert user.stats_json["total_profit"] == 100.0

    def test_can_claim_daily(self, db_session):
        """데일리 보상 수령 가능 여부"""
        user = User(tg_user_id=123)

        # 처음 수령 가능
        assert user.can_claim_daily() is True

        # 오늘 수령함
        user.last_daily_at = datetime.now(timezone.utc)
        assert user.can_claim_daily() is False

        # 어제 수령함 (오늘 수령 가능)
        user.last_daily_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert user.can_claim_daily() is True


class TestGroupModel:
    """Group 모델 테스트"""

    def test_create_group(self, db_session):
        """그룹 생성 테스트"""
        group = Group(chat_id=-123456789, title="Test Group", plan=PlanType.FREE)
        db_session.add(group)
        db_session.commit()

        assert group.id is not None
        assert group.chat_id == -123456789
        assert group.plan == PlanType.FREE

    def test_plan_active_free(self, db_session):
        """무료 플랜은 항상 활성"""
        group = Group(chat_id=-123, plan=PlanType.FREE)
        assert group.is_plan_active is True

    def test_plan_active_vip_no_expiry(self, db_session):
        """VIP 플랜 무제한"""
        group = Group(chat_id=-123, plan=PlanType.VIP, expires_at=None)
        assert group.is_plan_active is True

    def test_plan_active_vip_not_expired(self, db_session):
        """VIP 플랜 활성"""
        group = Group(
            chat_id=-123,
            plan=PlanType.VIP,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert group.is_plan_active is True

    def test_plan_active_vip_expired(self, db_session):
        """VIP 플랜 만료"""
        group = Group(
            chat_id=-123,
            plan=PlanType.VIP,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert group.is_plan_active is False

    def test_is_business(self, db_session):
        """비즈니스 플랜 여부"""
        group = Group(chat_id=-123, plan=PlanType.BUSINESS)
        assert group.is_business is True

    def test_ad_enabled_free_plan(self, db_session):
        """무료 플랜은 광고 활성"""
        group = Group(chat_id=-123, plan=PlanType.FREE, settings_json={})
        assert group.ad_enabled is True

    def test_ad_enabled_vip_plan(self, db_session):
        """VIP 플랜은 광고 비활성"""
        group = Group(
            chat_id=-123,
            plan=PlanType.VIP,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert group.ad_enabled is False

    def test_get_prefix_default(self, db_session):
        """기본 prefix"""
        group = Group(chat_id=-123, settings_json={})
        assert group.get_prefix() == "/"

    def test_get_prefix_custom(self, db_session):
        """커스텀 prefix"""
        group = Group(chat_id=-123, settings_json={"prefix": "!"})
        assert group.get_prefix() == "!"


class TestRoundModel:
    """Round 모델 테스트"""

    def test_create_round(self, db_session):
        """라운드 생성 테스트"""
        user = User(tg_user_id=123)
        db_session.add(user)
        db_session.commit()

        round_obj = Round(
            user_id=user.id,
            bet=100.0,
            player_hand=["AS", "KH"],
            dealer_hand=["7D", "9C"],
            outcome=GameOutcome.BLACKJACK,
            payout=150.0,
        )
        db_session.add(round_obj)
        db_session.commit()

        assert round_obj.id is not None
        assert round_obj.bet == Decimal("100.0")
        assert round_obj.outcome == GameOutcome.BLACKJACK

    def test_player_hand_str(self, db_session):
        """플레이어 패 문자열"""
        round_obj = Round(
            user_id=1,
            bet=100,
            player_hand=["AS", "KH"],
            dealer_hand=[],
            outcome=GameOutcome.WIN,
            payout=100,
        )
        assert round_obj.player_hand_str == "AS KH"

    def test_is_win(self, db_session):
        """승리 여부"""
        round_win = Round(
            user_id=1,
            bet=100,
            player_hand=[],
            dealer_hand=[],
            outcome=GameOutcome.WIN,
            payout=100,
        )
        assert round_win.is_win is True

        round_blackjack = Round(
            user_id=1,
            bet=100,
            player_hand=[],
            dealer_hand=[],
            outcome=GameOutcome.BLACKJACK,
            payout=150,
        )
        assert round_blackjack.is_win is True

        round_loss = Round(
            user_id=1,
            bet=100,
            player_hand=[],
            dealer_hand=[],
            outcome=GameOutcome.LOSS,
            payout=-100,
        )
        assert round_loss.is_win is False

    def test_is_push(self, db_session):
        """푸시 여부"""
        round_push = Round(
            user_id=1,
            bet=100,
            player_hand=[],
            dealer_hand=[],
            outcome=GameOutcome.PUSH,
            payout=0,
        )
        assert round_push.is_push is True


class TestApprovalModel:
    """Approval 모델 테스트"""

    def test_create_approval(self, db_session):
        """승인 요청 생성 테스트"""
        user = User(tg_user_id=123)
        db_session.add(user)
        db_session.commit()

        approval = Approval(
            user_id=user.id,
            type=ApprovalType.VIP,
            depositor_name="홍길동",
            amount=30.0,
            duration_days=30,
        )
        db_session.add(approval)
        db_session.commit()

        assert approval.id is not None
        assert approval.status == ApprovalStatus.PENDING
        assert approval.is_pending is True

    def test_approval_status(self, db_session):
        """승인 상태 테스트"""
        approval = Approval(
            user_id=1, type=ApprovalType.VIP, depositor_name="Test", amount=30, duration_days=30
        )

        # PENDING
        approval.status = ApprovalStatus.PENDING
        assert approval.is_pending is True
        assert approval.is_approved is False
        assert approval.is_rejected is False

        # APPROVED
        approval.status = ApprovalStatus.APPROVED
        assert approval.is_pending is False
        assert approval.is_approved is True
        assert approval.is_rejected is False

        # REJECTED
        approval.status = ApprovalStatus.REJECTED
        assert approval.is_pending is False
        assert approval.is_approved is False
        assert approval.is_rejected is True


class TestAdScheduleModel:
    """AdSchedule 모델 테스트"""

    def test_create_ad_schedule(self, db_session):
        """광고 스케줄 생성 테스트"""
        schedule = AdSchedule(chat_id=-123456789, interval_minutes=60)
        db_session.add(schedule)
        db_session.commit()

        assert schedule.id is not None
        assert schedule.chat_id == -123456789
        assert schedule.interval_minutes == 60

    def test_can_send_ad_first_time(self, db_session):
        """첫 광고 발송 가능"""
        schedule = AdSchedule(chat_id=-123, interval_minutes=60)
        assert schedule.can_send_ad() is True

    def test_can_send_ad_after_interval(self, db_session):
        """간격 경과 후 발송 가능"""
        schedule = AdSchedule(chat_id=-123, interval_minutes=60)
        schedule.last_sent_at = datetime.now(timezone.utc) - timedelta(minutes=61)
        assert schedule.can_send_ad() is True

    def test_can_send_ad_before_interval(self, db_session):
        """간격 경과 전 발송 불가"""
        schedule = AdSchedule(chat_id=-123, interval_minutes=60)
        schedule.last_sent_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        assert schedule.can_send_ad() is False

    def test_mark_sent(self, db_session):
        """광고 발송 기록"""
        schedule = AdSchedule(chat_id=-123, interval_minutes=60)
        before = datetime.now(timezone.utc)
        schedule.mark_sent()
        after = datetime.now(timezone.utc)

        assert schedule.last_sent_at is not None
        assert before <= schedule.last_sent_at <= after
