"""
JackPy - 보상 로직 테스트
출석 스트릭 및 파산 구제 계산 테스트
"""

from datetime import datetime, timedelta, timezone

from models.user import KST
from bot.utils.rewards import (
    DAILY_BASE_REWARD,
    DAILY_STREAK_BONUS_CAP_DAYS,
    DAILY_STREAK_BONUS_PER_DAY,
    DAILY_VIP_REWARD,
    RESCUE_COOLDOWN_HOURS,
    RESCUE_THRESHOLD,
    can_rescue,
    daily_reward_amount,
    next_daily_streak,
    parse_stored_datetime,
)

# 테스트 기준 시각: KST 2026-07-09 정오 (UTC 03:00)
NOW = datetime(2026, 7, 9, 3, 0, tzinfo=timezone.utc)


class TestNextDailyStreak:
    """출석 스트릭 계산 테스트"""

    def test_first_claim(self):
        """첫 수령은 1일차"""
        assert next_daily_streak(None, 0, now=NOW) == 1

    def test_claimed_yesterday_extends_streak(self):
        """어제(KST) 수령했으면 스트릭 연장"""
        yesterday = NOW - timedelta(days=1)
        assert next_daily_streak(yesterday, 3, now=NOW) == 4

    def test_missed_a_day_resets_streak(self):
        """하루 걸렀으면 1일차부터 다시"""
        two_days_ago = NOW - timedelta(days=2)
        assert next_daily_streak(two_days_ago, 5, now=NOW) == 1

    def test_kst_date_boundary(self):
        """KST 자정 경계: 어제 KST 23시(UTC 14시) 수령 → 연장"""
        yesterday_kst_23 = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)
        assert yesterday_kst_23.astimezone(KST).date().day == 8  # KST 기준 어제인지 확인
        assert next_daily_streak(yesterday_kst_23, 2, now=NOW) == 3

    def test_naive_datetime_treated_as_utc(self):
        """naive datetime은 UTC로 간주"""
        yesterday_naive = (NOW - timedelta(days=1)).replace(tzinfo=None)
        assert next_daily_streak(yesterday_naive, 1, now=NOW) == 2

    def test_negative_stored_streak_sanitized(self):
        """저장된 스트릭이 손상돼도 1 이상 보장"""
        yesterday = NOW - timedelta(days=1)
        assert next_daily_streak(yesterday, -5, now=NOW) == 1


class TestDailyRewardAmount:
    """일일 보상 금액 테스트"""

    def test_base_reward_first_day(self):
        """1일차는 기본 보상만"""
        base, bonus = daily_reward_amount(False, 1)
        assert base == DAILY_BASE_REWARD
        assert bonus == 0.0

    def test_vip_base_reward(self):
        """VIP는 기본 보상 상향"""
        base, _ = daily_reward_amount(True, 1)
        assert base == DAILY_VIP_REWARD

    def test_streak_bonus_grows(self):
        """스트릭에 따라 보너스 증가"""
        _, bonus = daily_reward_amount(False, 3)
        assert bonus == 2 * DAILY_STREAK_BONUS_PER_DAY

    def test_streak_bonus_capped(self):
        """보너스는 상한 일수까지만 증가"""
        _, bonus_at_cap = daily_reward_amount(False, DAILY_STREAK_BONUS_CAP_DAYS + 1)
        _, bonus_over_cap = daily_reward_amount(False, 30)
        assert bonus_at_cap == DAILY_STREAK_BONUS_CAP_DAYS * DAILY_STREAK_BONUS_PER_DAY
        assert bonus_over_cap == bonus_at_cap


class TestCanRescue:
    """파산 구제 가능 여부 테스트"""

    def test_rescue_when_broke_first_time(self):
        """잔액 0 + 구제 이력 없음 → 가능"""
        assert can_rescue(0.0, None, now=NOW) is True

    def test_no_rescue_with_enough_balance(self):
        """잔액이 임계값 이상이면 불가"""
        assert can_rescue(RESCUE_THRESHOLD, None, now=NOW) is False

    def test_no_rescue_during_cooldown(self):
        """쿨다운 중에는 불가"""
        recent = NOW - timedelta(hours=RESCUE_COOLDOWN_HOURS - 1)
        assert can_rescue(0.0, recent, now=NOW) is False

    def test_rescue_after_cooldown(self):
        """쿨다운이 지나면 다시 가능"""
        old = NOW - timedelta(hours=RESCUE_COOLDOWN_HOURS)
        assert can_rescue(0.0, old, now=NOW) is True

    def test_naive_last_rescue_treated_as_utc(self):
        """naive 저장 시각도 크래시 없이 처리"""
        old_naive = (NOW - timedelta(hours=RESCUE_COOLDOWN_HOURS + 1)).replace(
            tzinfo=None
        )
        assert can_rescue(0.0, old_naive, now=NOW) is True


class TestParseStoredDatetime:
    """저장 시각 파싱 테스트"""

    def test_parse_valid_iso(self):
        """ISO 문자열 왕복 파싱"""
        assert parse_stored_datetime(NOW.isoformat()) == NOW

    def test_parse_none_and_empty(self):
        """빈 값은 None"""
        assert parse_stored_datetime(None) is None
        assert parse_stored_datetime("") is None

    def test_parse_corrupted_value(self):
        """손상된 값은 None (크래시 금지)"""
        assert parse_stored_datetime("not-a-date") is None
