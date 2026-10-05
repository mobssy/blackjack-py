"""
JackPy - 멀티 테이블 이미지 렌더러
딜러와 최대 7개 좌석을 한 장에 그린다.
카드/배경/폰트는 CasinoCardRenderer를 재사용하고, 레이아웃만 담당한다.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from bot.utils.casino_card_renderer import CasinoCardRenderer, get_casino_renderer
from bot.utils.deck import calculate_hand_value
from bot.utils.glyph_filter import drawable_text
from bot.utils.photo_encoding import encode_photo
from bot.utils.themes import Theme

Color = Tuple[int, int, int]
WHITE: Color = (255, 255, 255)


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
    status_color: Color = WHITE


@dataclass
class TableLayout:
    """레이아웃 수치 (좌석 수에 따라 높이 계산)"""

    width: int = 1600
    margin: int = 50
    columns: int = 4
    seat_width: int = 360
    seat_height: int = 330
    gap: int = 24
    dealer_height: int = 360
    footer_height: int = 90
    dealer_scale: float = 0.62
    seat_scale: float = 0.42

    def rows(self, seat_count: int) -> int:
        return max(1, math.ceil(seat_count / self.columns))

    def height(self, seat_count: int, has_footer: bool) -> int:
        grid = self.rows(seat_count) * (self.seat_height + self.gap)
        footer = self.footer_height if has_footer else 0
        return self.margin + self.dealer_height + self.gap + grid + footer + self.margin

    def seat_origin(self, index: int, seat_count: int) -> Tuple[int, int]:
        """index번째 좌석 패널의 좌상단 좌표 (덜 찬 마지막 줄은 가운데 정렬)"""
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
        self._card_cache: Dict[Tuple[str, bool, float], Image.Image] = {}
        self.font_name = self._font_variant(cards.font_title, 34)
        self.font_small = self._font_variant(cards.font_message, 28)
        self.font_dealer = self._font_variant(cards.font_title, 44)

    @staticmethod
    def _font_variant(font, size: int):
        """같은 폰트 파일의 다른 크기 (기본 비트맵 폰트면 그대로)"""
        if isinstance(font, ImageFont.FreeTypeFont):
            return font.font_variant(size=size)
        return font

    # ── 카드 ──────────────────────────────────────────────────

    def _card(self, card_str: str, face_down: bool, scale: float) -> Image.Image:
        """축소된 카드 이미지 (카드별 캐시)"""
        key = (card_str, face_down, scale)
        if key not in self._card_cache:
            image = self.cards.card_image(card_str, face_down=face_down)
            size = (int(image.width * scale), int(image.height * scale))
            self._card_cache[key] = image.resize(size, Image.LANCZOS)
        return self._card_cache[key]

    def _card_size(self, scale: float) -> Tuple[int, int]:
        return (
            int(CasinoCardRenderer.CARD_WIDTH * scale),
            int(CasinoCardRenderer.CARD_HEIGHT * scale),
        )

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
        """max_width 안에 들어가도록 카드를 겹쳐 펼쳐 그림"""
        if not hand:
            return
        step = self._fan_step(len(hand), max_width, scale)
        for i, card_str in enumerate(hand):
            card = self._card(card_str, hide_first and i == 0, scale)
            image.paste(card, (x + i * step, y), card)

    def _fan_step(self, count: int, max_width: int, scale: float) -> int:
        """카드 간 간격 — 여유가 있으면 살짝 띄우고, 없으면 max_width 안으로 겹침"""
        card_w, _ = self._card_size(scale)
        step = card_w + 10
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

    def _panel(
        self,
        image: Image.Image,
        box: Tuple[int, int, int, int],
        highlight: Optional[Color] = None,
    ) -> None:
        """반투명 패널 (highlight 색이 있으면 그 색의 굵은 테두리로 강조)"""
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        if highlight is None:
            fill = (255, 255, 255, 16)
            outline = self.cards.theme.colors.border_color + (130,)
            width = 2
        else:
            fill = (255, 255, 255, 38)
            outline = highlight + (255,)
            width = 6
        draw.rounded_rectangle(box, radius=24, fill=fill, outline=outline, width=width)
        image.alpha_composite(overlay)

    def _draw_dealer(
        self,
        image: Image.Image,
        dealer_hand: List[str],
        hide_first: bool,
        label: str,
    ) -> None:
        layout = self.layout
        box = (
            layout.margin,
            layout.margin,
            layout.width - layout.margin,
            layout.margin + layout.dealer_height,
        )
        self._panel(image, box)
        draw = ImageDraw.Draw(image)
        center_x = (box[0] + box[2]) // 2
        max_width = box[2] - box[0] - 60

        title = label
        if not hide_first and dealer_hand:
            title = f"{label} · {calculate_hand_value(dealer_hand)}"
        title = self._fit(draw, title, self.font_dealer, max_width)
        title_width = self._text_width(draw, title, self.font_dealer)
        draw.text(
            (center_x - title_width // 2, box[1] + 20),
            title,
            fill=WHITE,
            font=self.font_dealer,
        )

        fan_width = self._fan_width(len(dealer_hand), max_width, layout.dealer_scale)
        self._draw_fan(
            image,
            dealer_hand,
            center_x - fan_width // 2,
            box[1] + 95,
            max_width,
            layout.dealer_scale,
            hide_first=hide_first,
        )

    def _draw_seat(
        self, image: Image.Image, index: int, seat_count: int, seat: SeatView
    ) -> None:
        layout = self.layout
        x, y = layout.seat_origin(index, seat_count)
        box = (x, y, x + layout.seat_width, y + layout.seat_height)
        # 현재 차례 좌석은 상태 문구(▶ 차례)와 같은 색으로 테두리 강조
        self._panel(image, box, seat.status_color if seat.active else None)
        draw = ImageDraw.Draw(image)
        inner = layout.seat_width - 40

        # 이름 (왼쪽) / 베팅 (오른쪽)
        bet_text = f"${seat.bet:,.0f}"
        bet_width = self._text_width(draw, bet_text, self.font_small)
        name = self._fit(draw, seat.name, self.font_name, inner - bet_width - 16)
        draw.text((x + 20, y + 16), name, fill=WHITE, font=self.font_name)
        draw.text(
            (x + layout.seat_width - 20 - bet_width, y + 22),
            bet_text,
            fill=self.cards.theme.colors.accent_color,
            font=self.font_small,
        )

        # 카드 (스플릿이면 가로로 나눠서)
        hand_width = inner // max(1, len(seat.hands))
        for i, hand in enumerate(seat.hands):
            self._draw_fan(
                image,
                hand,
                x + 20 + i * hand_width,
                y + 70,
                hand_width - 10,
                layout.seat_scale,
            )

        # 합계 / 상태
        _, card_h = self._card_size(layout.seat_scale)
        values = " / ".join(str(calculate_hand_value(h)) for h in seat.hands if h)
        # 합계도 상태와 같은 색 (버스트 25는 빨강, 승리는 초록)
        draw.text(
            (x + 20, y + 70 + card_h + 10),
            values,
            fill=seat.status_color,
            font=self.font_name,
        )
        if seat.status:
            status = self._fit(draw, seat.status, self.font_small, inner)
            draw.text(
                (x + 20, y + layout.seat_height - 48),
                status,
                fill=seat.status_color,
                font=self.font_small,
            )

    def _draw_footer(self, image: Image.Image, seat_count: int, text: str) -> None:
        layout = self.layout
        draw = ImageDraw.Draw(image)
        y = layout.height(seat_count, True) - layout.margin - layout.footer_height
        text = self._fit(draw, text, self.font_dealer, layout.width - 2 * layout.margin)
        width = self._text_width(draw, text, self.font_dealer)
        draw.text(
            ((layout.width - width) // 2, y + 20),
            text,
            fill=WHITE,
            font=self.font_dealer,
        )

    # ── 공개 API ──────────────────────────────────────────────

    def render(
        self,
        dealer_hand: List[str],
        seats: List[SeatView],
        hide_dealer_first: bool = True,
        dealer_label: str = "Dealer",
        footer: str = "",
    ) -> bytes:
        """
        테이블 이미지 생성

        Args:
            dealer_hand: 딜러 카드
            seats: 좌석 표시 정보 (착석 순서)
            hide_dealer_first: 딜러 홀 카드(첫 장) 가림 여부
            dealer_label: 딜러 라벨
            footer: 하단 안내 문구 (없으면 생략)

        Returns:
            bytes: JPEG 이미지
        """
        layout = self.layout
        height = layout.height(len(seats), bool(footer))
        image = self.cards.background(layout.width, height)

        self._draw_dealer(image, dealer_hand, hide_dealer_first, dealer_label)
        for index, seat in enumerate(seats):
            self._draw_seat(image, index, len(seats), seat)
        if footer:
            self._draw_footer(image, len(seats), footer)

        return encode_photo(image)


_table_renderers: Dict[str, TableImageRenderer] = {}


def get_table_renderer(theme: Optional[Theme] = None) -> TableImageRenderer:
    """테마별 테이블 렌더러 (카드 캐시 유지를 위해 재사용)"""
    theme_name = theme.name if theme else "Classic"
    if theme_name not in _table_renderers:
        _table_renderers[theme_name] = TableImageRenderer(get_casino_renderer(theme))
    return _table_renderers[theme_name]
