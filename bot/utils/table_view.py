"""
JackPy - 멀티 테이블 메시지 포맷
테이블 상태를 텔레그램 HTML 캡션 문자열로 변환 (텔레그램/DB 의존성 없음)
"""

from html import escape
from typing import Dict, List, Optional

from bot.utils.deck import Card, calculate_hand_value, format_hand
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


def mention(seat: Seat) -> str:
    """좌석 플레이어 멘션 (HTML)"""
    return f'<a href="tg://user?id={seat.user_id}">{escape(seat.name)}</a>'


def hand_text(hand: List[str]) -> str:
    """핸드 카드와 합계 (예: 8♠️ 8♥️ (16))"""
    return f"{format_hand(hand)} ({calculate_hand_value(hand)})"


def seat_hands_text(seat: Seat) -> str:
    """좌석의 모든 핸드 (스플릿이면 | 로 구분)"""
    return " | ".join(hand_text(hand) for hand in seat.game.hands)


def _hidden_dealer_text(dealer_hand: List[str]) -> str:
    """홀 카드(첫 장)를 가린 딜러 핸드"""
    shown = " ".join(Card(card).display for card in dealer_hand[1:])
    return f"🂠 {shown}"


def betting_caption(table: BlackjackTable) -> str:
    """베팅 단계 안내 및 착석 현황"""
    lang = table.lang
    lines = [
        t("table_opened", lang, max=MAX_SEATS, seconds=BETTING_SECONDS),
        "",
        t("table_seats_header", lang, n=len(table.seats), max=MAX_SEATS),
    ]
    lines += [
        t("table_seat_bet", lang, name=escape(seat.name), bet=seat.game.total_bet)
        for seat in table.seats
    ]
    return "\n".join(lines)


def _seat_marker(table: BlackjackTable, seat: Seat) -> str:
    if seat.surrendered:
        return "🏳️"
    if seat is table.current_seat:
        return "▶"
    return "✔" if seat.done else "·"


def turn_caption(table: BlackjackTable, notice: Optional[str] = None) -> str:
    """플레이 단계 캡션 — 딜러 업카드, 좌석별 핸드, 현재 차례 안내"""
    lang = table.lang
    lines = [notice, ""] if notice else []
    lines += [
        t("table_playing_title", lang, n=len(table.seats), max=MAX_SEATS),
        t(
            "table_dealer_line",
            lang,
            cards=_hidden_dealer_text(table.dealer_hand),
        ),
    ]
    for seat in table.seats:
        lines.append(
            f"{_seat_marker(table, seat)} {escape(seat.name)}: "
            f"{seat_hands_text(seat)} · ${seat.game.total_bet:,.2f}"
        )

    current = table.current_seat
    if current is not None:
        lines += [
            "",
            t(
                "table_turn",
                lang,
                name=mention(current),
                seconds=TURN_TIMEOUT_SECONDS,
            ),
        ]
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
    lines = [
        t("table_result_title", lang),
        t("table_dealer_line", lang, cards=hand_text(table.dealer_hand)),
    ]
    for seat, results in seat_results:
        lines += ["", f"👤 {mention(seat)}"]
        for (outcome, payout), hand in zip(results, seat.game.hands):
            emoji = PayoutCalculator.get_result_emoji(outcome)
            outcome_msg = t(OUTCOME_I18N_KEYS.get(outcome, "result_lose"), lang)
            lines.append(
                f"   {emoji} {hand_text(hand)} — {outcome_msg} "
                f"({PayoutCalculator.format_payout(payout)})"
            )
        settle_info = settle_infos[seat.user_id]
        lines += [f"   {line}" for line in _settle_extra_lines(settle_info, lang)]
        lines.append(f"   {t('balance_label', lang)}: ${settle_info['wallet']:,.2f}")
    lines += ["", t("table_result_footer", lang)]
    return "\n".join(lines)
