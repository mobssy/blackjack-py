"""
JackPy - 정산 로직
블랙잭 게임 결과에 따른 정산 계산
"""

from typing import Tuple
from models.round import GameOutcome


class PayoutCalculator:
    """
    정산 계산기

    블랙잭 룰:
    - 블랙잭: 베팅액의 3:2 (1.5배)
    - 일반 승리: 베팅액의 1:1 (1배)
    - 푸시: 베팅액 반환 (0)
    - 패배: 베팅액 손실 (-1배)
    """

    # 정산 배율
    BLACKJACK_MULTIPLIER = 1.5
    WIN_MULTIPLIER = 1.0
    PUSH_MULTIPLIER = 0.0
    LOSS_MULTIPLIER = -1.0

    @staticmethod
    def calculate(outcome: GameOutcome, bet_amount: float) -> float:
        """
        결과에 따른 정산 금액 계산

        Args:
            outcome: 게임 결과
            bet_amount: 베팅 금액

        Returns:
            float: 정산 금액 (양수: 획득, 음수: 손실, 0: 무승부)
        """
        if outcome == GameOutcome.BLACKJACK:
            return bet_amount * PayoutCalculator.BLACKJACK_MULTIPLIER
        elif outcome == GameOutcome.WIN:
            return bet_amount * PayoutCalculator.WIN_MULTIPLIER
        elif outcome == GameOutcome.PUSH:
            return bet_amount * PayoutCalculator.PUSH_MULTIPLIER
        elif outcome in (GameOutcome.LOSS, GameOutcome.BUST):
            return bet_amount * PayoutCalculator.LOSS_MULTIPLIER
        else:
            return 0.0

    @staticmethod
    def format_payout(payout: float) -> str:
        """
        정산 금액 포맷팅

        Args:
            payout: 정산 금액

        Returns:
            str: 포맷팅된 문자열
        """
        if payout > 0:
            return f"+${payout:,.2f}"
        elif payout < 0:
            return f"-${abs(payout):,.2f}"
        else:
            return "$0.00"

    @staticmethod
    def get_outcome_message(outcome: GameOutcome) -> str:
        """
        결과 메시지 반환

        Args:
            outcome: 게임 결과

        Returns:
            str: 결과 메시지
        """
        messages = {
            GameOutcome.BLACKJACK: "블랙잭! 대박!",
            GameOutcome.WIN: "승리했습니다!",
            GameOutcome.PUSH: "무승부 (베팅금 반환)",
            GameOutcome.LOSS: "패배했습니다",
            GameOutcome.BUST: "버스트! (21 초과)",
        }
        return messages.get(outcome, "게임 종료")

    @staticmethod
    def get_result_emoji(outcome: GameOutcome) -> str:
        """
        결과 이모지 반환

        Args:
            outcome: 게임 결과

        Returns:
            str: 이모지
        """
        emojis = {
            GameOutcome.BLACKJACK: "🎉",
            GameOutcome.WIN: "✅",
            GameOutcome.PUSH: "🤝",
            GameOutcome.LOSS: "❌",
            GameOutcome.BUST: "💥",
        }
        return emojis.get(outcome, "🎲")


def determine_outcome(
    player_value: int,
    dealer_value: int,
    player_blackjack: bool,
    dealer_blackjack: bool,
    player_bust: bool,
    dealer_bust: bool,
) -> GameOutcome:
    """
    게임 결과 판정

    Args:
        player_value: 플레이어 핸드 값
        dealer_value: 딜러 핸드 값
        player_blackjack: 플레이어 블랙잭 여부
        dealer_blackjack: 딜러 블랙잭 여부
        player_bust: 플레이어 버스트 여부
        dealer_bust: 딜러 버스트 여부

    Returns:
        GameOutcome: 게임 결과
    """
    # 플레이어 버스트
    if player_bust:
        return GameOutcome.BUST

    # 딜러 버스트
    if dealer_bust:
        if player_blackjack:
            return GameOutcome.BLACKJACK
        return GameOutcome.WIN

    # 블랙잭 체크
    if player_blackjack and dealer_blackjack:
        return GameOutcome.PUSH
    if player_blackjack:
        return GameOutcome.BLACKJACK
    if dealer_blackjack:
        return GameOutcome.LOSS

    # 값 비교
    if player_value > dealer_value:
        return GameOutcome.WIN
    elif player_value < dealer_value:
        return GameOutcome.LOSS
    else:
        return GameOutcome.PUSH
