"""
JackPy - 1인 게임 이미지 렌더러 (펠트 테이블)
딜러 카드는 위, 플레이어 핸드는 아래, 가운데엔 펠트에 인쇄된 규칙 문구(진행 중)
또는 결과 배지(종료)를 그린다. 도메인 객체 대신 표시용 값(GameScene)만 받으며,
BlackjackGame → GameScene 변환은 game_scene.py가 맡는다.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from bot.utils.casino_card_renderer import CasinoCardRenderer, get_casino_renderer
from bot.utils.felt import (
    ACTIVE_COLOR,
    CHIP_BLACK,
    CHIP_RED,
    CREAM,
    FELT_INK,
    TONE_COLORS,
    Tone,
    chip,
    draw_arc_text,
    felt_background,
    paste_card,
    pill,
)
from bot.utils.fonts import Weight, fitting_pretendard, pretendard, text_width
from bot.utils.glyph_filter import drawable_text
from bot.utils.photo_encoding import encode_photo

# 플레이어 핸드에서 뒷면으로 그릴 카드 (HIT 연출: 받을 카드를 먼저 뒷면으로 보여줌)
FACE_DOWN = "BACK"


@dataclass(frozen=True)
class HandScene:
    """
    플레이어 핸드 하나 (표시용 값)

    Attributes:
        cards: 카드 문자열 (FACE_DOWN은 뒷면)
        total: 합계 (뒷면 카드 제외)
        bet: 이 핸드의 베팅액
        active: 스플릿에서 지금 플레이 중인 핸드
        outcome: 스플릿 결과 화면의 핸드별 결과 문구 (없으면 생략)
        tone: outcome 색
    """

    cards: List[str]
    total: int
    bet: float
    active: bool = False
    outcome: str = ""
    tone: Optional[Tone] = None


@dataclass(frozen=True)
class ResultBanner:
    """결과 배지 ("승리! +$100.00")와 그 아래 부가 정보 줄"""

    headline: str
    amount: str
    tone: Tone
    details: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class GameScene:
    """
    게임 이미지 한 장의 표시용 값

    Attributes:
        dealer: 딜러 카드
        dealer_total: 딜러 합계 (None이면 홀 카드(첫 장)를 가림)
        hands: 플레이어 핸드 (스플릿이면 2개)
        felt_lines: 펠트에 인쇄할 규칙 문구 (진행 중에만 표시)
        bet_label: 베팅 원 안의 작은 라벨
        result: 결과 배지 (None이면 진행 중)
    """

    dealer: List[str]
    dealer_total: Optional[int]
    hands: List[HandScene]
    felt_lines: Tuple[str, ...]
    bet_label: str
    result: Optional[ResultBanner] = None

    @property
    def hide_hole(self) -> bool:
        return self.dealer_total is None


@dataclass(frozen=True)
class GameLayout:
    """
    레이아웃 수치 (정사각 고정 크기)

    텔레그램은 사진을 말풍선 폭에 맞춰 줄이므로, 폰에서 보이는 크기는 요소가
    이미지 폭에서 차지하는 비율로 정해진다 — 빈 펠트를 줄이고 카드·글자를 키운다.
    """

    width: int = 1080
    height: int = 1080
    margin: int = 30
    gap: int = 24
    card_gap: int = 16
    dealer_top: int = 40
    player_center_y: int = 830
    card_scale: float = 0.9
    split_card_scale: float = 0.7
    chip_size: int = 140
    split_chip_size: int = 100
    bet_diameter: int = 140
    split_bet_diameter: int = 96
    split_slot_gap: int = 40
    arc_center: Tuple[int, int] = (540, -700)
    arc_radii: Tuple[int, int] = (1190, 1240)
    arc_font_sizes: Tuple[int, int] = (40, 28)
    badge_top: int = 396
    badge_font_size: int = 76
    details_top: int = 572
    details_line_height: int = 52
    details_font_size: int = 40
    details_max_lines: int = 2
    outcome_font_size: int = 36


def format_bet(amount: float) -> str:
    """베팅 원 안의 금액 ($100 / $12.50)"""
    if float(amount).is_integer():
        return f"${amount:,.0f}"
    return f"${amount:,.2f}"


class FeltGameRenderer:
    """펠트 테이블 1인 게임 이미지"""

    def __init__(
        self, cards: CasinoCardRenderer, layout: Optional[GameLayout] = None
    ) -> None:
        self.cards = cards
        self.layout = layout or GameLayout()
        self._base_cache: Dict[Tuple[str, ...], Image.Image] = {}

    # ── 공개 API ──────────────────────────────────────────────

    def render(self, scene: GameScene) -> bytes:
        """GameScene → JPEG 바이트"""
        image = self._base(scene.felt_lines if scene.result is None else ())
        self._draw_dealer(image, scene)
        self._draw_hands(image, scene)
        if scene.result is not None:
            self._draw_result(image, scene.result)
        return encode_photo(image)

    # ── 배경 ──────────────────────────────────────────────────

    def _base(self, felt_lines: Tuple[str, ...]) -> Image.Image:
        """펠트 + 아치형 규칙 문구 (문구 조합별 캐시, 매번 사본 반환)"""
        if felt_lines not in self._base_cache:
            layout = self.layout
            image = felt_background(layout.width, layout.height)
            big, small = layout.arc_font_sizes
            styles = [(big, Weight.MEDIUM, 210), (small, Weight.REGULAR, 150)]
            for line, radius, (size, weight, alpha) in zip(
                felt_lines, layout.arc_radii, styles
            ):
                font = pretendard(size, weight)
                draw_arc_text(
                    image,
                    drawable_text(line, font),
                    layout.arc_center,
                    radius,
                    font,
                    FELT_INK + (alpha,),
                )
            self._base_cache[felt_lines] = image
        return self._base_cache[felt_lines].copy()

    # ── 카드 ──────────────────────────────────────────────────

    def _fan_width(self, count: int, scale: float, max_width: int) -> int:
        card_w, _ = self.cards.scaled_card_size(scale)
        return card_w + (count - 1) * self._fan_step(count, scale, max_width)

    def _fan_step(self, count: int, scale: float, max_width: int) -> int:
        """카드 간격 — 여유가 있으면 띄우고, 넘치면 max_width 안으로 겹침"""
        card_w, _ = self.cards.scaled_card_size(scale)
        step = card_w + self.layout.card_gap
        if count > 1:
            step = min(step, (max_width - card_w) // (count - 1))
        return step

    def _draw_fan(
        self,
        image: Image.Image,
        cards: List[str],
        origin: Tuple[int, int],
        scale: float,
        max_width: int,
        hide_first: bool = False,
    ) -> None:
        x, y = origin
        step = self._fan_step(len(cards), scale, max_width)
        for i, card_str in enumerate(cards):
            face_down = card_str == FACE_DOWN or (hide_first and i == 0)
            card = self.cards.scaled_card(card_str, face_down, scale)
            paste_card(image, card, x + i * step, y)

    # ── 딜러 ──────────────────────────────────────────────────

    def _draw_dealer(self, image: Image.Image, scene: GameScene) -> None:
        layout = self.layout
        if not scene.dealer:
            return
        scale = layout.card_scale
        _, card_h = self.cards.scaled_card_size(scale)
        chip_space = layout.chip_size + layout.gap
        max_width = layout.width - 2 * (layout.margin + chip_space)
        fan_width = self._fan_width(len(scene.dealer), scale, max_width)
        x = (layout.width - fan_width) // 2
        self._draw_fan(
            image,
            scene.dealer,
            (x, layout.dealer_top),
            scale,
            max_width,
            hide_first=scene.hide_hole,
        )
        if scene.dealer_total is not None:
            total_chip = chip(str(scene.dealer_total), CHIP_BLACK, layout.chip_size)
            chip_y = layout.dealer_top + (card_h - total_chip.height) // 2
            image.alpha_composite(total_chip, (x + fan_width + layout.gap, chip_y))

    # ── 플레이어 ──────────────────────────────────────────────

    def _draw_hands(self, image: Image.Image, scene: GameScene) -> None:
        """핸드마다 [베팅 원] [카드] [합계 칩] 묶음을 칸 가운데에 배치"""
        layout = self.layout
        count = max(1, len(scene.hands))
        split = count > 1
        usable = layout.width - 2 * layout.margin
        slot_width = (usable - (count - 1) * layout.split_slot_gap) // count
        for i, hand in enumerate(scene.hands):
            slot_x = layout.margin + i * (slot_width + layout.split_slot_gap)
            self._draw_hand(image, hand, scene.bet_label, slot_x, slot_width, split)

    def _draw_hand(
        self,
        image: Image.Image,
        hand: HandScene,
        bet_label: str,
        slot_x: int,
        slot_width: int,
        split: bool,
    ) -> None:
        layout = self.layout
        scale = layout.split_card_scale if split else layout.card_scale
        chip_size = layout.split_chip_size if split else layout.chip_size
        bet_d = layout.split_bet_diameter if split else layout.bet_diameter
        _, card_h = self.cards.scaled_card_size(scale)

        fan_max = slot_width - bet_d - chip_size - 2 * layout.gap
        fan_width = self._fan_width(len(hand.cards), scale, fan_max)
        group_width = bet_d + layout.gap + fan_width + layout.gap + chip_size
        x = slot_x + (slot_width - group_width) // 2
        center_y = layout.player_center_y
        cards_x = x + bet_d + layout.gap
        cards_top = center_y - card_h // 2

        self._draw_bet_circle(
            image, (x + bet_d // 2, center_y), bet_d, hand.bet, bet_label
        )
        self._draw_fan(image, hand.cards, (cards_x, cards_top), scale, fan_max)
        total_chip = chip(str(hand.total), CHIP_RED, chip_size)
        image.alpha_composite(
            total_chip,
            (cards_x + fan_width + layout.gap, center_y - chip_size // 2),
        )

        below = center_y + card_h // 2
        draw = ImageDraw.Draw(image)
        if hand.active:
            draw.rounded_rectangle(
                (cards_x, below + 14, cards_x + fan_width, below + 20),
                radius=3,
                fill=ACTIVE_COLOR,
            )
        if hand.outcome:
            font = fitting_pretendard(
                hand.outcome, Weight.SEMIBOLD, layout.outcome_font_size, slot_width
            )
            color = TONE_COLORS[hand.tone] if hand.tone else CREAM
            draw.text(
                (cards_x + fan_width // 2, below + 42),
                drawable_text(hand.outcome, font),
                font=font,
                fill=color,
                anchor="mm",
            )

    def _draw_bet_circle(
        self,
        image: Image.Image,
        center: Tuple[int, int],
        diameter: int,
        bet: float,
        label: str,
    ) -> None:
        """펠트에 인쇄된 베팅 원 + 금액"""
        cx, cy = center
        radius = diameter // 2
        draw = ImageDraw.Draw(image)
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=FELT_INK + (170,),
            width=3,
        )
        amount = format_bet(bet)
        amount_font = fitting_pretendard(
            amount, Weight.SEMIBOLD, diameter // 4, diameter - 24
        )
        label_font = pretendard(max(12, diameter // 7), Weight.MEDIUM)
        draw.text(
            (cx, cy - diameter // 10), amount, font=amount_font, fill=CREAM, anchor="mm"
        )
        draw.text(
            (cx, cy + diameter // 5),
            drawable_text(label, label_font),
            font=label_font,
            fill=FELT_INK,
            anchor="mm",
        )

    # ── 결과 ──────────────────────────────────────────────────

    def _draw_result(self, image: Image.Image, result: ResultBanner) -> None:
        layout = self.layout
        color = TONE_COLORS[result.tone]
        max_width = layout.width - 2 * layout.margin
        text = f"{result.headline}  {result.amount}"
        font = fitting_pretendard(
            text, Weight.BOLD, layout.badge_font_size, max_width - 90
        )
        badge = pill(drawable_text(text, font), font, color)
        image.alpha_composite(
            badge, ((layout.width - badge.width) // 2, layout.badge_top)
        )

        details_font = pretendard(layout.details_font_size, Weight.MEDIUM)
        draw = ImageDraw.Draw(image)
        for i, line in enumerate(self._detail_lines(result.details, details_font)):
            draw.text(
                (
                    layout.width // 2,
                    layout.details_top + i * layout.details_line_height,
                ),
                line,
                font=details_font,
                fill=CREAM,
                anchor="mm",
            )

    def _detail_lines(self, details: List[str], font) -> List[str]:
        """부가 정보를 가로폭에 맞춰 줄로 묶음 (최대 줄 수 초과분은 마지막 줄에 이어 붙임)"""
        layout = self.layout
        max_width = layout.width - 2 * layout.margin
        items = [drawable_text(d, font) for d in details]
        lines: List[str] = []
        for item in filter(None, items):
            if lines and text_width(font, f"{lines[-1]}   {item}") <= max_width:
                lines[-1] = f"{lines[-1]}   {item}"
            elif len(lines) < layout.details_max_lines:
                lines.append(item)
            else:
                lines[-1] = f"{lines[-1]}   {item}"
        return lines


_game_renderer: Optional[FeltGameRenderer] = None


def get_game_renderer() -> FeltGameRenderer:
    """펠트 게임 렌더러 (카드·배경 캐시 유지를 위해 재사용)"""
    global _game_renderer
    if _game_renderer is None:
        _game_renderer = FeltGameRenderer(get_casino_renderer())
    return _game_renderer
