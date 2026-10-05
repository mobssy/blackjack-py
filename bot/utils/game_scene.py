"""
JackPy - 1인 게임 이미지용 장면 변환
BlackjackGame과 정산 결과를 FeltGameRenderer가 그릴 GameScene으로 바꾼다
(텔레그램/DB 의존성 없음 — 멀티 테이블의 table_view.py와 같은 역할)
"""

from fractions import Fraction
from typing import Dict, List, Tuple

from bot.utils.blackjack_game import BlackjackGame
from bot.utils.deck import calculate_hand_value
from bot.utils.game_renderer import (
    FACE_DOWN,
    GameScene,
    HandScene,
    ResultBanner,
    Tone,
)
from bot.utils.i18n import t
from bot.utils.payouts import OUTCOME_I18N_KEYS, PayoutCalculator
from models.round import GameOutcome

Results = List[Tuple[GameOutcome, float]]

_OUTCOME_TONES = {
    GameOutcome.BLACKJACK: Tone.BLACKJACK,
    GameOutcome.WIN: Tone.WIN,
    GameOutcome.PUSH: Tone.PUSH,
    GameOutcome.LOSS: Tone.LOSS,
    GameOutcome.BUST: Tone.LOSS,
    GameOutcome.SURRENDER: Tone.LOSS,
}


def _outcome_text(outcome: GameOutcome, lang: str) -> str:
    return t(OUTCOME_I18N_KEYS.get(outcome, "result_lose"), lang)


def _tone_of_total(total: float) -> Tone:
    if total > 0:
        return Tone.WIN
    if total < 0:
        return Tone.LOSS
    return Tone.PUSH


def felt_lines(lang: str) -> Tuple[str, ...]:
    """펠트 규칙 문구 — 블랙잭 배당은 실제 배당 상수에서 계산 (6:5 등)"""
    ratio = Fraction(PayoutCalculator.BLACKJACK_MULTIPLIER).limit_denominator(10)
    return (
        t("img_felt_blackjack", lang, num=ratio.numerator, den=ratio.denominator),
        t("img_felt_dealer_rule", lang),
    )


def play_scene(game: BlackjackGame, lang: str, drawing: bool = False) -> GameScene:
    """
    진행 중 장면 (딜러 홀 카드 가림)

    Args:
        drawing: HIT 연출 — 지금 핸드에 받을 카드를 뒷면으로 한 장 더 그림
    """
    hands = []
    for i, (hand, bet) in enumerate(zip(game.hands, game.bets)):
        current = i == game.active_index
        cards = list(hand) + ([FACE_DOWN] if drawing and current else [])
        hands.append(
            HandScene(
                cards=cards,
                total=calculate_hand_value(hand),
                bet=bet,
                active=game.is_split and current,
            )
        )
    return GameScene(
        dealer=list(game.dealer_hand),
        dealer_total=None,
        hands=hands,
        felt_lines=felt_lines(lang),
        bet_label=t("img_bet", lang),
    )


def result_scene(
    game: BlackjackGame, results: Results, settle_info: Dict, lang: str
) -> GameScene:
    """
    결과 장면 — 딜러 공개, 결과 배지, 잔액·보험·연승 정보

    스플릿이면 배지는 합계 손익, 핸드별 결과는 각 핸드 아래에 표시한다.
    """
    split = len(results) > 1
    hands = []
    for i, ((outcome, payout), hand, bet) in enumerate(
        zip(results, game.hands, game.bets), 1
    ):
        outcome_line = ""
        if split:
            outcome_line = t(
                "img_hand_outcome",
                lang,
                n=i,
                outcome=_outcome_text(outcome, lang),
                payout=PayoutCalculator.format_payout(payout),
            )
        hands.append(
            HandScene(
                cards=list(hand),
                total=calculate_hand_value(hand),
                bet=bet,
                outcome=outcome_line,
                tone=_OUTCOME_TONES.get(outcome) if split else None,
            )
        )

    total = sum(payout for _, payout in results)
    if split:
        headline, tone = t("img_split_total", lang), _tone_of_total(total)
    else:
        outcome = results[0][0]
        headline, tone = _outcome_text(outcome, lang), _OUTCOME_TONES[outcome]

    return GameScene(
        dealer=list(game.dealer_hand),
        dealer_total=calculate_hand_value(game.dealer_hand),
        hands=hands,
        felt_lines=felt_lines(lang),
        bet_label=t("img_bet", lang),
        result=ResultBanner(
            headline=headline,
            amount=PayoutCalculator.format_payout(total),
            tone=tone,
            details=_result_details(settle_info, lang),
        ),
    )


def _result_details(settle_info: Dict, lang: str) -> List[str]:
    """배지 아래 정보 — 잔액, 보험 결과, 연승"""
    details = [t("img_balance", lang, amount=settle_info["wallet"])]
    insurance_bet = settle_info.get("insurance_bet")
    if insurance_bet:
        insurance_net = settle_info.get("insurance_net", 0.0)
        if insurance_net > 0:
            details.append(t("insurance_win_line", lang, amount=insurance_net))
        else:
            details.append(t("insurance_lost_line", lang, amount=insurance_bet))
    streak = settle_info.get("streak", 0)
    bonus = settle_info.get("bonus", 0.0)
    if bonus > 0:
        details.append(t("streak_bonus_line", lang, n=streak, bonus=bonus))
    elif streak >= 2:
        details.append(t("streak_line", lang, n=streak))
    return details
