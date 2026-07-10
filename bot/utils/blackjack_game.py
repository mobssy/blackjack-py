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
        # 인슈어런스 (딜러 업카드 A일 때 베팅액 절반)
        self.insurance_bet: Optional[float] = None

    # ── 직렬화 (세션 영속화용) ──────────────────────────────────

    def to_dict(self) -> dict:
        """JSON 저장 가능한 상태 dict로 변환"""
        return {
            "user_id": self.user_id,
            "hands": self.hands,
            "bets": self.bets,
            "active_index": self.active_index,
            "is_split": self.is_split,
            "split_rank": self.split_rank,
            "dealer_hand": self.dealer_hand,
            "deck_cards": self.deck.cards,
            "insurance_bet": self.insurance_bet,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BlackjackGame":
        """to_dict()로 저장된 상태에서 게임 복원"""
        game = cls(user_id=data["user_id"], bet=0.0)
        game.hands = [list(hand) for hand in data["hands"]]
        game.bets = [float(bet) for bet in data["bets"]]
        game.active_index = int(data["active_index"])
        game.is_split = bool(data["is_split"])
        game.split_rank = data.get("split_rank")
        game.dealer_hand = list(data["dealer_hand"])
        game.deck.cards = list(data["deck_cards"])
        insurance_bet = data.get("insurance_bet")
        game.insurance_bet = float(insurance_bet) if insurance_bet is not None else None
        return game

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

    # ── 인슈어런스 ─────────────────────────────────────────────

    @property
    def dealer_upcard(self) -> Optional[str]:
        """딜러 공개 카드 (첫 카드는 뒷면이므로 두 번째 카드)"""
        if len(self.dealer_hand) < 2:
            return None
        return self.dealer_hand[1]

    @property
    def can_insure(self) -> bool:
        """인슈어런스 가능 여부 (첫 턴 + 딜러 업카드 A + 미가입)"""
        if not self.is_first_turn or self.insurance_bet is not None:
            return False
        upcard = self.dealer_upcard
        return upcard is not None and Card(upcard).rank == "A"

    @property
    def insurance_cost(self) -> float:
        """인슈어런스 가입 비용 (베팅액 절반)"""
        return self.bets[0] / 2

    def take_insurance(self) -> float:
        """
        인슈어런스 가입 (베팅액 절반)

        호출 전에 can_insure와 잔액 확인 필요

        Returns:
            float: 가입 금액
        """
        self.insurance_bet = self.insurance_cost
        return self.insurance_bet

    @property
    def dealer_has_blackjack(self) -> bool:
        """딜러 블랙잭 여부"""
        return is_blackjack(self.dealer_hand)

    @property
    def insurance_net(self) -> float:
        """
        인슈어런스 순손익 (2:1 배당)

        딜러 블랙잭이면 +2배, 아니면 가입액 손실. 미가입 시 0.
        """
        if self.insurance_bet is None:
            return 0.0
        if self.dealer_has_blackjack:
            return self.insurance_bet * 2
        return -self.insurance_bet

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
