"""
JackPy - 보상 로직
일일 보상 출석 스트릭 및 파산 구제 계산 (텔레그램/DB 의존성 없음)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from models.user import KST

# 일일 보상
DAILY_BASE_REWARD = 200.0
DAILY_VIP_REWARD = 500.0
# 출석 스트릭: 2일차부터 하루당 +$25, 최대 7일치(+$175)까지 증가
DAILY_STREAK_BONUS_PER_DAY = 25.0
DAILY_STREAK_BONUS_CAP_DAYS = 7

# 파산 구제: 잔액이 임계값 미만이면 쿨다운마다 소액 지급
RESCUE_AMOUNT = 50.0
RESCUE_THRESHOLD = 10.0
RESCUE_COOLDOWN_HOURS = 4


def _as_utc(dt: datetime) -> datetime:
    """naive datetime은 UTC로 간주해 aware로 변환"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def next_daily_streak(
    last_daily_at: Optional[datetime],
    current_streak: int = 0,
    now: Optional[datetime] = None,
) -> int:
    """
    이번 수령 시점의 출석 스트릭 계산 (KST 날짜 기준)

    마지막 수령이 어제(KST)면 스트릭 연장, 아니면 1일차부터 다시 시작.

    Args:
        last_daily_at: 마지막 수령 시각 (naive는 UTC로 간주)
        current_streak: 현재 저장된 스트릭
        now: 현재 시각 (테스트용 오버라이드)

    Returns:
        int: 갱신된 스트릭 (1 이상)
    """
    if last_daily_at is None:
        return 1

    now = now or datetime.now(timezone.utc)
    last_date = _as_utc(last_daily_at).astimezone(KST).date()
    today = _as_utc(now).astimezone(KST).date()

    if last_date == today - timedelta(days=1):
        return max(current_streak, 0) + 1
    return 1


def daily_reward_amount(is_vip: bool, streak: int) -> Tuple[float, float]:
    """
    일일 보상 금액 계산

    Args:
        is_vip: VIP 여부
        streak: 출석 스트릭 (1 이상)

    Returns:
        Tuple[float, float]: (기본 보상, 스트릭 보너스)
    """
    base = DAILY_VIP_REWARD if is_vip else DAILY_BASE_REWARD
    bonus_days = min(max(streak - 1, 0), DAILY_STREAK_BONUS_CAP_DAYS)
    return base, bonus_days * DAILY_STREAK_BONUS_PER_DAY


def can_rescue(
    wallet: float,
    last_rescue_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> bool:
    """
    파산 구제금 지급 가능 여부

    Args:
        wallet: 현재 잔액
        last_rescue_at: 마지막 구제 시각 (naive는 UTC로 간주)
        now: 현재 시각 (테스트용 오버라이드)

    Returns:
        bool: 잔액이 임계값 미만이고 쿨다운이 지났으면 True
    """
    if wallet >= RESCUE_THRESHOLD:
        return False
    if last_rescue_at is None:
        return True

    now = now or datetime.now(timezone.utc)
    elapsed = _as_utc(now) - _as_utc(last_rescue_at)
    return elapsed >= timedelta(hours=RESCUE_COOLDOWN_HOURS)


def parse_stored_datetime(value: Optional[str]) -> Optional[datetime]:
    """stats_json에 ISO 문자열로 저장된 시각 파싱 (없거나 손상 시 None)"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
