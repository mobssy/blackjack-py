"""
JackPy - 블랙잭 게임 로직 테스트
BlackjackGame 클래스 및 게임 유틸리티 함수 테스트
"""

import pytest
from bot.utils.deck import (
    Card,
    Deck,
    calculate_hand_value,
    is_blackjack,
    is_bust,
    format_hand,
    get_hand_display,
)
from bot.utils.payouts import PayoutCalculator, determine_outcome
from models.round import GameOutcome


class TestCard:
    """Card 클래스 테스트"""

    def test_card_creation(self):
        """카드 생성"""
        card = Card("AS")
        assert card.rank == "A"
        assert card.suit == "S"

    def test_card_value_number(self):
        """숫자 카드 값"""
        card = Card("7H")
        assert card.value == 7

    def test_card_value_face(self):
        """그림 카드 값"""
        assert Card("JD").value == 10
        assert Card("QC").value == 10
        assert Card("KH").value == 10

    def test_card_value_ace(self):
        """에이스 값 (11)"""
        card = Card("AS")
        assert card.value == 11

    def test_card_display(self):
        """카드 표시"""
        card = Card("AS")
        assert "A" in card.display
        assert "♠️" in card.display


class TestDeck:
    """Deck 클래스 테스트"""

    def test_deck_creation_single(self):
        """단일 덱 생성"""
        deck = Deck(num_decks=1)
        assert len(deck.cards) == 52

    def test_deck_creation_multiple(self):
        """멀티 덱 생성"""
        deck = Deck(num_decks=6)
        assert len(deck.cards) == 52 * 6

    def test_draw_card(self):
        """카드 뽑기"""
        deck = Deck(num_decks=1)
        initial_count = len(deck.cards)
        card = deck.draw()
        assert isinstance(card, str)
        assert len(deck.cards) == initial_count - 1

    def test_draw_multiple(self):
        """여러 카드 뽑기"""
        deck = Deck(num_decks=1)
        cards = deck.draw_multiple(5)
        assert len(cards) == 5
        assert len(deck.cards) == 52 - 5

    def test_reset_when_empty(self):
        """덱이 비면 자동 리셋"""
        deck = Deck(num_decks=1)
        # 모든 카드 뽑기
        for _ in range(52):
            deck.draw()
        assert len(deck.cards) == 0

        # 다음 뽑기에서 자동 리셋
        card = deck.draw()
        assert isinstance(card, str)


class TestHandValue:
    """핸드 값 계산 테스트"""

    def test_simple_hand(self):
        """일반 핸드"""
        hand = ["7H", "9D"]
        assert calculate_hand_value(hand) == 16

    def test_hand_with_face_cards(self):
        """그림 카드 포함"""
        hand = ["KH", "QD"]
        assert calculate_hand_value(hand) == 20

    def test_hand_with_ace_as_eleven(self):
        """에이스가 11로 계산되는 경우"""
        hand = ["AS", "9H"]
        assert calculate_hand_value(hand) == 20

    def test_hand_with_ace_as_one(self):
        """에이스가 1로 계산되는 경우 (버스트 방지)"""
        hand = ["AS", "KH", "9D"]  # 11 + 10 + 9 = 30 -> 1 + 10 + 9 = 20
        assert calculate_hand_value(hand) == 20

    def test_multiple_aces(self):
        """여러 에이스"""
        hand = ["AS", "AH", "9D"]  # 11 + 11 + 9 = 31 -> 11 + 1 + 9 = 21
        assert calculate_hand_value(hand) == 21

    def test_blackjack_hand(self):
        """블랙잭 핸드"""
        hand = ["AS", "KH"]
        assert calculate_hand_value(hand) == 21


class TestBlackjack:
    """블랙잭 판정 테스트"""

    def test_blackjack_true(self):
        """블랙잭 O"""
        assert is_blackjack(["AS", "KH"]) is True
        assert is_blackjack(["10D", "AC"]) is True

    def test_blackjack_false_not_21(self):
        """21이 아님"""
        assert is_blackjack(["9H", "10D"]) is False

    def test_blackjack_false_three_cards(self):
        """3장으로 21 (블랙잭 X)"""
        assert is_blackjack(["7H", "7D", "7C"]) is False

    def test_blackjack_false_empty(self):
        """빈 핸드"""
        assert is_blackjack([]) is False


class TestBust:
    """버스트 판정 테스트"""

    def test_bust_true(self):
        """버스트 O"""
        assert is_bust(["KH", "QD", "5C"]) is True  # 25

    def test_bust_false(self):
        """버스트 X"""
        assert is_bust(["KH", "QD"]) is False  # 20
        assert is_bust(["AS", "KH"]) is False  # 21

    def test_bust_with_ace_adjustment(self):
        """에이스 조정으로 버스트 회피"""
        assert is_bust(["AS", "5H", "5D"]) is False  # 1 + 5 + 5 = 11


