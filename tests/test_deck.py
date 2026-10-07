"""
JackPy - Deck 테스트
카드 덱 및 블랙잭 로직 테스트
"""

import pytest
from bot.utils.deck import (
    Card,
    Deck,
    calculate_hand_value,
    dealer_should_hit,
    is_blackjack,
    is_soft,
    is_bust,
)


class TestCard:
    """Card 클래스 테스트"""

    def test_card_creation(self):
        """카드 생성 테스트"""
        card = Card("AS")
        assert card.rank == "A"
        assert card.suit == "S"

    def test_card_value(self):
        """카드 값 테스트"""
        assert Card("AS").value == 11  # Ace
        assert Card("KH").value == 10  # King
        assert Card("5D").value == 5  # Number
        assert Card("10C").value == 10  # 10


class TestDeck:
    """Deck 클래스 테스트"""

    def test_deck_creation(self):
        """덱 생성 테스트"""
        deck = Deck()
        assert len(deck.cards) == 52

    def test_multiple_decks(self):
        """멀티덱 테스트"""
        deck = Deck(num_decks=2)
        assert len(deck.cards) == 104

    def test_draw_card(self):
        """카드 뽑기 테스트"""
        deck = Deck()
        card = deck.draw()
        assert isinstance(card, str)
        assert len(deck.cards) == 51


class TestHandCalculation:
    """핸드 계산 테스트"""

    def test_simple_hand(self):
        """간단한 핸드 테스트"""
        hand = ["5H", "7D"]
        assert calculate_hand_value(hand) == 12

    def test_blackjack(self):
        """블랙잭 테스트"""
        hand = ["AS", "KH"]
        assert calculate_hand_value(hand) == 21
        assert is_blackjack(hand) is True

    def test_soft_ace(self):
        """소프트 에이스 테스트"""
        hand = ["AS", "5H", "7D"]  # A + 5 + 7 = 13 (A를 1로 계산)
        assert calculate_hand_value(hand) == 13

    def test_bust(self):
        """버스트 테스트"""
        hand = ["KH", "QD", "5C"]  # 10 + 10 + 5 = 25
        assert calculate_hand_value(hand) == 25
        assert is_bust(hand) is True

    def test_not_blackjack_with_21(self):
        """21이지만 블랙잭이 아닌 경우"""
        hand = ["5H", "6D", "KS"]  # 5 + 6 + 10 = 21 (3장)
        assert calculate_hand_value(hand) == 21
        assert is_blackjack(hand) is False


class TestDealerRule:
    """딜러 규칙 (H17: 17 미만·소프트 17 히트)"""

    @pytest.mark.parametrize(
        "hand, soft",
        [
            (["AS", "6H"], True),  # 소프트 17
            (["AS", "5H", "7D"], False),  # A를 1로 계산 → 하드 13
            (["10S", "7H"], False),
            (["AS", "AH", "5D"], True),  # A 하나만 11 → 소프트 17
        ],
    )
    def test_is_soft(self, hand, soft):
        assert is_soft(hand) is soft

    @pytest.mark.parametrize(
        "hand, hit",
        [
            (["10S", "6H"], True),  # 16
            (["AS", "6H"], True),  # 소프트 17 → 히트
            (["10S", "7H"], False),  # 하드 17 → 스탠드
            (["AS", "7H"], False),  # 소프트 18 → 스탠드
            (["AS", "6H", "10D"], False),  # 하드 17 (A=1) → 스탠드
        ],
    )
    def test_dealer_should_hit(self, hand, hit):
        assert dealer_should_hit(hand) is hit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
