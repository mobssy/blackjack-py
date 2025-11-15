"""
JackPy - Deck 테스트
카드 덱 및 블랙잭 로직 테스트
"""
import pytest
from bot.utils.deck import (
    Card, Deck, calculate_hand_value, is_blackjack,
    is_bust, format_hand
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
        assert Card("5D").value == 5   # Number
        assert Card("10C").value == 10  # 10

    def test_card_display(self):
        """카드 표시 테스트"""
        card = Card("AS")
        assert "♠" in card.display


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


class TestHandFormatting:
    """핸드 포맷팅 테스트"""

    def test_format_hand(self):
        """핸드 포맷 테스트"""
        hand = ["AS", "KH"]
        formatted = format_hand(hand)
        assert "♠" in formatted
        assert "♥" in formatted

    def test_format_hand_hide_first(self):
        """첫 카드 숨김 테스트"""
        hand = ["AS", "KH"]
        formatted = format_hand(hand, hide_first=True)
        assert "🂠" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
