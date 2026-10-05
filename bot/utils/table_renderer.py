"""
JackPy - 멀티 테이블 이미지 렌더러 (펠트 테이블)
딜러와 최대 7개 좌석을 한 장에 그린다. 1인 게임 이미지와 같은 펠트·칩·팔레트
(felt.py)를 쓰고, 카드는 CasinoCardRenderer, 글자는 Pretendard(fonts.py)를 쓴다.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from bot.utils.casino_card_renderer import CasinoCardRenderer, get_casino_renderer
from bot.utils.deck import calculate_hand_value
from bot.utils.felt import (
    CHIP_BLACK,
    CHIP_RED,
    CREAM,
    FELT_INK,
    Color,
    chip,
    draw_arc_text,
    felt_background,
    paste_card,
)
from bot.utils.fonts import Weight, pretendard
from bot.utils.glyph_filter import drawable_text
from bot.utils.photo_encoding import encode_photo
from bot.utils.themes import Theme

__all__ = ["Color", "SeatView", "TableLayout", "TableImageRenderer"]


@dataclass(frozen=True)
class SeatView:
    """
    이미지에 그릴 좌석 정보 (도메인 모델과 분리된 표시용 값)

    Attributes:
        name: 플레이어 이름
        hands: 핸드 목록 (스플릿이면 2개)
        bet: 총 베팅액
        active: 현재 차례 여부 (테두리 강조)
        status: 좌석 하단 상태 문구 (예: "버스트", "승리 +$100.00")
        status_color: 상태 문구 색상
    """

    name: str
    hands: List[List[str]]
    bet: float
    active: bool = False
    status: str = ""
    status_color: Color = CREAM


@dataclass
class TableLayout:
    """레이아웃 수치 (좌석 수에 따라 높이 계산)"""

    width: int = 1600
    margin: int = 40
    columns: int = 4
    seat_width: int = 360
    seat_height: int = 350
    gap: int = 24
    dealer_height: int = 420
    dealer_scale: float = 0.62
    seat_scale: float = 0.42
    card_gap: int = 10
    dealer_chip_size: int = 96
    seat_chip_size: int = 56
    # 딜러 카드 아래 아치형 규칙 문구 (원 중심이 이미지 위쪽 밖에 있어 완만한 곡선)
    arc_center: Tuple[int, int] = (800, -1000)
    arc_radii: Tuple[int, int] = (1400, 1440)
    # 결과 화면에서 규칙 문구 대신 쓰는 펠트 문구의 세로 중심 (딜러 카드와 좌석 사이)
    caption_y: int = 410

    def rows(self, seat_count: int) -> int:
        return max(1, math.ceil(seat_count / self.columns))

    def height(self, seat_count: int) -> int:
        grid = self.rows(seat_count) * (self.seat_height + self.gap)
        return self.margin + self.dealer_height + self.gap + grid + self.margin

    def seat_origin(self, index: int, seat_count: int) -> Tuple[int, int]:
        """index번째 좌석 상자의 좌상단 좌표 (덜 찬 마지막 줄은 가운데 정렬)"""
        row, col = divmod(index, self.columns)
        in_row = min(self.columns, seat_count - row * self.columns)
        row_width = in_row * self.seat_width + (in_row - 1) * self.gap
        left = (self.width - row_width) // 2
        top = self.margin + self.dealer_height + self.gap
        return (
            left + col * (self.seat_width + self.gap),
            top + row * (self.seat_height + self.gap),
        )


class TableImageRenderer:
    """딜러 + 좌석 그리드 이미지 렌더러"""

    def __init__(self, cards: CasinoCardRenderer, layout: Optional[TableLayout] = None):
        self.cards = cards
        self.layout = layout or TableLayout()
        self.font_name = pretendard(34, Weight.SEMIBOLD)
        self.font_small = pretendard(28, Weight.MEDIUM)
        self.font_dealer = pretendard(32, Weight.SEMIBOLD)
        self.font_caption = pretendard(40, Weight.SEMIBOLD)

    # ── 카드 ──────────────────────────────────────────────────

    def _card_size(self, scale: float) -> Tuple[int, int]:
        return self.cards.scaled_card_size(scale)

    def _draw_fan(
        self,
        image: Image.Image,
        hand: List[str],
        x: int,
        y: int,
        max_width: int,
        scale: float,
        hide_first: bool = False,
    ) -> None:
        """max_width 안에 들어가도록 카드를 겹쳐 펼쳐 그림 (카드마다 그림자)"""
        if not hand:
            return
        step = self._fan_step(len(hand), max_width, scale)
        for i, card_str in enumerate(hand):
            card = self.cards.scaled_card(card_str, hide_first and i == 0, scale)
            paste_card(image, card, x + i * step, y)

    def _fan_step(self, count: int, max_width: int, scale: float) -> int:
        """카드 간 간격 — 여유가 있으면 살짝 띄우고, 없으면 max_width 안으로 겹침"""
        card_w, _ = self._card_size(scale)
        step = card_w + self.layout.card_gap
        if count > 1:
            step = min(step, (max_width - card_w) // (count - 1))
        return step

    def _fan_width(self, count: int, max_width: int, scale: float) -> int:
        """_draw_fan이 실제로 차지하는 너비"""
        if count == 0:
            return 0
        card_w, _ = self._card_size(scale)
        return card_w + (count - 1) * self._fan_step(count, max_width, scale)

    # ── 텍스트 ────────────────────────────────────────────────

    @staticmethod
    def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    def _fit(self, draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
        """그릴 수 없는 문자(이모지 등)를 빼고, max_width를 넘으면 말줄임"""
        text = drawable_text(text, font)
        if self._text_width(draw, text, font) <= max_width:
            return text
        while text and self._text_width(draw, text + "…", font) > max_width:
            text = text[:-1]
        return text + "…"

    # ── 섹션 ──────────────────────────────────────────────────

    def _seat_box(
        self,
        image: Image.Image,
        box: Tuple[int, int, int, int],
        highlight: Optional[Color] = None,
    ) -> None:
        """펠트에 인쇄된 좌석 상자 (highlight 색이 있으면 그 색의 굵은 테두리로 강조)"""
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        if highlight is None:
            fill, outline, width = (0, 0, 0, 38), FELT_INK + (140,), 2
        else:
            fill, outline, width = (0, 0, 0, 70), highlight + (255,), 6
        draw.rounded_rectangle(box, radius=24, fill=fill, outline=outline, width=width)
        image.alpha_composite(overlay)

    def _draw_felt_lines(self, image: Image.Image, lines: Tuple[str, ...]) -> None:
        """딜러 카드 아래 아치형 규칙 문구 (진행 중에만)"""
        layout = self.layout
        styles = [(30, Weight.MEDIUM, 210), (20, Weight.REGULAR, 150)]
        for line, radius, (size, weight, alpha) in zip(lines, layout.arc_radii, styles):
            font = pretendard(size, weight)
            draw_arc_text(
                image,
                drawable_text(line, font),
                layout.arc_center,
                radius,
                font,
                FELT_INK + (alpha,),
            )

    def _draw_dealer(
        self,
        image: Image.Image,
        dealer_hand: List[str],
        hide_first: bool,
        label: str,
    ) -> None:
        layout = self.layout
        draw = ImageDraw.Draw(image)
        center_x = layout.width // 2
        chip_space = layout.dealer_chip_size + 24
        max_width = layout.width - 2 * (layout.margin + chip_space)

        title = self._fit(draw, label, self.font_dealer, max_width)
        draw.text(
            (center_x, layout.margin + 18),
            title,
            fill=FELT_INK,
            font=self.font_dealer,
            anchor="mm",
        )

        cards_top = layout.margin + 50
        fan_width = self._fan_width(len(dealer_hand), max_width, layout.dealer_scale)
        fan_x = center_x - fan_width // 2
        self._draw_fan(
            image,
            dealer_hand,
            fan_x,
            cards_top,
            max_width,
            layout.dealer_scale,
            hide_first=hide_first,
        )
        if dealer_hand and not hide_first:
            _, card_h = self._card_size(layout.dealer_scale)
            total = chip(
                str(calculate_hand_value(dealer_hand)),
                CHIP_BLACK,
                layout.dealer_chip_size,
            )
            image.alpha_composite(
                total,
                (fan_x + fan_width + 24, cards_top + (card_h - total.height) // 2),
            )

    def _draw_seat(
        self, image: Image.Image, index: int, seat_count: int, seat: SeatView
    ) -> None:
        layout = self.layout
        x, y = layout.seat_origin(index, seat_count)
        box = (x, y, x + layout.seat_width, y + layout.seat_height)
        # 현재 차례 좌석은 상태 문구(▶ 차례)와 같은 색으로 테두리 강조
        self._seat_box(image, box, seat.status_color if seat.active else None)
        draw = ImageDraw.Draw(image)
        inner = layout.seat_width - 40

        # 이름 (왼쪽) / 베팅 (오른쪽, 펠트 인쇄색)
        bet_text = f"${seat.bet:,.0f}"
        bet_width = self._text_width(draw, bet_text, self.font_small)
        name = self._fit(draw, seat.name, self.font_name, inner - bet_width - 16)
        draw.text((x + 20, y + 16), name, fill=CREAM, font=self.font_name)
        draw.text(
            (x + layout.seat_width - 20 - bet_width, y + 22),
            bet_text,
            fill=FELT_INK,
            font=self.font_small,
        )

        # 카드 + 핸드별 합계 칩 (스플릿이면 가로로 나눠서)
        _, card_h = self._card_size(layout.seat_scale)
        hand_width = inner // max(1, len(seat.hands))
        chip_top = y + 70 + card_h + 14
        for i, hand in enumerate(seat.hands):
            hand_x = x + 20 + i * hand_width
            self._draw_fan(
                image, hand, hand_x, y + 70, hand_width - 10, layout.seat_scale
            )
            if hand:
                total = chip(
                    str(calculate_hand_value(hand)), CHIP_RED, layout.seat_chip_size
                )
                image.alpha_composite(total, (hand_x, chip_top))

        if seat.status:
            status = self._fit(draw, seat.status, self.font_small, inner)
            draw.text(
                (x + 20, y + layout.seat_height - 46),
                status,
                fill=seat.status_color,
                font=self.font_small,
            )

    def _draw_caption(self, image: Image.Image, text: str) -> None:
        """딜러 카드와 좌석 사이 펠트에 인쇄된 문구 (예: 라운드 결과)"""
        layout = self.layout
        draw = ImageDraw.Draw(image)
        text = self._fit(
            draw, text, self.font_caption, layout.width - 2 * layout.margin
        )
        draw.text(
            (layout.width // 2, layout.caption_y),
            text,
            fill=FELT_INK,
            font=self.font_caption,
            anchor="mm",
        )

    # ── 공개 API ──────────────────────────────────────────────

    def render(
        self,
        dealer_hand: List[str],
        seats: List[SeatView],
        hide_dealer_first: bool = True,
        dealer_label: str = "Dealer",
        caption: str = "",
        felt_lines: Tuple[str, ...] = (),
    ) -> bytes:
        """
        테이블 이미지 생성

        Args:
            dealer_hand: 딜러 카드
            seats: 좌석 표시 정보 (착석 순서)
            hide_dealer_first: 딜러 홀 카드(첫 장) 가림 여부
            dealer_label: 딜러 라벨
            caption: 딜러 카드 아래 펠트 문구 (예: 라운드 결과, 없으면 생략)
            felt_lines: 딜러 카드 아래 아치형 규칙 문구 (진행 중, 없으면 생략)

        Returns:
            bytes: JPEG 이미지
        """
        layout = self.layout
        image = felt_background(layout.width, layout.height(len(seats)))

        if felt_lines:
            self._draw_felt_lines(image, felt_lines)
        elif caption:
            self._draw_caption(image, caption)
        self._draw_dealer(image, dealer_hand, hide_dealer_first, dealer_label)
        for index, seat in enumerate(seats):
            self._draw_seat(image, index, len(seats), seat)

        return encode_photo(image)


_table_renderers: Dict[str, TableImageRenderer] = {}


def get_table_renderer(theme: Optional[Theme] = None) -> TableImageRenderer:
    """테마별 테이블 렌더러 (카드 캐시 유지를 위해 재사용)"""
    theme_name = theme.name if theme else "Classic"
    if theme_name not in _table_renderers:
        _table_renderers[theme_name] = TableImageRenderer(get_casino_renderer(theme))
    return _table_renderers[theme_name]
