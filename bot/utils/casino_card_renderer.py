"""
JackPy - 카드 이미지
assets/cards의 카드 PNG(앞면 52장 + back.png)를 골드 테두리·광택이 있는 카드로 만들고,
렌더러들이 쓰는 크기별 축소본을 캐시한다. 배경·레이아웃·글자는 각 렌더러가 담당한다.
"""

from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter

CARDS_DIR = Path(__file__).parent.parent.parent / "assets" / "cards"
SUIT_NAMES = {"S": "spades", "H": "hearts", "D": "diamonds", "C": "clubs"}

WHITE_RGBA = (255, 255, 255, 255)
METALLIC_GOLD = (255, 215, 0)
DARK_GOLD = (184, 134, 11)
PLATINUM = (229, 228, 226)


def card_asset_path(card_str: str) -> Path:
    """카드 문자열("10D", "AS")의 PNG 경로 (예: 10_of_diamonds.png)"""
    rank, suit = card_str[:-1], card_str[-1]
    return CARDS_DIR / f"{rank}_of_{SUIT_NAMES[suit]}.png"


class CasinoCardRenderer:
    """골드 테두리 카드 앞/뒷면 이미지와 크기별 축소 캐시"""

    CARD_WIDTH = 240
    CARD_HEIGHT = 360
    CARD_RADIUS = 28

    _ASSET_EDGE = 2  # 카드 PNG 자체의 회색 외곽선/투명 모서리 두께
    _ART_INSET = 16  # 골드 테두리(5~15px) 안쪽 — 그림이 테두리에 가리지 않는 여백

    def __init__(self) -> None:
        self._scaled_cache: Dict[Tuple[str, float], Image.Image] = {}

    # ── 공통 재료 (모든 카드에 같으므로 한 번만 만듦) ────────────────

    @staticmethod
    @lru_cache(maxsize=1)
    def _corner_mask() -> Image.Image:
        size = (CasinoCardRenderer.CARD_WIDTH, CasinoCardRenderer.CARD_HEIGHT)
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [(0, 0), size], radius=CasinoCardRenderer.CARD_RADIUS, fill=255
        )
        return mask

    @staticmethod
    @lru_cache(maxsize=1)
    def _gloss() -> Image.Image:
        """왼쪽 위 광택 (블러 반경 60이라 비싸서 한 번만 계산)"""
        width, height = CasinoCardRenderer.CARD_WIDTH, CasinoCardRenderer.CARD_HEIGHT
        gloss = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(gloss).ellipse(
            [(-width * 0.3, -height * 0.4), (width * 0.7, height * 0.3)],
            fill=(255, 255, 255, 40),
        )
        return gloss.filter(ImageFilter.GaussianBlur(radius=60))

    # ── 앞면 ──────────────────────────────────────────────────

    def _fit_card_art(self, art: Image.Image) -> Image.Image:
        """
        카드 그림을 비율 유지한 채 골드 테두리 안쪽 가운데에 배치

        카드 PNG(약 266x376)를 카드 크기로 그대로 늘리면 가로로 찌그러지고,
        모서리 숫자("10")가 위에 그리는 골드 테두리에 가려진다.
        """
        edge = self._ASSET_EDGE
        art = art.crop((edge, edge, art.width - edge, art.height - edge))
        box_w = self.CARD_WIDTH - 2 * self._ART_INSET
        box_h = self.CARD_HEIGHT - 2 * self._ART_INSET
        scale = min(box_w / art.width, box_h / art.height)
        size = (round(art.width * scale), round(art.height * scale))
        art = art.resize(size, Image.LANCZOS)

        canvas = Image.new("RGBA", (self.CARD_WIDTH, self.CARD_HEIGHT), WHITE_RGBA)
        offset = ((self.CARD_WIDTH - size[0]) // 2, (self.CARD_HEIGHT - size[1]) // 2)
        canvas.alpha_composite(art, dest=offset)
        return canvas

    def _front(self, card_str: str) -> Image.Image:
        """앞면 — PNG를 테두리 안쪽에 배치 + 3중 골드 테두리 + 광택"""
        mask = self._corner_mask()
        with Image.open(card_asset_path(card_str)) as art:
            card = Image.new("RGBA", (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))
            card.paste(self._fit_card_art(art.convert("RGBA")), (0, 0), mask)

        draw = ImageDraw.Draw(card)
        frames = [(5, 2, DARK_GOLD, 5), (10, 5, METALLIC_GOLD, 3), (14, 7, PLATINUM, 1)]
        for inset, radius_cut, color, width in frames:
            draw.rounded_rectangle(
                [(inset, inset), (self.CARD_WIDTH - inset, self.CARD_HEIGHT - inset)],
                radius=self.CARD_RADIUS - radius_cut,
                outline=color,
                width=width,
            )

        card = Image.alpha_composite(card, self._gloss())
        # 광택이 둥근 모서리 바깥(투명 영역)에 번지지 않도록 다시 잘라냄
        card.putalpha(ImageChops.multiply(card.getchannel("A"), mask))
        return card

    # ── 뒷면 ──────────────────────────────────────────────────

    def _back(self) -> Image.Image:
        """뒷면 — back.png + 4중 골드 테두리"""
        with Image.open(CARDS_DIR / "back.png") as art:
            art = art.convert("RGBA").resize(
                (self.CARD_WIDTH, self.CARD_HEIGHT), Image.LANCZOS
            )
        card = Image.new("RGBA", art.size, (0, 0, 0, 0))
        card.paste(art, (0, 0), self._corner_mask())

        draw = ImageDraw.Draw(card)
        for i in range(4):
            inset = 5 + i * 4
            draw.rounded_rectangle(
                [(inset, inset), (self.CARD_WIDTH - inset, self.CARD_HEIGHT - inset)],
                radius=self.CARD_RADIUS - i * 2,
                outline=METALLIC_GOLD + (255 - i * 40,),
                width=3,
            )
        return card

    # ── 공개 API ──────────────────────────────────────────────

    def card_image(self, card_str: str, face_down: bool = False) -> Image.Image:
        """카드 한 장 이미지 (CARD_WIDTH × CARD_HEIGHT, RGBA)"""
        return self._back() if face_down else self._front(card_str)

    def scaled_card(self, card_str: str, face_down: bool, scale: float) -> Image.Image:
        """
        축소한 카드 이미지 (카드·크기별 캐시 — 붙여넣기만 하고 수정하지 말 것)

        뒷면은 어떤 카드든 같으므로 한 장만 캐시한다.
        """
        key = ("BACK" if face_down else card_str, scale)
        if key not in self._scaled_cache:
            image = self.card_image(card_str, face_down=face_down)
            self._scaled_cache[key] = image.resize(
                self.scaled_card_size(scale), Image.LANCZOS
            )
        return self._scaled_cache[key]

    def scaled_card_size(self, scale: float) -> Tuple[int, int]:
        """scaled_card가 돌려주는 카드 크기"""
        return int(self.CARD_WIDTH * scale), int(self.CARD_HEIGHT * scale)


_card_renderer = CasinoCardRenderer()


def get_casino_renderer() -> CasinoCardRenderer:
    """공용 카드 렌더러 (축소 카드 캐시를 렌더러들이 공유)"""
    return _card_renderer
