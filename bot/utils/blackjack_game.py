"""
JackPy - 블랙잭 게임 로직
텔레그램 의존성 없는 순수 게임 상태/규칙 클래스
"""

from typing import List, Optional, Tuple

from bot.utils.deck import (
    Card,
    Deck,
    calculate_hand_value,
    is_blackjack,
    is_bust,
)
from bot.utils.payouts import PayoutCalculator, determine_outcome
from models.round import GameOutcome


class BlackjackGame:
    """
    블랙잭 게임 로직 클래스

    스플릿 시 핸드가 여러 개가 되며, player_hand/bet은 항상
    현재 플레이 중인(활성) 핸드를 가리킨다.
    """

    def __init__(self, user_id: int, bet: float):
        """
        게임 초기화

        Args:
            user_id: 사용자 ID
            bet: 베팅 금액
        """
        self.user_id = user_id
        self.deck = Deck(num_decks=6)  # 6덱 사용
        self.hands: List[List[str]] = [[]]
        self.bets: List[float] = [bet]
        self.active_index = 0
        self.is_split = False
        self.split_rank: Optional[str] = None
        self.dealer_hand: List[str] = []
        self.is_finished = False

    # ── 활성 핸드 접근자 ────────────────────────────────────────

    @property
    def player_hand(self) -> List[str]:
        """현재 플레이 중인 핸드"""
        return self.hands[self.active_index]

    @property
    def bet(self) -> float:
        """현재 플레이 중인 핸드의 베팅 금액"""
        return self.bets[self.active_index]

    @bet.setter
    def bet(self, value: float) -> None:
        self.bets[self.active_index] = value

    @property
    def total_bet(self) -> float:
        """전체 핸드 베팅 합계"""
        return sum(self.bets)

    @property
    def hand_count(self) -> int:
        """핸드 개수"""
        return len(self.hands)

    @property
    def hand_number(self) -> int:
        """현재 핸드 번호 (1부터)"""
        return self.active_index + 1

    # ── 상태 판정 ──────────────────────────────────────────────

    @property
    def is_first_turn(self) -> bool:
        """첫 턴(스플릿 전, 첫 2장 상태) 여부 — 더블/서렌더/스플릿 가능 조건"""
        return not self.is_split and len(self.hands[0]) == 2

    @property
    def can_split(self) -> bool:
        """스플릿 가능 여부 (첫 턴 + 같은 랭크 2장, 재스플릿 불가)"""
        if not self.is_first_turn:
            return False
        first, second = self.hands[0]
        return Card(first).rank == Card(second).rank

    def any_hand_alive(self) -> bool:
        """버스트되지 않은 핸드가 하나라도 있는지"""
        return any(not is_bust(hand) for hand in self.hands)

    # ── 플레이 액션 ────────────────────────────────────────────

    def deal_initial(self):
        """초기 카드 2장씩 딜"""
        self.hands[0] = self.deck.draw_multiple(2)
        self.dealer_hand = self.deck.draw_multiple(2)

    def player_hit(self):
        """플레이어 히트 (활성 핸드에 카드 추가)"""
        card = self.deck.draw()
        self.player_hand.append(card)

    def player_double(self):
        """
        더블 다운: 베팅 2배 후 카드 1장만 추가

        호출 전에 첫 턴 여부와 추가 베팅 잔액 확인 필요
        """
        self.bet *= 2
        self.player_hit()

    def split(self):
        """
        스플릿: 같은 랭크 2장을 두 핸드로 분리, 각 핸드에 카드 1장씩 추가

        호출 전에 can_split과 추가 베팅 잔액 확인 필요
        """
        first, second = self.hands[0]
        self.split_rank = Card(first).rank
        self.hands = [
            [first, self.deck.draw()],
            [second, self.deck.draw()],
        ]
        self.bets = [self.bets[0], self.bets[0]]
        self.active_index = 0
        self.is_split = True

    def advance_hand(self) -> bool:
        """
        다음 핸드로 진행

        Returns:
            bool: 다음 핸드가 있어 이동했으면 True, 모든 핸드 완료면 False
        """
        if self.active_index + 1 < len(self.hands):
            self.active_index += 1
            return True
        return False

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

    # ── 결과 계산 ──────────────────────────────────────────────

    def get_results(self) -> List[Tuple[GameOutcome, float]]:
        """
        모든 핸드의 게임 결과 계산

        스플릿 후 두 장 21은 블랙잭이 아닌 일반 21로 취급한다.

        Returns:
            List[Tuple[GameOutcome, float]]: 핸드별 (outcome, payout)
        """
        dealer_value = calculate_hand_value(self.dealer_hand)
        dealer_blackjack = is_blackjack(self.dealer_hand)
        dealer_bust = is_bust(self.dealer_hand)

        results = []
        for hand, bet in zip(self.hands, self.bets):
            player_blackjack = is_blackjack(hand) and not self.is_split
            outcome = determine_outcome(
                calculate_hand_value(hand),
                dealer_value,
                player_blackjack,
                dealer_blackjack,
                is_bust(hand),
                dealer_bust,
            )
            results.append((outcome, PayoutCalculator.calculate(outcome, bet)))
        return results

    def get_result(self) -> Tuple[GameOutcome, float]:
        """
        단일 핸드 게임 결과 (하위 호환용)

        Returns:
            Tuple[GameOutcome, float]: (outcome, payout)
        """
        return self.get_results()[0]
