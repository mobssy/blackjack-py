"""
JackPy - Payouts 테스트
정산 로직 테스트
"""

import pytest
from bot.utils.payouts import (
    PayoutCalculator,
    determine_outcome,
    streak_bonus,
    update_streak,
)
from models.round import GameOutcome


class TestPayoutCalculator:
    """PayoutCalculator 테스트"""

    def test_blackjack_payout(self):
        """블랙잭 정산 테스트 (3:2)"""
        payout = PayoutCalculator.calculate(GameOutcome.BLACKJACK, 100)
        assert payout == 150.0  # 100 * 1.5

    def test_win_payout(self):
        """일반 승리 정산 테스트 (1:1)"""
        payout = PayoutCalculator.calculate(GameOutcome.WIN, 100)
        assert payout == 100.0  # 100 * 1

    def test_push_payout(self):
        """무승부 정산 테스트"""
        payout = PayoutCalculator.calculate(GameOutcome.PUSH, 100)
        assert payout == 0.0

    def test_loss_payout(self):
        """패배 정산 테스트"""
        payout = PayoutCalculator.calculate(GameOutcome.LOSS, 100)
        assert payout == -100.0  # 100 * -1

    def test_bust_payout(self):
        """버스트 정산 테스트"""
        payout = PayoutCalculator.calculate(GameOutcome.BUST, 100)
        assert payout == -100.0

    def test_surrender_payout(self):
        """서렌더 정산 테스트 (베팅액 절반 손실)"""
        payout = PayoutCalculator.calculate(GameOutcome.SURRENDER, 100)
        assert payout == -50.0  # 100 * -0.5

    def test_format_payout_positive(self):
        """양수 정산 포맷 테스트"""
        formatted = PayoutCalculator.format_payout(150.0)
        assert formatted == "+$150.00"

    def test_format_payout_negative(self):
        """음수 정산 포맷 테스트"""
        formatted = PayoutCalculator.format_payout(-100.0)
        assert formatted == "-$100.00"

    def test_format_payout_zero(self):
        """0 정산 포맷 테스트"""
        formatted = PayoutCalculator.format_payout(0.0)
        assert formatted == "$0.00"

    def test_outcome_message(self):
        """결과 메시지 테스트"""
        msg = PayoutCalculator.get_outcome_message(GameOutcome.BLACKJACK)
        assert "블랙잭" in msg


class TestDetermineOutcome:
    """게임 결과 판정 테스트"""

    def test_player_bust(self):
        """플레이어 버스트"""
        outcome = determine_outcome(
            player_value=25,
            dealer_value=20,
            player_blackjack=False,
            dealer_blackjack=False,
            player_bust=True,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.BUST

    def test_dealer_bust(self):
        """딜러 버스트"""
        outcome = determine_outcome(
            player_value=20,
            dealer_value=25,
            player_blackjack=False,
            dealer_blackjack=False,
            player_bust=False,
            dealer_bust=True,
        )
        assert outcome == GameOutcome.WIN

    def test_both_blackjack(self):
        """양쪽 모두 블랙잭"""
        outcome = determine_outcome(
            player_value=21,
            dealer_value=21,
            player_blackjack=True,
            dealer_blackjack=True,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.PUSH

    def test_player_blackjack(self):
        """플레이어만 블랙잭"""
        outcome = determine_outcome(
            player_value=21,
            dealer_value=20,
            player_blackjack=True,
            dealer_blackjack=False,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.BLACKJACK

    def test_dealer_blackjack(self):
        """딜러만 블랙잭"""
        outcome = determine_outcome(
            player_value=20,
            dealer_value=21,
            player_blackjack=False,
            dealer_blackjack=True,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.LOSS

    def test_player_higher(self):
        """플레이어가 더 높음"""
        outcome = determine_outcome(
            player_value=20,
            dealer_value=18,
            player_blackjack=False,
            dealer_blackjack=False,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.WIN

    def test_dealer_higher(self):
        """딜러가 더 높음"""
        outcome = determine_outcome(
            player_value=18,
            dealer_value=20,
            player_blackjack=False,
            dealer_blackjack=False,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.LOSS

    def test_push(self):
        """무승부"""
        outcome = determine_outcome(
            player_value=19,
            dealer_value=19,
            player_blackjack=False,
            dealer_blackjack=False,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.PUSH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestStreak:
    """연승 스트릭 보너스 테스트"""

    def test_update_streak_win_increments(self):
        """승리(정산 양수) 시 연승 +1"""
        assert update_streak(0, 100.0) == 1
        assert update_streak(4, 150.0) == 5

    def test_update_streak_loss_resets(self):
        """패배(정산 음수) 시 연승 리셋"""
        assert update_streak(7, -100.0) == 0

    def test_update_streak_push_keeps(self):
        """푸시(정산 0) 시 연승 유지"""
        assert update_streak(3, 0.0) == 3

    def test_no_bonus_below_three(self):
        """3연승 미만은 보너스 없음"""
        assert streak_bonus(1, 100.0) == 0.0
        assert streak_bonus(2, 100.0) == 0.0

    def test_bonus_at_three_wins(self):
        """3~4연승: 정산액의 10%"""
        assert streak_bonus(3, 100.0) == 10.0
        assert streak_bonus(4, 200.0) == 20.0

    def test_bonus_at_five_wins(self):
        """5연승 이상: 정산액의 20%"""
        assert streak_bonus(5, 100.0) == 20.0
        assert streak_bonus(10, 100.0) == 20.0

    def test_no_bonus_on_loss(self):
        """정산이 양수가 아니면 연승과 무관하게 보너스 없음"""
        assert streak_bonus(5, -100.0) == 0.0
        assert streak_bonus(5, 0.0) == 0.0
