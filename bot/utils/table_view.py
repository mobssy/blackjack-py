"""
JackPy - 멀티 테이블 메시지 포맷
테이블 상태를 텔레그램 HTML 캡션 문자열과 이미지용 좌석 정보(SeatView)로 변환
(텔레그램/DB 의존성 없음)
"""

from html import escape
from typing import Dict, List, Optional, Tuple

from bot.utils.deck import calculate_hand_value, is_blackjack
from bot.utils.i18n import t
from bot.utils.payouts import OUTCOME_I18N_KEYS, PayoutCalculator
from bot.utils.table import (
    BETTING_SECONDS,
    MAX_SEATS,
    TURN_TIMEOUT_SECONDS,
    BlackjackTable,
    Seat,
    SeatResults,
)
from bot.utils.felt import ACTIVE_COLOR, TONE_COLORS, Tone
from bot.utils.table_renderer import Color, SeatView
from models.round import GameOutcome

# 이미지 좌석 상태 문구 색상 (1인 게임 이미지와 같은 펠트 팔레트)
COLOR_TURN: Color = ACTIVE_COLOR
COLOR_WIN: Color = TONE_COLORS[Tone.WIN]
COLOR_LOSS: Color = TONE_COLORS[Tone.LOSS]
COLOR_NEUTRAL: Color = TONE_COLORS[Tone.PUSH]
COLOR_BLACKJACK: Color = TONE_COLORS[Tone.BLACKJACK]


def mention(seat: Seat) -> str:
    """좌석 플레이어 멘션 (HTML)"""
    return f'<a href="tg://user?id={seat.user_id}">{escape(seat.name)}</a>'


def betting_caption(table: BlackjackTable) -> str:
    """베팅 단계 착석 현황과 참가 방법 (한 메시지로 계속 갱신)"""
    lang = table.lang
    lines = [t("table_betting_title", lang, n=len(table.seats), max=MAX_SEATS)]
    lines += [
        t("table_seat_bet", lang, name=escape(seat.name), bet=seat.game.total_bet)
        for seat in table.seats
    ]
    lines += ["", t("table_betting_hint", lang, minutes=BETTING_SECONDS // 60)]
    return "\n".join(lines)


def turn_caption(table: BlackjackTable, notice: Optional[str] = None) -> str:
    """
    플레이 단계 캡션 — 직전 액션 공지와 현재 차례만 (카드/합계/베팅은 이미지에 표시)
    """
    lang = table.lang
    lines = [notice, ""] if notice else []
    current = table.current_seat
    if current is not None:
        lines.append(
            t(
                "table_turn",
                lang,
                name=mention(current),
                seconds=TURN_TIMEOUT_SECONDS,
            )
        )
    return "\n".join(lines)


def _settle_extra_lines(settle_info: Dict, lang: str) -> List[str]:
    """보험/연승 보너스 부가 정보"""
    lines = []
    if settle_info.get("insurance_bet"):
        insurance_net = settle_info.get("insurance_net", 0.0)
        if insurance_net > 0:
            lines.append(t("insurance_win_line", lang, amount=insurance_net))
        else:
            lines.append(
                t("insurance_lost_line", lang, amount=settle_info["insurance_bet"])
            )
    streak = settle_info.get("streak", 0)
    bonus = settle_info.get("bonus", 0.0)
    if bonus > 0:
        lines.append(t("streak_bonus_line", lang, n=streak, bonus=bonus))
    elif streak >= 2:
        lines.append(t("streak_line", lang, n=streak))
    return lines


def result_text(
    table: BlackjackTable,
    seat_results: SeatResults,
    settle_infos: Dict[int, Dict],
) -> str:
    """
    라운드 결과 메시지 (HTML)

    Args:
        table: 테이블 (딜러 플레이 완료 상태)
        seat_results: 좌석별 핸드 결과
        settle_infos: user_id → 정산 결과 정보
    """
    lang = table.lang
    lines = [result_title(table), ""]
    for seat, results in seat_results:
        settle_info = settle_infos[seat.user_id]
        status, _ = _result_status(results, lang)
        lines.append(
            t(
                "table_result_line",
                lang,
                emoji=_seat_emoji(results),
                name=mention(seat),
                status=status,
                wallet=settle_info["wallet"],
            )
        )
        lines += [f"   {line}" for line in _settle_extra_lines(settle_info, lang)]
    return "\n".join(lines)


def result_title(table: BlackjackTable) -> str:
    """결과 제목 (딜러 최종 합계 포함)"""
    return t(
        "table_result_title",
        table.lang,
        dealer=calculate_hand_value(table.dealer_hand),
    )


def _seat_emoji(results) -> str:
    """좌석 결과 이모지 — 핸드가 하나면 결과별, 스플릿이면 합계 손익 기준"""
    if len(results) == 1:
        return PayoutCalculator.get_result_emoji(results[0][0])
    total = sum(payout for _, payout in results)
    if total > 0:
        return PayoutCalculator.get_result_emoji(GameOutcome.WIN)
    if total < 0:
        return PayoutCalculator.get_result_emoji(GameOutcome.LOSS)
    return PayoutCalculator.get_result_emoji(GameOutcome.PUSH)


# ── 이미지용 좌석 정보 ────────────────────────────────────────


def _playing_status(table: BlackjackTable, seat: Seat) -> Tuple[str, Color]:
    """플레이 중 좌석 상태 문구와 색상"""
    lang = table.lang
    game = seat.game
    if seat is table.current_seat:
        return t("img_status_turn", lang), COLOR_TURN
    if seat.surrendered:
        return t("img_status_surrender", lang), COLOR_NEUTRAL
    if not game.any_hand_alive():
        return t("result_bust", lang), COLOR_LOSS
    if not game.is_split and is_blackjack(game.hands[0]):
        return t("result_blackjack", lang), COLOR_BLACKJACK
    if seat.done:
        return t("img_status_stand", lang), COLOR_NEUTRAL
    return t("img_status_waiting", lang), COLOR_NEUTRAL


def _result_status(results, lang: str) -> Tuple[str, Color]:
    """정산 결과 문구 (핸드별 결과 + 합계 정산액)와 색상"""
    outcomes = " / ".join(
        t(OUTCOME_I18N_KEYS.get(outcome, "result_lose"), lang) for outcome, _ in results
    )
    total = sum(payout for _, payout in results)
    if total > 0:
        color = COLOR_WIN
    elif total < 0:
        color = COLOR_LOSS
    else:
        color = COLOR_NEUTRAL
    return f"{outcomes} {PayoutCalculator.format_payout(total)}", color


def seat_views(
    table: BlackjackTable, seat_results: Optional[SeatResults] = None
) -> List[SeatView]:
    """
    테이블 이미지에 그릴 좌석 정보

    Args:
        table: 테이블
        seat_results: 라운드 결과 (주면 결과 모드, 없으면 플레이 중 모드)
    """
    results_by_user = (
        {seat.user_id: results for seat, results in seat_results}
        if seat_results is not None
        else None
    )
    current = table.current_seat
    views = []
    for seat in table.seats:
        if results_by_user is not None:
            status, color = _result_status(results_by_user[seat.user_id], table.lang)
        else:
            status, color = _playing_status(table, seat)
        views.append(
            SeatView(
                name=seat.name,
                hands=[list(hand) for hand in seat.game.hands],
                bet=seat.game.total_bet,
                active=seat is current and results_by_user is None,
                status=status,
                status_color=color,
            )
        )
    return views
