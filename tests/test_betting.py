"""
JackPy - 베팅 입력 검증 테스트
소액 베팅 반올림 칩 복제, nan/inf 입력 등 보안 회귀 방지
"""

from decimal import Decimal

import pytest

from bot.utils.betting import (
    MIN_BET,
    BetError,
    BetRequest,
    is_valid_amount,
    parse_bet,
)
from bot.utils.i18n import STRINGS


class TestParseBet:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("100", "100"),
            ("12.5", "12.5"),
            ("12.50", "12.50"),
            ("1", "1"),
            (" 7 ", "7"),
        ],
    )
    def test_valid_amounts(self, raw, expected):
        request = parse_bet(raw)
        assert request == BetRequest(all_in=False, amount=Decimal(expected))

    @pytest.mark.parametrize("raw", ["all", "ALL", "올인"])
    def test_all_in(self, raw):
        assert parse_bet(raw) == BetRequest(all_in=True)

    @pytest.mark.parametrize(
        "raw",
        ["nan", "NaN", "inf", "-inf", "Infinity", "sNaN", "abc", "", "1e30", "1,000"],
    )
    def test_invalid_input(self, raw):
        with pytest.raises(BetError) as e:
            parse_bet(raw)
        assert e.value.key == "deal_invalid"

    @pytest.mark.parametrize("raw", ["0", "-5", "-0.01"])
    def test_non_positive(self, raw):
        with pytest.raises(BetError) as e:
            parse_bet(raw)
        assert e.value.key == "deal_positive"

    @pytest.mark.parametrize("raw", ["0.004", "1.005", "10.001", "5e-3"])
    def test_sub_cent_rejected(self, raw):
        """1센트 미만 단위: 반올림 칩 복제 버그의 원인이라 거부"""
        with pytest.raises(BetError) as e:
            parse_bet(raw)
        assert e.value.key == "bet_decimals"

    @pytest.mark.parametrize("raw", ["0.5", "0.99", "0.01"])
    def test_below_minimum(self, raw):
        with pytest.raises(BetError) as e:
            parse_bet(raw)
        assert e.value.key == "bet_min"
        assert e.value.kwargs == {"min": float(MIN_BET)}

    def test_error_keys_exist_in_both_languages(self):
        for key in ("deal_invalid", "deal_positive", "bet_decimals", "bet_min"):
            assert key in STRINGS["ko"] and key in STRINGS["en"]


class TestResolve:
    def test_amount(self):
        assert parse_bet("25.50").resolve(Decimal("1000")) == 25.5

    def test_all_in_uses_wallet(self):
        assert parse_bet("all").resolve(Decimal("321.45")) == 321.45


class TestIsValidAmount:
    def test_minimum_boundary(self):
        assert is_valid_amount(1.0) is True
        assert is_valid_amount(0.99) is False

    def test_small_all_in_rejected(self):
        """잔액이 최소 베팅 미만이면 올인도 불가 (파산 구제 경로로)"""
        assert is_valid_amount(0.5) is False
        assert is_valid_amount(0.0) is False