class TestPayoutCalculator:
    """정산 계산 테스트"""

    def test_blackjack_payout(self):
        """블랙잭 정산 (3:2)"""
        payout = PayoutCalculator.calculate(GameOutcome.BLACKJACK, 100.0)
        assert payout == 150.0

    def test_win_payout(self):
        """일반 승리 정산 (1:1)"""
        payout = PayoutCalculator.calculate(GameOutcome.WIN, 100.0)
        assert payout == 100.0

    def test_push_payout(self):
        """무승부 정산 (0)"""
        payout = PayoutCalculator.calculate(GameOutcome.PUSH, 100.0)
        assert payout == 0.0

    def test_loss_payout(self):
        """패배 정산 (-1)"""
        payout = PayoutCalculator.calculate(GameOutcome.LOSS, 100.0)
        assert payout == -100.0

    def test_bust_payout(self):
        """버스트 정산 (-1)"""
        payout = PayoutCalculator.calculate(GameOutcome.BUST, 100.0)
        assert payout == -100.0

    def test_format_payout_positive(self):
        """양수 정산 포맷"""
        assert PayoutCalculator.format_payout(150.0) == "+$150.00"

    def test_format_payout_negative(self):
        """음수 정산 포맷"""
        assert PayoutCalculator.format_payout(-100.0) == "-$100.00"

    def test_format_payout_zero(self):
        """0 정산 포맷"""
        assert PayoutCalculator.format_payout(0.0) == "$0.00"

    def test_outcome_message(self):
        """결과 메시지"""
        assert "블랙잭" in PayoutCalculator.get_outcome_message(GameOutcome.BLACKJACK)
        assert "승리" in PayoutCalculator.get_outcome_message(GameOutcome.WIN)
        assert "무승부" in PayoutCalculator.get_outcome_message(GameOutcome.PUSH)

    def test_result_emoji(self):
        """결과 이모지"""
        assert PayoutCalculator.get_result_emoji(GameOutcome.BLACKJACK) == "🎉"
        assert PayoutCalculator.get_result_emoji(GameOutcome.WIN) == "✅"
        assert PayoutCalculator.get_result_emoji(GameOutcome.BUST) == "💥"


class TestDetermineOutcome:
    """게임 결과 판정 테스트"""

    def test_player_bust(self):
        """플레이어 버스트"""
        outcome = determine_outcome(
            player_value=25,
            dealer_value=18,
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
        """양쪽 블랙잭 (무승부)"""
        outcome = determine_outcome(
            player_value=21,
            dealer_value=21,
            player_blackjack=True,
            dealer_blackjack=True,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.PUSH

    def test_player_blackjack_only(self):
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

    def test_dealer_blackjack_only(self):
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

    def test_player_higher_value(self):
        """플레이어가 높은 값"""
        outcome = determine_outcome(
            player_value=20,
            dealer_value=18,
            player_blackjack=False,
            dealer_blackjack=False,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.WIN

    def test_dealer_higher_value(self):
        """딜러가 높은 값"""
        outcome = determine_outcome(
            player_value=18,
            dealer_value=20,
            player_blackjack=False,
            dealer_blackjack=False,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.LOSS

    def test_same_value(self):
        """같은 값 (무승부)"""
        outcome = determine_outcome(
            player_value=19,
            dealer_value=19,
            player_blackjack=False,
            dealer_blackjack=False,
            player_bust=False,
            dealer_bust=False,
        )
        assert outcome == GameOutcome.PUSH


class TestHandDisplay:
    """핸드 표시 테스트"""

    def test_format_hand_normal(self):
        """일반 핸드 표시"""
        hand = ["AS", "KH"]
        formatted = format_hand(hand)
        assert "A" in formatted
        assert "K" in formatted

    def test_format_hand_hide_first(self):
        """첫 카드 숨김"""
        hand = ["AS", "KH"]
        formatted = format_hand(hand, hide_first=True)
        assert "🂠" in formatted  # 숨겨진 카드

    def test_get_hand_display_normal(self):
        """핸드 표시와 값"""
        hand = ["AS", "KH"]
        display, value = get_hand_display(hand)
        assert isinstance(display, str)
        assert value == 21

    def test_get_hand_display_hide_first(self):
        """첫 카드 숨김 시 표시와 값"""
        hand = ["AS", "KH"]
        display, value = get_hand_display(hand, hide_first=True)
        assert "🂠" in display
        # 첫 카드만 계산 (AS = 11)
        assert value == 11
