"""
JackPy - Models 테스트
User, Group, GroupMember, Round 모델 테스트
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models.user import STARTING_WALLET, User
from models.group import Group
from models.group_member import GroupMember
from models.round import Round, GameOutcome


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

    def test_create_new_defaults(self, db_session):
        """create_new: 시작 잔액·빈 통계·기본 언어로 생성"""
        user = User.create_new(42, "newbie", "New")
        db_session.add(user)
        db_session.commit()

        assert user.wallet == Decimal(str(STARTING_WALLET))
        assert user.language == "ko"
        assert user.stats_json["total_games"] == 0
        assert user.stats_json["total_profit"] == 0

    def test_create_new_language(self, db_session):
        """create_new: 언어 선택으로 가입하면 해당 언어 저장"""
        user = User.create_new(43, None, "Eng", language="en")
        db_session.add(user)
        db_session.commit()

        assert user.language == "en"
        assert user.display_name == "Eng"

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
        group = Group(chat_id=-123456789, title="Test Group")
        db_session.add(group)
        db_session.commit()

        assert group.id is not None
        assert group.chat_id == -123456789


class TestLegacyColumns:
    """
    제거된 VIP/플랜 기능의 NOT NULL 컬럼이 기본값으로 채워지는지 검증

    운영 DB 구조는 유지하므로, 코드에서 값을 지정하지 않아도
    신규 사용자/그룹 INSERT가 실패하지 않아야 한다.
    """

    def test_new_user_insert_without_vip_fields(self, db_session):
        user = User(tg_user_id=555)
        db_session.add(user)
        db_session.commit()
        assert user.is_vip is False

    def test_new_group_insert_without_plan_fields(self, db_session):
        group = Group(chat_id=-555)
        db_session.add(group)
        db_session.commit()
        assert group.plan is not None
        assert group.settings_json == {}


class TestGroupMemberModel:
    """GroupMember 모델 테스트"""

    def test_create_group_member(self, db_session):
        """그룹 멤버 기록 생성"""
        user = User(tg_user_id=123)
        db_session.add(user)
        db_session.commit()

        member = GroupMember(chat_id=-100123, user_id=user.id)
        db_session.add(member)
        db_session.commit()

        assert member.id is not None
        assert member.chat_id == -100123
        assert member.user_id == user.id

    def test_unique_constraint(self, db_session):
        """같은 (chat_id, user_id) 중복 기록 불가"""
        from sqlalchemy.exc import IntegrityError

        user = User(tg_user_id=123)
        db_session.add(user)
        db_session.commit()

        db_session.add(GroupMember(chat_id=-100123, user_id=user.id))
        db_session.commit()

        db_session.add(GroupMember(chat_id=-100123, user_id=user.id))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_same_user_multiple_groups(self, db_session):
        """같은 사용자가 여러 그룹에 기록 가능"""
        user = User(tg_user_id=123)
        db_session.add(user)
        db_session.commit()

        db_session.add(GroupMember(chat_id=-100123, user_id=user.id))
        db_session.add(GroupMember(chat_id=-100456, user_id=user.id))
        db_session.commit()

        assert db_session.query(GroupMember).count() == 2


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

    @pytest.mark.parametrize("model", [Round, Group, GroupMember])
    def test_chat_id_is_bigint(self, model):
        """슈퍼그룹 ID(-100…)는 32비트를 넘으므로 PostgreSQL에서도 담기도록 BIGINT"""
        assert isinstance(model.__table__.c.chat_id.type, BigInteger)

    def test_supergroup_chat_id_roundtrip(self, db_session):
        user = User(tg_user_id=123)
        db_session.add(user)
        db_session.commit()
        round_obj = Round(
            user_id=user.id,
            chat_id=-1001234567890,
            bet=10.0,
            player_hand=["9S", "8H"],
            dealer_hand=["7D", "9C"],
            outcome=GameOutcome.WIN,
            payout=10.0,
        )
        db_session.add(round_obj)
        db_session.commit()
        db_session.expire_all()
        assert db_session.get(Round, round_obj.id).chat_id == -1001234567890

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


class TestDailyResetKST:
    """일일 보상 KST 자정 리셋 테스트"""

    def test_can_claim_when_never_claimed(self, db_session):
        user = User(tg_user_id=123)
        assert user.can_claim_daily() is True

    def test_cannot_claim_same_kst_day(self, db_session):
        """오늘(KST) 이미 수령했으면 불가"""
        from models.user import KST

        user = User(tg_user_id=123)
        user.last_daily_at = datetime.now(timezone.utc)
        assert user.can_claim_daily() is False

        # 오늘 KST 자정 직후 수령한 경우도 불가
        kst_midnight = datetime.now(KST).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        user.last_daily_at = kst_midnight + timedelta(minutes=1)
        assert user.can_claim_daily() is False

    def test_can_claim_after_kst_midnight(self, db_session):
        """마지막 수령이 어제(KST)면 UTC 날짜와 무관하게 가능"""
        from models.user import KST

        user = User(tg_user_id=123)
        kst_midnight = datetime.now(KST).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # 어제 KST 23:59 수령 → 오늘 수령 가능
        user.last_daily_at = kst_midnight - timedelta(minutes=1)
        assert user.can_claim_daily() is True

    def test_naive_datetime_handled(self, db_session):
        """DB에서 naive로 조회된 last_daily_at도 크래시 없이 처리"""
        user = User(tg_user_id=123)
        user.last_daily_at = datetime.utcnow() - timedelta(days=2)
        assert user.can_claim_daily() is True
