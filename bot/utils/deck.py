"""
JackPy - 카드 덱 관리
블랙잭 카드 생성 및 계산 로직
"""

import random
from typing import List, Tuple


class Card:
    """
    카드 클래스

    카드 표기: 랭크 + 무늬
    예: AS (Ace of Spades), KH (King of Hearts), 10D (10 of Diamonds)
    """

    SUITS = ["S", "H", "D", "C"]  # Spades, Hearts, Diamonds, Clubs
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

    # 한국어 표시용
    SUIT_NAMES = {"S": "♠️", "H": "♥️", "D": "♦️", "C": "♣️"}

    RANK_NAMES = {"A": "A", "J": "J", "Q": "Q", "K": "K"}

    def __init__(self, card_str: str):
        """
        카드 생성

        Args:
            card_str: 카드 문자열 (예: "AS", "10H")
        """
        self.rank = card_str[:-1]
        self.suit = card_str[-1]

    def __str__(self):
        return f"{self.rank}{self.suit}"

    def __repr__(self):
        return self.__str__()

    @property
    def display(self) -> str:
        """표시용 카드 이름"""
        rank_display = self.RANK_NAMES.get(self.rank, self.rank)
        suit_display = self.SUIT_NAMES.get(self.suit, self.suit)
        return f"{rank_display}{suit_display}"

    @property
    def value(self) -> int:
        """
        카드 값 (Ace는 11로 계산)

        Returns:
            int: 카드 값
        """
        if self.rank in ["J", "Q", "K"]:
            return 10
        elif self.rank == "A":
            return 11
        else:
            return int(self.rank)


class Deck:
    """카드 덱 클래스"""

    def __init__(self, num_decks: int = 1):
        """
        덱 생성

        Args:
            num_decks: 사용할 덱 개수 (기본 1)
        """
        self.cards: List[str] = []
        self.num_decks = num_decks
        self.reset()

    def reset(self):
        """덱 초기화"""
        self.cards = []
        for _ in range(self.num_decks):
            for suit in Card.SUITS:
                for rank in Card.RANKS:
                    self.cards.append(f"{rank}{suit}")
        random.shuffle(self.cards)

    def draw(self) -> str:
        """
        카드 한 장 뽑기

        Returns:
            str: 카드 문자열
        """
        if not self.cards:
            self.reset()
        return self.cards.pop()

    def draw_multiple(self, count: int) -> List[str]:
        """
        여러 장 뽑기

        Args:
            count: 뽑을 카드 수

        Returns:
            List[str]: 카드 리스트
        """
        return [self.draw() for _ in range(count)]


def calculate_hand_value(hand: List[str]) -> int:
    """
    핸드 값 계산 (Soft/Hard 고려)

    Args:
        hand: 카드 리스트

    Returns:
        int: 핸드 값
    """
    cards = [Card(card) for card in hand]
    total = sum(card.value for card in cards)
    aces = sum(1 for card in cards if card.rank == "A")

    # Ace를 1로 계산하여 bust 방지
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


def is_blackjack(hand: List[str]) -> bool:
    """
    블랙잭 여부 확인 (첫 두 카드가 21)

    Args:
        hand: 카드 리스트

    Returns:
        bool: 블랙잭 여부
    """
    return len(hand) == 2 and calculate_hand_value(hand) == 21


def is_bust(hand: List[str]) -> bool:
    """
    버스트 여부 확인 (21 초과)

    Args:
        hand: 카드 리스트

    Returns:
        bool: 버스트 여부
    """
    return calculate_hand_value(hand) > 21


def format_hand(hand: List[str], hide_first: bool = False) -> str:
    """
    핸드 표시용 문자열 생성

    Args:
        hand: 카드 리스트
        hide_first: 첫 카드 숨김 여부

    Returns:
        str: 표시용 문자열
    """
    if hide_first and len(hand) > 0:
        cards = [Card(hand[0])]
        return f"{cards[0].display} 🂠"
    else:
        cards = [Card(card) for card in hand]
        return " ".join(card.display for card in cards)


def get_hand_display(hand: List[str], hide_first: bool = False) -> Tuple[str, int]:
    """
    핸드 표시 문자열과 값 반환

    Args:
        hand: 카드 리스트
        hide_first: 첫 카드 숨김 여부

    Returns:
        Tuple[str, int]: (표시 문자열, 핸드 값)
    """
    hand_str = format_hand(hand, hide_first)
    value = (
        calculate_hand_value(hand)
        if not hide_first
        else calculate_hand_value([hand[0]])
    )
    return hand_str, value
