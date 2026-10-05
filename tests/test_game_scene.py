"""
JackPy - 1인 게임 장면 변환 테스트
BlackjackGame/정산 결과 → GameScene (홀 카드, HIT 연출, 스플릿, 결과 배지)
"""

from bot.utils.blackjack_game import BlackjackGame
from bot.utils.game_renderer import FACE_DOWN, Tone
from bot.utils.game_scene import felt_lines, play_scene, result_scene
from bot.utils.i18n import t
from bot.utils.payouts import PayoutCalculator
from models.round import GameOutcome


def _game(player, dealer, bet=100.0):
    game = BlackjackGame(1, bet)
    game.hands = [list(player)]
    game.dealer_hand = list(dealer)
    return game


def _split_game():
    game = _game(["8S", "3D"], ["10D", "7C"])
    game.hands = [["8S", "3D", "10H"], ["8H", "9C"]]
    game.bets = [100.0, 100.0]
    game.is_split = True
    game.active_index = 1
    return game


_SETTLE = {"wallet": 1200.0, "streak": 0}


class TestFeltLines:
    def test_blackjack_ratio_comes_from_payout_constant(self, monkeypatch):
        assert felt_lines("en")[0] == "BLACKJACK PAYS 6 TO 5"
        monkeypatch.setattr(PayoutCalculator, "BLACKJACK_MULTIPLIER", 1.5)
        assert felt_lines("en")[0] == "BLACKJACK PAYS 3 TO 2"

    def test_dealer_rule_line(self):
        assert felt_lines("ko")[1] == t("img_felt_dealer_rule", "ko")


class TestPlayScene:
    def test_hides_hole_card(self):
        scene = play_scene(_game(["9S", "QH"], ["10D", "7C"]), "ko")
        assert scene.hide_hole
        assert scene.dealer_total is None
        assert scene.result is None

    def test_single_hand(self):
        scene = play_scene(_game(["9S", "QH"], ["10D", "7C"], bet=250.0), "ko")
        (hand,) = scene.hands
        assert hand.cards == ["9S", "QH"]
        assert hand.total == 19
        assert hand.bet == 250.0
        assert not hand.active  # 스플릿이 아니면 강조 없음

    def test_drawing_adds_face_down_card_without_changing_total(self):
        scene = play_scene(_game(["5S", "6H"], ["10D", "7C"]), "ko", drawing=True)
        (hand,) = scene.hands
        assert hand.cards == ["5S", "6H", FACE_DOWN]
        assert hand.total == 11

    def test_split_marks_and_draws_only_active_hand(self):
        scene = play_scene(_split_game(), "ko", drawing=True)
        first, second = scene.hands
        assert not first.active and second.active
        assert FACE_DOWN not in first.cards
        assert second.cards[-1] == FACE_DOWN


class TestResultScene:
    def test_single_hand_badge(self):
        game = _game(["9S", "QH"], ["10D", "7C"])
        scene = result_scene(game, [(GameOutcome.WIN, 100.0)], _SETTLE, "ko")
        assert not scene.hide_hole
        assert scene.dealer_total == 17
        assert scene.result.headline == t("result_win", "ko")
        assert scene.result.amount == "+$100.00"
        assert scene.result.tone is Tone.WIN
        assert scene.hands[0].outcome == ""  # 단일 핸드 결과는 배지에만

    def test_outcome_tones(self):
        game = _game(["9S", "QH"], ["10D", "7C"])
        expected = {
            GameOutcome.BLACKJACK: Tone.BLACKJACK,
            GameOutcome.PUSH: Tone.PUSH,
            GameOutcome.BUST: Tone.LOSS,
            GameOutcome.SURRENDER: Tone.LOSS,
        }
        for outcome, tone in expected.items():
            scene = result_scene(game, [(outcome, 0.0)], _SETTLE, "en")
            assert scene.result.tone is tone, outcome

    def test_details_balance_insurance_streak(self):
        game = _game(["9S", "QH"], ["AS", "KD"])
        settle = {
            "wallet": 1000.0,
            "insurance_bet": 50.0,
            "insurance_net": 100.0,
            "streak": 4,
            "bonus": 0.0,
        }
        scene = result_scene(game, [(GameOutcome.LOSS, -100.0)], settle, "en")
        assert scene.result.details == [
            t("img_balance", "en", amount=1000.0),
            t("insurance_win_line", "en", amount=100.0),
            t("streak_line", "en", n=4),
        ]

    def test_split_badge_is_total_and_hands_get_outcomes(self):
        results = [(GameOutcome.WIN, 100.0), (GameOutcome.LOSS, -100.0)]
        scene = result_scene(_split_game(), results, _SETTLE, "ko")
        assert scene.result.headline == t("img_split_total", "ko")
        assert scene.result.amount == PayoutCalculator.format_payout(0)
        assert scene.result.tone is Tone.PUSH
        first, second = scene.hands
        assert first.tone is Tone.WIN and second.tone is Tone.LOSS
        assert "+$100.00" in first.outcome and "-$100.00" in second.outcome
        assert not first.active and not second.active
