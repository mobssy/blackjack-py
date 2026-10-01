"""
JackPy - 칩 선물(/give) 입력 해석과 이체 규칙
명령어 인자를 검증된 선물 요청으로 바꾸고, 두 사용자 사이 칩을 옮긴다
(텔레그램 의존성 없음 — DB 커밋은 호출자 책임)
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, List, Optional

from bot.utils.betting import BetError, parse_bet
from models.user import User


class GiveError(ValueError):
    """선물 오류 — 사용자에게 보여줄 i18n 키와 포맷 인자를 담는다"""

    def __init__(self, key: str, **kwargs: Any):
        super().__init__(key)
        self.key = key
        self.kwargs = kwargs


@dataclass(frozen=True)
class GiveRequest:
    """
    검증된 선물 요청

    Attributes:
        amount: 보낼 금액
        username: 받는 사람 @username (답장으로 지정하면 None)
    """

    amount: Decimal
    username: Optional[str] = None


def parse_give_args(args: List[str]) -> GiveRequest:
    """
    /give 인자 해석 — "/give @name 100", "/give 100 @name", 답장 + "/give 100"

    금액 규칙은 베팅과 같다 (최소 $1, 소수점 둘째 자리까지 — 센트 미만 복제 방지).
    올인 표현("all")은 실수 방지를 위해 받지 않는다.

    Raises:
        GiveError: 인자 개수/형식이 맞지 않거나 금액이 올바르지 않은 경우
    """
    usernames = [arg for arg in args if arg.startswith("@")]
    amounts = [arg for arg in args if not arg.startswith("@")]
    if len(amounts) != 1 or len(usernames) > 1:
        raise GiveError("give_usage")
    if usernames and len(usernames[0]) < 2:
        raise GiveError("give_usage")

    try:
        bet = parse_bet(amounts[0])
    except BetError:
        raise GiveError("give_invalid_amount")
    if bet.all_in:
        raise GiveError("give_invalid_amount")

    username = usernames[0][1:] if usernames else None
    return GiveRequest(amount=bet.amount, username=username)


def transfer_chips(sender: User, recipient: User, amount: Decimal) -> None:
    """
    sender → recipient 칩 이체 (DB 세션 커밋은 호출자 책임)

    Raises:
        GiveError: 자기 자신에게 보내거나 잔액이 부족한 경우
    """
    if sender.tg_user_id == recipient.tg_user_id:
        raise GiveError("give_self")
    if not sender.deduct_wallet(float(amount)):
        raise GiveError("give_no_balance", balance=float(sender.wallet))
    recipient.add_wallet(float(amount))
