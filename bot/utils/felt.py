"""
JackPy - 펠트 테이블 그리기 요소
초록 펠트 배경, 펠트에 인쇄된 곡선 문구, 합계 칩, 카드 그림자, 결과 배지 등
게임 이미지와 테이블 이미지가 함께 쓰는 그리기 도구 (도메인 의존성 없음)
"""

import math
from enum import Enum
from functools import lru_cache
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFilter

from bot.utils.fonts import Weight, pretendard, text_width

Color = Tuple[int, int, int]

FELT_LIGHT: Color = (28, 98, 70)
FELT_DARK: Color = (10, 52, 38)
FELT_INK: Color = (196, 170, 104)  # 펠트에 인쇄된 금색 글씨
CREAM: Color = (245, 240, 228)
CHIP_RED: Color = (178, 34, 46)
CHIP_BLACK: Color = (28, 28, 30)
BADGE_FILL = (8, 30, 22, 225)


class Tone(Enum):
    """결과 색 계열 (1인 게임·테이블 이미지 공용)"""

    WIN = "win"
    LOSS = "loss"
    PUSH = "push"
    BLACKJACK = "blackjack"


TONE_COLORS: Dict[Tone, Color] = {
    Tone.WIN: (64, 196, 120),
    Tone.LOSS: (226, 82, 82),
    Tone.PUSH: (222, 216, 196),
    Tone.BLACKJACK: (240, 196, 80),
}
ACTIVE_COLOR: Color = (240, 196, 80)  # 지금 차례인 핸드/좌석 강조

# 펠트 그라데이션을 계산하는 저해상도 격자 (크게 늘려도 부드러운 그라데이션이라 충분)
_GRADIENT_GRID = (120, 90)


def _lerp(a: Color, b: Color, t: float) -> Tuple[int, ...]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


@lru_cache(maxsize=16)
def _felt(width: int, height: int) -> Image.Image:
    grid_w, grid_h = _GRADIENT_GRID
    small = Image.new("RGB", _GRADIENT_GRID)
    center_x, center_y = grid_w / 2, grid_h * 0.42
    max_dist = math.hypot(center_x, grid_h - center_y)
    for y in range(grid_h):
        for x in range(grid_w):
            t = min(1.0, math.hypot(x - center_x, y - center_y) / max_dist)
            small.putpixel((x, y), _lerp(FELT_LIGHT, FELT_DARK, t * t))
    felt = small.resize((width, height), Image.BICUBIC)

    # 펠트 결 — 아주 옅은 노이즈
    grain = Image.effect_noise((width, height), 40).convert("RGB")
    return Image.blend(felt, grain, 0.04).convert("RGBA")


def felt_background(width: int, height: int) -> Image.Image:
    """가운데가 밝은 초록 펠트 (크기별로 한 번만 계산, 매번 새 사본을 반환)"""
    return _felt(width, height).copy()


def draw_arc_text(
    image: Image.Image,
    text: str,
    center: Tuple[float, float],
    radius: float,
    font,
    color: Tuple[int, ...],
    tracking: int = 2,
) -> None:
    """
    중심이 위쪽에 있는 원의 아랫부분을 따라 글자를 한 자씩 기울여 그림
    (실제 블랙잭 테이블에 인쇄된 아치형 문구)
    """
    center_x, center_y = center
    space = text_width(font, "n")
    widths = [space if ch == " " else text_width(font, ch) + tracking for ch in text]
    theta = math.pi / 2 + sum(widths) / radius / 2  # 왼쪽 끝 각도
    for ch, width in zip(text, widths):
        half = width / 2 / radius
        theta -= half
        if ch != " ":
            side = max(width, font.size) * 3
            tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            ImageDraw.Draw(tile).text(
                (side // 2, side // 2), ch, font=font, fill=color, anchor="mm"
            )
            tile = tile.rotate(math.degrees(math.pi / 2 - theta), Image.BICUBIC)
            x = center_x + radius * math.cos(theta) - side / 2
            y = center_y + radius * math.sin(theta) - side / 2
            image.alpha_composite(tile, (int(x), int(y)))
        theta -= half


@lru_cache(maxsize=256)
def chip(label: str, color: Color, size: int) -> Image.Image:
    """
    카지노 칩 모양 합계 표시 (캐시된 이미지 — 붙여넣기만 하고 수정하지 말 것)

    가장자리 줄무늬 6개 + 안쪽 링 + 가운데 숫자. 3배로 그려서 줄여 계단 현상을 없앤다.
    """
    s = size * 3
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, s - 1, s - 1), fill=color + (255,))
    for k in range(6):
        angle = math.radians(k * 60)
        cx = s / 2 + math.cos(angle) * s * 0.42
        cy = s / 2 + math.sin(angle) * s * 0.42
        corners = [(-0.035, -0.075), (0.035, -0.075), (0.035, 0.075), (-0.035, 0.075)]
        points = [
            (
                cx + (x * math.cos(angle) - y * math.sin(angle)) * s,
                cy + (x * math.sin(angle) + y * math.cos(angle)) * s,
            )
            for x, y in corners
        ]
        draw.polygon(points, fill=CREAM + (255,))
    inset = s * 0.15
    draw.ellipse(
        (inset, inset, s - inset, s - inset),
        fill=color + (255,),
        outline=CREAM + (255,),
        width=max(2, s // 60),
    )
    font = pretendard(int(s * (0.36 if len(label) <= 2 else 0.28)), Weight.BOLD)
    draw.text((s / 2, s / 2), label, font=font, fill=CREAM, anchor="mm")
    return image.resize((size, size), Image.LANCZOS)


@lru_cache(maxsize=8)
def _shadow(size: Tuple[int, int], radius: int) -> Image.Image:
    width, height = size
    pad = radius * 3
    shadow = Image.new("RGBA", (width + pad * 2, height + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (pad, pad + radius // 2, pad + width, pad + height + radius // 2),
        radius=width // 9,
        fill=(0, 0, 0, 150),
    )
    return shadow.filter(ImageFilter.GaussianBlur(radius))


def paste_card(image: Image.Image, card: Image.Image, x: int, y: int) -> None:
    """카드 아래에 부드러운 그림자를 깔고 카드를 붙임"""
    radius = max(6, card.width // 13)
    shadow = _shadow(card.size, radius)
    pad = radius * 3
    image.alpha_composite(shadow, (x - pad, y - pad))
    image.alpha_composite(card, (x, y))


def pill(text: str, font, color: Color, padding: int = 45) -> Image.Image:
    """결과 배지 — 어두운 반투명 알약 + 결과 색 테두리·글자"""
    height = int(font.size * 1.65)
    width = text_width(font, text) + padding * 2
    badge = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    draw.rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=height // 2,
        fill=BADGE_FILL,
        outline=color + (255,),
        width=4,
    )
    draw.text((width // 2, height // 2), text, font=font, fill=color, anchor="mm")
    return badge
