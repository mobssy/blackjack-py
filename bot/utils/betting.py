"""
JackPy - 베팅 금액 검증
사용자 입력을 검증된 베팅 요청으로 변환 (텔레그램/DB 의존성 없음)

잔액은 DB에 소수점 둘째 자리로 저장되므로, 1센트 미만 단위 베팅을 허용하면
패배 시 차감액은 반올림으로 사라지고 승리 시 이득만 남아 칩을 복제할 수 있다.
최소 베팅과 소수점 자릿수 제한으로 막는다. nan/inf 같은 특수 값도 거부한다.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

MIN_BET = Decimal("1")
# 이보다 큰 입력은 숫자로 취급하지 않음 (Decimal 연산 정밀도 초과 방지)
_MAX_INPUT = Decimal("1e15")
_CENT = Decimal("0.01")
ALL_IN_WORDS = ("all", "올인")


class BetError(ValueError):
    """베팅 입력 오류 — 사용자에게 보여줄 i18n 키와 포맷 인자를 담는다"""

    def __init__(self, key: str, **kwargs: Any):
        super().__init__(key)
        self.key = key
        self.kwargs = kwargs


@dataclass(frozen=True)
class BetRequest:
    """
    검증된 베팅 요청

    Attributes:
        all_in: 올인 여부 (금액은 잔액에서 결정)
        amount: 올인이 아니면 베팅 금액
    """

    all_in: bool
    amount: Optional[Decimal] = None

    def resolve(self, wallet) -> float:
        """잔액 기준 실제 베팅액 (올인이면 잔액 전액)"""
        if self.all_in:
            return float(wallet)
        return float(self.amount)


def parse_bet(raw: str) -> BetRequest:
    """
    베팅 입력 검증

    Args:
        raw: 사용자 입력 (예: "100", "12.50", "all", "올인")

    Returns:
        BetRequest: 검증된 베팅 요청

    Raises:
        BetError: 숫자가 아니거나(nan/inf 포함), 0 이하, 최소 베팅 미만,
            소수점 셋째 자리 이상인 경우
    """
    text = raw.strip().lower()
    if text in ALL_IN_WORDS:
        return BetRequest(all_in=True)

    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise BetError("deal_invalid")
    if not amount.is_finite() or amount > _MAX_INPUT:
        raise BetError("deal_invalid")
    if amount <= 0:
        raise BetError("deal_positive")
    if amount != amount.quantize(_CENT):
        raise BetError("bet_decimals")
    if amount < MIN_BET:
        raise BetError("bet_min", min=float(MIN_BET))
    return BetRequest(all_in=False, amount=amount)


def is_valid_amount(bet: float) -> bool:
    """잔액으로 확정된 베팅액이 최소 베팅 이상인지 (올인 포함)"""
    return Decimal(str(bet)) >= MIN_BET
