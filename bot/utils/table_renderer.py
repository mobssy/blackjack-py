"""
JackPy - 멀티 테이블 이미지 렌더러 (펠트 테이블)
딜러와 최대 7개 좌석을 한 장에 그린다. 1인 게임 이미지와 같은 펠트·칩·팔레트
(felt.py)를 쓰고, 카드는 CasinoCardRenderer, 글자는 Pretendard(fonts.py)를 쓴다.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

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

__all__ = [
    "DENSE_LAYOUT",
    "ROOMY_LAYOUT",
    "ROOMY_MAX_SEATS",
    "Color",
    "SeatView",
    "TableLayout",
    "TableImageRenderer",
    "table_layout_for",
]


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


@dataclass(frozen=True)
class TableLayout:
    """
    레이아웃 수치 (좌석 수에 따라 높이 계산)

    텔레그램은 사진을 말풍선 폭에 맞춰 줄이므로, 폰에서 보이는 크기는 요소가
    이미지 폭에서 차지하는 비율로 정해진다. 그래서 한 줄 좌석 수(columns)를 줄여
    카드·글자를 키운다 — 인원에 따라 table_layout_for가 프리셋을 고른다.
    """

    width: int = 1200
    margin: int = 30
    columns: int = 2
    gap: int = 20
    seat_scale: float = 0.62
    seat_chip_size: int = 72
    name_font_size: int = 40
    small_font_size: int = 32
    dealer_height: int = 430
    dealer_scale: float = 0.75
    dealer_chip_size: int = 110
    dealer_font_size: int = 34
    caption_font_size: int = 44
    # 딜러 카드 아래 아치형 규칙 문구 (원 중심이 이미지 위쪽 밖에 있어 완만한 곡선)
    arc_center: Tuple[int, int] = (600, -900)
    arc_radii: Tuple[int, int] = (1290, 1330)
    arc_font_sizes: Tuple[int, int] = (36, 24)
    # 결과 화면에서 규칙 문구 대신 쓰는 펠트 문구의 세로 중심 (딜러 카드와 좌석 사이)
    caption_y: int = 410

    @property
    def seat_width(self) -> int:
        usable = self.width - 2 * self.margin - (self.columns - 1) * self.gap
        return usable // self.columns

    @property
    def header_height(self) -> int:
        """좌석 상자 위쪽 이름/베팅 줄"""
        return self.name_font_size + 34

    @property
    def seat_card_height(self) -> int:
        return int(CasinoCardRenderer.CARD_HEIGHT * self.seat_scale)

    @property
    def seat_height(self) -> int:
        """이름 줄 + 카드 + 합계 칩 + 상태 문구"""
        return (
            self.header_height
            + self.seat_card_height
            + 14
            + self.seat_chip_size
            + 12
            + self.small_font_size
            + 22
        )

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


# 4명까지는 한 줄 2석으로 크게, 5~7명은 한 줄 3석
ROOMY_LAYOUT = TableLayout()
DENSE_LAYOUT = TableLayout(
    columns=3,
    seat_scale=0.46,
    seat_chip_size=60,
    name_font_size=34,
    small_font_size=28,
)
ROOMY_MAX_SEATS = 4


def table_layout_for(seat_count: int) -> TableLayout:
    """인원에 맞는 레이아웃 프리셋"""
    return ROOMY_LAYOUT if seat_count <= ROOMY_MAX_SEATS else DENSE_LAYOUT


class TableImageRenderer:
    """딜러 + 좌석 그리드 이미지 렌더러"""

    CARD_GAP = 10  # 카드 사이 간격 (여유가 있을 때)

    def __init__(self, cards: CasinoCardRenderer, layout: Optional[TableLayout] = None):
        """layout을 주면 항상 그 레이아웃, 없으면 인원에 따라 table_layout_for로 고름"""
        self.cards = cards
        self.fixed_layout = layout

    def layout_for(self, seat_count: int) -> TableLayout:
        return self.fixed_layout or table_layout_for(seat_count)

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
        step = card_w + self.CARD_GAP
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

    def _draw_felt_lines(
        self, image: Image.Image, layout: TableLayout, lines: Tuple[str, ...]
    ) -> None:
        """딜러 카드 아래 아치형 규칙 문구 (진행 중에만)"""
        big, small = layout.arc_font_sizes
        styles = [(big, Weight.MEDIUM, 210), (small, Weight.REGULAR, 150)]
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
        layout: TableLayout,
        dealer_hand: List[str],
        hide_first: bool,
        label: str,
    ) -> None:
        draw = ImageDraw.Draw(image)
        center_x = layout.width // 2
        chip_space = layout.dealer_chip_size + 24
        max_width = layout.width - 2 * (layout.margin + chip_space)

        font = pretendard(layout.dealer_font_size, Weight.SEMIBOLD)
        draw.text(
            (center_x, layout.margin + 18),
            self._fit(draw, label, font, max_width),
            fill=FELT_INK,
            font=font,
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
        self,
        image: Image.Image,
        layout: TableLayout,
        index: int,
        seat_count: int,
        seat: SeatView,
    ) -> None:
        x, y = layout.seat_origin(index, seat_count)
        box = (x, y, x + layout.seat_width, y + layout.seat_height)
        # 현재 차례 좌석은 상태 문구(▶ 차례)와 같은 색으로 테두리 강조
        self._seat_box(image, box, seat.status_color if seat.active else None)
        draw = ImageDraw.Draw(image)
        inner = layout.seat_width - 40
        font_name = pretendard(layout.name_font_size, Weight.SEMIBOLD)
        font_small = pretendard(layout.small_font_size, Weight.MEDIUM)

        # 이름 (왼쪽) / 베팅 (오른쪽, 펠트 인쇄색) — 같은 줄 가운데 맞춤
        name_center_y = y + layout.header_height // 2
        bet_text = f"${seat.bet:,.0f}"
        bet_width = self._text_width(draw, bet_text, font_small)
        name = self._fit(draw, seat.name, font_name, inner - bet_width - 16)
        draw.text(
            (x + 20, name_center_y), name, fill=CREAM, font=font_name, anchor="lm"
        )
        draw.text(
            (x + layout.seat_width - 20, name_center_y),
            bet_text,
            fill=FELT_INK,
            font=font_small,
            anchor="rm",
        )

        # 카드 + 핸드별 합계 칩 (스플릿이면 가로로 나눠서)
        cards_top = y + layout.header_height
        hand_width = inner // max(1, len(seat.hands))
        chip_top = cards_top + layout.seat_card_height + 14
        for i, hand in enumerate(seat.hands):
            hand_x = x + 20 + i * hand_width
            self._draw_fan(
                image, hand, hand_x, cards_top, hand_width - 10, layout.seat_scale
            )
            if hand:
                total = chip(
                    str(calculate_hand_value(hand)), CHIP_RED, layout.seat_chip_size
                )
                image.alpha_composite(total, (hand_x, chip_top))

        if seat.status:
            status = self._fit(draw, seat.status, font_small, inner)
            draw.text(
                (x + 20, y + layout.seat_height - 22),
                status,
                fill=seat.status_color,
                font=font_small,
                anchor="ls",
            )

    def _draw_caption(self, image: Image.Image, layout: TableLayout, text: str) -> None:
        """딜러 카드와 좌석 사이 펠트에 인쇄된 문구 (예: 라운드 결과)"""
        draw = ImageDraw.Draw(image)
        font = pretendard(layout.caption_font_size, Weight.SEMIBOLD)
        draw.text(
            (layout.width // 2, layout.caption_y),
            self._fit(draw, text, font, layout.width - 2 * layout.margin),
            fill=FELT_INK,
            font=font,
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
        layout = self.layout_for(len(seats))
        image = felt_background(layout.width, layout.height(len(seats)))

        if felt_lines:
            self._draw_felt_lines(image, layout, felt_lines)
        elif caption:
            self._draw_caption(image, layout, caption)
        self._draw_dealer(image, layout, dealer_hand, hide_dealer_first, dealer_label)
        for index, seat in enumerate(seats):
            self._draw_seat(image, layout, index, len(seats), seat)

        return encode_photo(image)


_table_renderer = TableImageRenderer(get_casino_renderer())


def get_table_renderer() -> TableImageRenderer:
    """공용 테이블 렌더러 (카드 축소 캐시는 카드 렌더러가 공유)"""
    return _table_renderer
