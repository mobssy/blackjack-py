"""
JackPy - 블랙잭 게임 로직
텔레그램 의존성 없는 순수 게임 상태/규칙 클래스
"""

from typing import Tuple

from bot.utils.deck import (
    Deck,
    calculate_hand_value,
    is_blackjack,
    is_bust,
)
from bot.utils.payouts import PayoutCalculator, determine_outcome
from models.round import GameOutcome


class BlackjackGame:
    """블랙잭 게임 로직 클래스"""

    def __init__(self, user_id: int, bet: float):
        """
        게임 초기화

        Args:
            user_id: 사용자 ID
            bet: 베팅 금액
        """
        self.user_id = user_id
        self.bet = bet
        self.deck = Deck(num_decks=6)  # 6덱 사용
        self.player_hand = []
        self.dealer_hand = []
        self.is_finished = False

    @property
    def is_first_turn(self) -> bool:
        """첫 턴(첫 2장 상태) 여부 — 더블 다운/서렌더 가능 조건"""
        return len(self.player_hand) == 2

    def deal_initial(self):
        """초기 카드 2장씩 딜"""
        self.player_hand = self.deck.draw_multiple(2)
        self.dealer_hand = self.deck.draw_multiple(2)

    def player_hit(self):
        """플레이어 히트"""
        card = self.deck.draw()
        self.player_hand.append(card)

    def player_double(self):
        """
        더블 다운: 베팅 2배 후 카드 1장만 추가

        호출 전에 첫 턴 여부와 추가 베팅 잔액 확인 필요
        """
        self.bet *= 2
        self.player_hit()

    def surrender_result(self) -> Tuple[GameOutcome, float]:
        """
        서렌더 결과 계산 (베팅액 절반 손실)

        Returns:
            Tuple[GameOutcome, float]: (SURRENDER, 정산 금액)
        """
        payout = PayoutCalculator.calculate(GameOutcome.SURRENDER, self.bet)
        return GameOutcome.SURRENDER, payout

    def dealer_play(self):
        """딜러 자동 플레이 (17 이상까지)"""
        while calculate_hand_value(self.dealer_hand) < 17:
            card = self.deck.draw()
            self.dealer_hand.append(card)

    def get_result(self) -> tuple:
        """
        게임 결과 계산

        Returns:
            tuple: (outcome, payout)
        """
        player_value = calculate_hand_value(self.player_hand)
        dealer_value = calculate_hand_value(self.dealer_hand)
        player_blackjack = is_blackjack(self.player_hand)
        dealer_blackjack = is_blackjack(self.dealer_hand)
        player_bust = is_bust(self.player_hand)
        dealer_bust = is_bust(self.dealer_hand)

        outcome = determine_outcome(
            player_value,
            dealer_value,
            player_blackjack,
            dealer_blackjack,
            player_bust,
            dealer_bust,
        )

        payout = PayoutCalculator.calculate(outcome, self.bet)
        return outcome, payout
