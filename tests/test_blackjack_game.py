"""
JackPy - 블랙잭 게임 로직 테스트
BlackjackGame 클래스 및 게임 유틸리티 함수 테스트
"""

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


class TestBlackjackGame:
    """BlackjackGame 클래스 테스트 (더블 다운 / 서렌더 포함)"""

    def _make_game(self, bet: float = 100.0):
        from bot.utils.blackjack_game import BlackjackGame

        game = BlackjackGame(user_id=1, bet=bet)
        game.deal_initial()
        return game

    def test_deal_initial(self):
        """초기 딜: 플레이어/딜러 각 2장"""
        game = self._make_game()
        assert len(game.player_hand) == 2
        assert len(game.dealer_hand) == 2

    def test_is_first_turn(self):
        """첫 턴 여부는 첫 2장 상태에서만 True"""
        game = self._make_game()
        assert game.is_first_turn is True
        game.player_hit()
        assert game.is_first_turn is False

    def test_player_double(self):
        """더블 다운: 베팅 2배 + 카드 1장 추가"""
        game = self._make_game(bet=100.0)
        game.player_double()
        assert game.bet == 200.0
        assert len(game.player_hand) == 3

    def test_surrender_result(self):
        """서렌더: SURRENDER 결과와 베팅액 절반 손실"""
        game = self._make_game(bet=100.0)
        outcome, payout = game.surrender_result()
        assert outcome == GameOutcome.SURRENDER
        assert payout == -50.0

    def test_dealer_play_reaches_17(self):
        """딜러는 17 이상까지 히트"""
        game = self._make_game()
        game.dealer_play()
        assert calculate_hand_value(game.dealer_hand) >= 17

    def test_get_result_returns_outcome_and_payout(self):
        """결과 계산은 (outcome, payout) 튜플 반환"""
        game = self._make_game()
        game.dealer_play()
        outcome, payout = game.get_result()
        assert isinstance(outcome, GameOutcome)
        assert isinstance(payout, float)


class TestBlackjackGameSplit:
    """스플릿 기능 테스트"""

    def _make_game(self, hand, bet: float = 100.0):
        from bot.utils.blackjack_game import BlackjackGame

        game = BlackjackGame(user_id=1, bet=bet)
        game.deal_initial()
        game.hands[0] = list(hand)  # 테스트용 핸드 강제 설정
        return game

    def test_can_split_same_rank(self):
        """같은 랭크 2장이면 스플릿 가능"""
        game = self._make_game(["8S", "8H"])
        assert game.can_split is True

    def test_cannot_split_different_rank(self):
        """다른 랭크면 스플릿 불가 (같은 값이어도 랭크가 다르면 불가)"""
        game = self._make_game(["8S", "9H"])
        assert game.can_split is False
        game = self._make_game(["10S", "KH"])  # 둘 다 10점이지만 랭크 다름
        assert game.can_split is False

    def test_cannot_split_after_hit(self):
        """카드를 받은 후에는 스플릿 불가"""
        game = self._make_game(["8S", "8H"])
        game.player_hit()
        assert game.can_split is False

    def test_split_creates_two_hands(self):
        """스플릿 시 두 핸드로 분리, 각 핸드 2장 + 동일 베팅"""
        game = self._make_game(["8S", "8H"], bet=100.0)
        game.split()
        assert game.hand_count == 2
        assert game.hands[0][0] == "8S"
        assert game.hands[1][0] == "8H"
        assert len(game.hands[0]) == 2
        assert len(game.hands[1]) == 2
        assert game.bets == [100.0, 100.0]
        assert game.total_bet == 200.0
        assert game.is_split is True
        assert game.split_rank == "8"

    def test_no_resplit(self):
        """스플릿 후 재스플릿 불가"""
        game = self._make_game(["8S", "8H"])
        game.split()
        assert game.can_split is False
        assert game.is_first_turn is False  # 더블/서렌더도 불가

    def test_advance_hand(self):
        """핸드 진행: 1번 → 2번 → 종료"""
        game = self._make_game(["8S", "8H"])
        game.split()
        assert game.hand_number == 1
        assert game.advance_hand() is True
        assert game.hand_number == 2
        assert game.advance_hand() is False

    def test_active_hand_bet_setter(self):
        """활성 핸드의 bet만 변경되는지 (스플릿 후 더블 방지 확인용)"""
        game = self._make_game(["8S", "8H"], bet=100.0)
        game.split()
        game.advance_hand()
        game.bet = 300.0
        assert game.bets == [100.0, 300.0]

    def test_split_21_is_not_blackjack(self):
        """스플릿 후 두 장 21은 블랙잭이 아닌 일반 승/패로 판정"""
        game = self._make_game(["AS", "AH"])
        game.split()
        # 핸드를 A+K(21)로 강제, 딜러는 20으로 강제
        game.hands[0] = ["AS", "KD"]
        game.hands[1] = ["AH", "KC"]
        game.dealer_hand = ["10S", "QH"]
        results = game.get_results()
        assert all(outcome == GameOutcome.WIN for outcome, _ in results)
        # 블랙잭 배당(1.5배)이 아닌 일반 배당(1배)
        assert all(payout == 100.0 for _, payout in results)

    def test_get_results_per_hand(self):
        """핸드별로 독립 판정 (한 핸드 승, 한 핸드 패)"""
        game = self._make_game(["8S", "8H"])
        game.split()
        game.hands[0] = ["8S", "KD"]  # 18
        game.hands[1] = ["8H", "5C"]  # 13
        game.dealer_hand = ["10S", "7H"]  # 17
        results = game.get_results()
        assert results[0][0] == GameOutcome.WIN
        assert results[1][0] == GameOutcome.LOSS

    def test_any_hand_alive(self):
        """버스트 여부에 따른 생존 핸드 확인"""
        game = self._make_game(["8S", "8H"])
        game.split()
        game.hands[0] = ["8S", "KD", "9C"]  # 27 버스트
        game.hands[1] = ["8H", "5C"]
        assert game.any_hand_alive() is True
        game.hands[1] = ["8H", "KC", "9D"]  # 27 버스트
        assert game.any_hand_alive() is False


class TestInsurance:
    """인슈어런스 테스트"""

    def _make_game(self, dealer_hand, bet: float = 100.0):
        from bot.utils.blackjack_game import BlackjackGame

        game = BlackjackGame(user_id=1, bet=bet)
        game.deal_initial()
        game.hands[0] = ["8S", "7H"]  # 블랙잭 아닌 첫 두 장
        game.dealer_hand = list(dealer_hand)
        return game

    def test_dealer_upcard_is_second_card(self):
        """업카드는 딜러의 두 번째 카드 (첫 카드는 뒷면)"""
        game = self._make_game(["KS", "AH"])
        assert game.dealer_upcard == "AH"

    def test_can_insure_when_upcard_ace(self):
        """딜러 업카드 A면 인슈어런스 가능"""
        game = self._make_game(["KS", "AH"])
        assert game.can_insure is True

    def test_cannot_insure_when_upcard_not_ace(self):
        """딜러 업카드가 A가 아니면 불가 (홀카드 A는 무관)"""
        game = self._make_game(["AS", "KH"])
        assert game.can_insure is False

    def test_cannot_insure_after_hit(self):
        """첫 턴이 지나면 불가"""
        game = self._make_game(["KS", "AH"])
        game.player_hit()
        assert game.can_insure is False

    def test_cannot_insure_twice(self):
        """이미 가입했으면 불가"""
        game = self._make_game(["KS", "AH"])
        game.take_insurance()
        assert game.can_insure is False

    def test_insurance_cost_is_half_bet(self):
        """가입 비용은 베팅액 절반"""
        game = self._make_game(["KS", "AH"], bet=100.0)
        assert game.insurance_cost == 50.0
        assert game.take_insurance() == 50.0

    def test_insurance_net_dealer_blackjack(self):
        """딜러 블랙잭이면 2:1 순수익"""
        game = self._make_game(["KS", "AH"], bet=100.0)
        game.take_insurance()
        assert game.dealer_has_blackjack is True
        assert game.insurance_net == 100.0  # 50 * 2

    def test_insurance_net_no_blackjack(self):
        """딜러 블랙잭이 아니면 가입액 손실"""
        game = self._make_game(["9S", "AH"], bet=100.0)
        game.take_insurance()
        assert game.dealer_has_blackjack is False
        assert game.insurance_net == -50.0

    def test_insurance_net_without_insurance(self):
        """미가입 시 순손익 0"""
        game = self._make_game(["KS", "AH"])
        assert game.insurance_net == 0.0

    def test_insurance_cost_fixed_before_double(self):
        """더블 다운으로 베팅이 늘어도 가입액은 유지"""
        game = self._make_game(["9S", "AH"], bet=100.0)
        game.take_insurance()
        game.player_double()
        assert game.insurance_bet == 50.0

    def test_insurance_serialization_roundtrip(self):
        """to_dict/from_dict에 인슈어런스 상태 유지"""
        from bot.utils.blackjack_game import BlackjackGame

        game = self._make_game(["KS", "AH"], bet=100.0)
        game.take_insurance()
        restored = BlackjackGame.from_dict(game.to_dict())
        assert restored.insurance_bet == 50.0

    def test_serialization_backward_compat(self):
        """insurance_bet 없는 기존 세션 데이터도 복원 가능"""
        from bot.utils.blackjack_game import BlackjackGame

        game = self._make_game(["KS", "AH"])
        data = game.to_dict()
        del data["insurance_bet"]
        restored = BlackjackGame.from_dict(data)
        assert restored.insurance_bet is None
