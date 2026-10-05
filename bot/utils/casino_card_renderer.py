"""
JackPy - 카지노급 카드 렌더러
실제 카지노 카드처럼 K, Q, J, A 그림 포함
"""

import logging

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from typing import Dict, Optional, Tuple
from pathlib import Path
from bot.utils.themes import Theme, ThemeManager
import math

logger = logging.getLogger(__name__)

WHITE_RGBA = (255, 255, 255, 255)


class CasinoCardRenderer:
    """
    카지노급 카드 렌더러

    특징:
    - K, Q, J에 실제 얼굴 그림
    - A에 대형 심볼
    - 숫자 카드에 심볼 배치
    - 프로페셔널한 디자인
    """

    CARD_WIDTH = 240
    CARD_HEIGHT = 360
    CARD_SPACING = 35
    CARD_RADIUS = 28

    # 고급 색상
    METALLIC_GOLD = (255, 215, 0)
    DARK_GOLD = (184, 134, 11)
    PLATINUM = (229, 228, 226)

    SUIT_COLORS = {
        "S": (20, 20, 20),
        "C": (25, 25, 25),
        "H": (220, 20, 60),
        "D": (255, 85, 0),
    }

    SUIT_GLOW_COLORS = {
        "S": (100, 100, 255),
        "C": (50, 255, 50),
        "H": (255, 50, 100),
        "D": (255, 200, 50),
    }

    SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}

    def __init__(self, theme: Optional[Theme] = None):
        """초기화"""
        self.theme = theme or ThemeManager.CLASSIC
        self.cards_dir = Path(__file__).parent.parent.parent / "assets" / "cards"
        self._scaled_cache: Dict[Tuple[str, bool, float], Image.Image] = {}
        self._load_fonts()

    def _load_fonts(self):
        """
        카드 그림용 Poppins (직접 그리는 대체 카드의 랭크·무늬, 뒷면 로고)

        게임/테이블 이미지의 글자는 bot/utils/fonts.py의 Pretendard를 쓴다.
        """
        fonts_dir = Path(__file__).parent.parent.parent / "assets" / "fonts" / "Poppins"
        try:
            semibold = str(fonts_dir / "Poppins-SemiBold.ttf")
            regular = str(fonts_dir / "Poppins-Regular.ttf")
            bold = str(fonts_dir / "Poppins-Bold.ttf")
            self.font_rank_large = ImageFont.truetype(semibold, 72)
            self.font_rank_small = ImageFont.truetype(semibold, 48)
            self.font_suit_huge = ImageFont.truetype(regular, 180)
            self.font_suit_large = ImageFont.truetype(regular, 100)
            self.font_suit_medium = ImageFont.truetype(regular, 60)
            self.font_suit_small = ImageFont.truetype(regular, 44)
            self.font_face_letter = ImageFont.truetype(bold, 140)
        except OSError:
            logger.warning("Poppins 폰트를 찾지 못해 기본 폰트로 카드를 그립니다")
            default = ImageFont.load_default()
            self.font_rank_large = default
            self.font_rank_small = default
            self.font_suit_huge = default
            self.font_suit_large = default
            self.font_suit_medium = default
            self.font_suit_small = default
            self.font_face_letter = default

    def _get_card_image_path(self, card_str: str) -> Optional[Path]:
        """
        실제 카드 이미지 파일 경로

        Args:
            card_str: 카드 문자열 (예: "AS", "KH", "TD")

        Returns:
            카드 이미지 경로 또는 None
        """
        # 카드 파일명 매핑
        rank_map = {
            "A": "A",
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "5",
            "6": "6",
            "7": "7",
            "8": "8",
            "9": "9",
            "T": "10",
            "J": "J",
            "Q": "Q",
            "K": "K",
        }
        suit_map = {"S": "spades", "H": "hearts", "D": "diamonds", "C": "clubs"}

        rank = card_str[:-1]
        suit = card_str[-1]

        rank_name = rank_map.get(rank, rank)
        suit_name = suit_map.get(suit, "")

        # 파일명: "A_of_hearts.png"
        filename = f"{rank_name}_of_{suit_name}.png"
        filepath = self.cards_dir / filename

        if filepath.exists():
            return filepath

        return None

    _ASSET_EDGE = 2  # 카드 PNG 자체의 회색 외곽선/투명 모서리 두께
    _ART_INSET = 16  # 골드 테두리(5~15px) 안쪽 — 그림이 테두리에 가리지 않는 여백

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

    def _load_real_card_image(self, card_str: str) -> Optional[Image.Image]:
        """
        실제 카드 이미지 파일 로드

        Args:
            card_str: 카드 문자열

        Returns:
            PIL Image 또는 None
        """
        card_path = self._get_card_image_path(card_str)

        if card_path and card_path.exists():
            try:
                # 이미지 로드
                card_img = Image.open(card_path).convert("RGBA")

                card_img = self._fit_card_art(card_img)

                # 라운드 코너 적용
                mask = Image.new("L", (self.CARD_WIDTH, self.CARD_HEIGHT), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle(
                    [(0, 0), (self.CARD_WIDTH, self.CARD_HEIGHT)],
                    radius=self.CARD_RADIUS,
                    fill=255,
                )

                # 마스크 적용
                result = Image.new("RGBA", card_img.size, (0, 0, 0, 0))
                result.paste(card_img, (0, 0), mask)

                # 골드 테두리 추가
                draw = ImageDraw.Draw(result)
                draw.rounded_rectangle(
                    [(5, 5), (self.CARD_WIDTH - 5, self.CARD_HEIGHT - 5)],
                    radius=self.CARD_RADIUS - 2,
                    outline=self.DARK_GOLD,
                    width=5,
                )
                draw.rounded_rectangle(
                    [(10, 10), (self.CARD_WIDTH - 10, self.CARD_HEIGHT - 10)],
                    radius=self.CARD_RADIUS - 5,
                    outline=self.METALLIC_GOLD,
                    width=3,
                )
                draw.rounded_rectangle(
                    [(14, 14), (self.CARD_WIDTH - 14, self.CARD_HEIGHT - 14)],
                    radius=self.CARD_RADIUS - 7,
                    outline=self.PLATINUM,
                    width=1,
                )

                # 광택 효과
                gloss = Image.new("RGBA", result.size, (0, 0, 0, 0))
                gloss_draw = ImageDraw.Draw(gloss)
                gloss_draw.ellipse(
                    [
                        (-self.CARD_WIDTH * 0.3, -self.CARD_HEIGHT * 0.4),
                        (self.CARD_WIDTH * 0.7, self.CARD_HEIGHT * 0.3),
                    ],
                    fill=(255, 255, 255, 40),
                )
                gloss = gloss.filter(ImageFilter.GaussianBlur(radius=60))
                result = Image.alpha_composite(result, gloss)
                # 광택이 둥근 모서리 바깥(투명 영역)에 번지지 않도록 다시 잘라냄
                result.putalpha(ImageChops.multiply(result.getchannel("A"), mask))

                return result

            except Exception:
                # 에러 발생 시 None 반환하여 폴백 렌더링 사용
                return None

        return None

    def _create_corner_index(
        self, rank: str, suit_symbol: str, color: Tuple
    ) -> Image.Image:
        """코너 인덱스 (랭크 + 무늬)"""
        corner = Image.new("RGBA", (90, 130), (0, 0, 0, 0))
        draw = ImageDraw.Draw(corner)

        # 랭크
        draw.text((10, 5), rank, fill=color, font=self.font_rank_small)

        # 무늬
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_small)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (45 - text_width // 2, 70),
            suit_symbol,
            fill=color,
            font=self.font_suit_small,
        )

        return corner

    def _draw_face_king(
        self, suit: str, color: Tuple, glow_color: Tuple
    ) -> Image.Image:
        """킹 카드 중앙 그림"""
        center = Image.new("RGBA", (200, 260), (0, 0, 0, 0))
        draw = ImageDraw.Draw(center)

        suit_symbol = self.SUIT_SYMBOLS[suit]

        # 배경 실루엣 (왕관 모양)
        crown_points = [
            (100, 30),  # 정점
            (120, 50),
            (110, 50),
            (120, 70),
            (100, 60),
            (80, 70),
            (90, 50),
            (80, 50),
        ]
        draw.polygon(crown_points, fill=glow_color + (60,), outline=color, width=3)

        # 큰 'K' 문자
        bbox = draw.textbbox((0, 0), "K", font=self.font_face_letter)
        text_width = bbox[2] - bbox[0]
        x = (200 - text_width) // 2
        y = 90

        # 그림자
        for offset in [(4, 4), (3, 3), (2, 2)]:
            draw.text(
                (x + offset[0], y + offset[1]),
                "K",
                fill=(0, 0, 0, 80),
                font=self.font_face_letter,
            )

        # 메인 'K'
        draw.text((x, y), "K", fill=color, font=self.font_face_letter)

        # 하단 심볼
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_medium)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (100 - text_width // 2, 210),
            suit_symbol,
            fill=color,
            font=self.font_suit_medium,
        )

        return center

    def _draw_face_queen(
        self, suit: str, color: Tuple, glow_color: Tuple
    ) -> Image.Image:
        """퀸 카드 중앙 그림"""
        center = Image.new("RGBA", (200, 260), (0, 0, 0, 0))
        draw = ImageDraw.Draw(center)

        suit_symbol = self.SUIT_SYMBOLS[suit]

        # 배경 하트 (여왕 상징)
        heart_center = (100, 50)
        draw.ellipse(
            [
                (heart_center[0] - 25, heart_center[1] - 15),
                (heart_center[0] + 25, heart_center[1] + 15),
            ],
            fill=glow_color + (60,),
            outline=color,
            width=2,
        )

        # 큰 'Q' 문자
        bbox = draw.textbbox((0, 0), "Q", font=self.font_face_letter)
        text_width = bbox[2] - bbox[0]
        x = (200 - text_width) // 2
        y = 90

        # 그림자
        for offset in [(4, 4), (3, 3), (2, 2)]:
            draw.text(
                (x + offset[0], y + offset[1]),
                "Q",
                fill=(0, 0, 0, 80),
                font=self.font_face_letter,
            )

        # 메인 'Q'
        draw.text((x, y), "Q", fill=color, font=self.font_face_letter)

        # 하단 심볼
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_medium)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (100 - text_width // 2, 210),
            suit_symbol,
            fill=color,
            font=self.font_suit_medium,
        )

        return center

    def _draw_face_jack(
        self, suit: str, color: Tuple, glow_color: Tuple
    ) -> Image.Image:
        """잭 카드 중앙 그림"""
        center = Image.new("RGBA", (200, 260), (0, 0, 0, 0))
        draw = ImageDraw.Draw(center)

        suit_symbol = self.SUIT_SYMBOLS[suit]

        # 배경 다이아몬드
        diamond_points = [
            (100, 20),
            (120, 50),
            (100, 80),
            (80, 50),
        ]
        draw.polygon(diamond_points, fill=glow_color + (60,), outline=color, width=3)

        # 큰 'J' 문자
        bbox = draw.textbbox((0, 0), "J", font=self.font_face_letter)
        text_width = bbox[2] - bbox[0]
        x = (200 - text_width) // 2
        y = 90

        # 그림자
        for offset in [(4, 4), (3, 3), (2, 2)]:
            draw.text(
                (x + offset[0], y + offset[1]),
                "J",
                fill=(0, 0, 0, 80),
                font=self.font_face_letter,
            )

        # 메인 'J'
        draw.text((x, y), "J", fill=color, font=self.font_face_letter)

        # 하단 심볼
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_medium)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (100 - text_width // 2, 210),
            suit_symbol,
            fill=color,
            font=self.font_suit_medium,
        )

        return center

    def _draw_ace_center(
        self, suit: str, color: Tuple, glow_color: Tuple
    ) -> Image.Image:
        """에이스 중앙 (초대형 심볼)"""
        center = Image.new("RGBA", (200, 280), (0, 0, 0, 0))
        draw = ImageDraw.Draw(center)

        suit_symbol = self.SUIT_SYMBOLS[suit]

        # 글로우 효과
        glow_layer = Image.new("RGBA", center.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.ellipse([(20, 20), (180, 260)], fill=glow_color + (40,))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=40))
        center = Image.alpha_composite(center, glow_layer)

        draw = ImageDraw.Draw(center)

        # 초대형 심볼
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_huge)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (200 - text_width) // 2
        y = (280 - text_height) // 2

        # 깊은 그림자
        for offset in [(6, 6), (4, 4), (2, 2)]:
            draw.text(
                (x + offset[0], y + offset[1]),
                suit_symbol,
                fill=(0, 0, 0, 100),
                font=self.font_suit_huge,
            )

        # 골드 외곽선
        for dx in [-3, -2, -1, 0, 1, 2, 3]:
            for dy in [-3, -2, -1, 0, 1, 2, 3]:
                if dx != 0 or dy != 0:
                    draw.text(
                        (x + dx, y + dy),
                        suit_symbol,
                        fill=self.DARK_GOLD + (80,),
                        font=self.font_suit_huge,
                    )

        # 메인 심볼
        draw.text((x, y), suit_symbol, fill=color, font=self.font_suit_huge)

        # 하이라이트
        draw.text(
            (x - 3, y - 3),
            suit_symbol,
            fill=(255, 255, 255, 60),
            font=self.font_suit_huge,
        )

        return center

    def _draw_number_symbols(self, rank: str, suit: str, color: Tuple) -> Image.Image:
        """숫자 카드 심볼 배치"""
        center = Image.new("RGBA", (180, 260), (0, 0, 0, 0))
        draw = ImageDraw.Draw(center)

        suit_symbol = self.SUIT_SYMBOLS[suit]
        num = int(rank) if rank != "T" else 10

        # 심볼 위치 정의
        positions = {
            2: [(90, 50), (90, 210)],
            3: [(90, 40), (90, 130), (90, 220)],
            4: [(50, 50), (130, 50), (50, 210), (130, 210)],
            5: [(50, 50), (130, 50), (90, 130), (50, 210), (130, 210)],
            6: [(50, 50), (130, 50), (50, 130), (130, 130), (50, 210), (130, 210)],
            7: [
                (50, 40),
                (130, 40),
                (90, 90),
                (50, 140),
                (130, 140),
                (50, 220),
                (130, 220),
            ],
            8: [
                (50, 40),
                (130, 40),
                (90, 80),
                (50, 130),
                (130, 130),
                (90, 180),
                (50, 220),
                (130, 220),
            ],
            9: [
                (50, 40),
                (130, 40),
                (50, 95),
                (130, 95),
                (90, 130),
                (50, 165),
                (130, 165),
                (50, 220),
                (130, 220),
            ],
            10: [
                (50, 30),
                (130, 30),
                (90, 70),
                (50, 110),
                (130, 110),
                (50, 150),
                (130, 150),
                (90, 190),
                (50, 230),
                (130, 230),
            ],
        }

        if num in positions:
            for x, y in positions[num]:
                bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_small)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # 그림자
                draw.text(
                    (x - text_width // 2 + 2, y - text_height // 2 + 2),
                    suit_symbol,
                    fill=(0, 0, 0, 60),
                    font=self.font_suit_small,
                )

                # 메인
                draw.text(
                    (x - text_width // 2, y - text_height // 2),
                    suit_symbol,
                    fill=color,
                    font=self.font_suit_small,
                )

        return center

    def _create_casino_card_front(self, card_str: str) -> Image.Image:
        """카지노급 앞면 카드"""

        # ===  실제 카드 이미지 먼저 시도 ===
        real_card = self._load_real_card_image(card_str)
        if real_card is not None:
            return real_card

        # === 실제 이미지 없으면 그려서 생성 ===
        card = Image.new("RGBA", (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))

        rank = card_str[:-1]
        suit = card_str[-1]
        suit_color = self.SUIT_COLORS.get(suit, (0, 0, 0))
        suit_symbol = self.SUIT_SYMBOLS.get(suit, suit)
        glow_color = self.SUIT_GLOW_COLORS.get(suit, (255, 255, 255))

        # 펄 화이트 베이스
        base = Image.new("RGBA", card.size, (255, 255, 255, 255))

        # 미세 펄 효과
        for y in range(0, self.CARD_HEIGHT, 5):
            alpha = int(15 + 10 * math.sin(y * 0.1))
            draw_base = ImageDraw.Draw(base)
            draw_base.line([(0, y), (self.CARD_WIDTH, y)], fill=(248, 248, 255, alpha))

        # 라운드 마스크
        mask = Image.new("L", card.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [(0, 0), (self.CARD_WIDTH, self.CARD_HEIGHT)],
            radius=self.CARD_RADIUS,
            fill=255,
        )

        result = Image.new("RGBA", card.size, (0, 0, 0, 0))
        result.paste(base, (0, 0), mask)
        card = result

        # 골드 테두리 (3중)
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle(
            [(5, 5), (self.CARD_WIDTH - 5, self.CARD_HEIGHT - 5)],
            radius=self.CARD_RADIUS - 2,
            outline=self.DARK_GOLD,
            width=5,
        )
        draw.rounded_rectangle(
            [(10, 10), (self.CARD_WIDTH - 10, self.CARD_HEIGHT - 10)],
            radius=self.CARD_RADIUS - 5,
            outline=self.METALLIC_GOLD,
            width=3,
        )
        draw.rounded_rectangle(
            [(14, 14), (self.CARD_WIDTH - 14, self.CARD_HEIGHT - 14)],
            radius=self.CARD_RADIUS - 7,
            outline=self.PLATINUM,
            width=1,
        )

        # 코너 인덱스
        corner = self._create_corner_index(rank, suit_symbol, suit_color)
        card.paste(corner, (20, 25), corner)

        # 하단 코너 (회전)
        corner_bottom = corner.rotate(180)
        card.paste(
            corner_bottom,
            (
                self.CARD_WIDTH - corner.width - 20,
                self.CARD_HEIGHT - corner.height - 25,
            ),
            corner_bottom,
        )

        # 중앙 그림
        if rank == "K":
            center = self._draw_face_king(suit, suit_color, glow_color)
        elif rank == "Q":
            center = self._draw_face_queen(suit, suit_color, glow_color)
        elif rank == "J":
            center = self._draw_face_jack(suit, suit_color, glow_color)
        elif rank == "A":
            center = self._draw_ace_center(suit, suit_color, glow_color)
        else:
            center = self._draw_number_symbols(rank, suit, suit_color)

        # 중앙 배치
        center_x = (self.CARD_WIDTH - center.width) // 2
        center_y = (self.CARD_HEIGHT - center.height) // 2
        card.paste(center, (center_x, center_y), center)

        # 최종 광택
        gloss = Image.new("RGBA", card.size, (0, 0, 0, 0))
        gloss_draw = ImageDraw.Draw(gloss)
        gloss_draw.ellipse(
            [
                (-self.CARD_WIDTH * 0.3, -self.CARD_HEIGHT * 0.4),
                (self.CARD_WIDTH * 0.7, self.CARD_HEIGHT * 0.3),
            ],
            fill=(255, 255, 255, 50),
        )
        gloss = gloss.filter(ImageFilter.GaussianBlur(radius=60))
        card = Image.alpha_composite(card, gloss)

        return card

    def _create_casino_card_back(self) -> Image.Image:
        """카지노급 뒷면 (assets/cards/back.png가 있으면 사용, 없으면 직접 그림)"""
        return self._load_card_back() or self._draw_card_back()

    def _rounded_card_mask(self) -> Image.Image:
        """카드 크기 라운드 코너 마스크"""
        mask = Image.new("L", (self.CARD_WIDTH, self.CARD_HEIGHT), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [(0, 0), (self.CARD_WIDTH, self.CARD_HEIGHT)],
            radius=self.CARD_RADIUS,
            fill=255,
        )
        return mask

    def _draw_gold_border(self, card: Image.Image) -> None:
        """카드 뒷면 골드 테두리 (제자리 그리기)"""
        draw = ImageDraw.Draw(card)
        for i in range(4):
            offset = 5 + i * 4
            draw.rounded_rectangle(
                [
                    (offset, offset),
                    (self.CARD_WIDTH - offset, self.CARD_HEIGHT - offset),
                ],
                radius=self.CARD_RADIUS - i * 2,
                outline=self.METALLIC_GOLD + (255 - i * 40,),
                width=3,
            )

    def _load_card_back(self) -> Optional[Image.Image]:
        """실제 뒷면 이미지 로드 (없거나 읽기 실패 시 None)"""
        back_path = self.cards_dir / "back.png"
        if not back_path.exists():
            return None
        try:
            card_img = Image.open(back_path).convert("RGBA")
        except OSError as e:
            logger.warning(f"뒷면 이미지 로드 실패: {e}")
            return None
        card_img = card_img.resize((self.CARD_WIDTH, self.CARD_HEIGHT), Image.LANCZOS)

        result = Image.new("RGBA", card_img.size, (0, 0, 0, 0))
        result.paste(card_img, (0, 0), self._rounded_card_mask())
        self._draw_gold_border(result)
        return result

    def _draw_card_back(self) -> Image.Image:
        """뒷면 직접 그리기 — 다크 그라데이션 + 다이아몬드 패턴 + 골드 테두리 + JP 로고"""
        size = (self.CARD_WIDTH, self.CARD_HEIGHT)

        # 다크 그라데이션
        base = Image.new("RGBA", size, (0, 0, 0, 0))
        draw_base = ImageDraw.Draw(base)
        for y in range(self.CARD_HEIGHT):
            ratio = y / self.CARD_HEIGHT
            r = int(10 + (30 * ratio))
            g = int(10 + (40 * ratio))
            b = int(50 + (70 * ratio))
            draw_base.line([(0, y), (self.CARD_WIDTH, y)], fill=(r, g, b, 255))

        card = Image.new("RGBA", size, (0, 0, 0, 0))
        card.paste(base, (0, 0), self._rounded_card_mask())

        # 다이아몬드 패턴
        pattern = Image.new("RGBA", size, (0, 0, 0, 0))
        pattern_draw = ImageDraw.Draw(pattern)
        spacing = 40
        for y in range(0, self.CARD_HEIGHT + spacing, spacing):
            for x in range(0, self.CARD_WIDTH + spacing, spacing):
                points = [(x, y - 10), (x + 10, y), (x, y + 10), (x - 10, y)]
                pattern_draw.polygon(
                    points, outline=self.METALLIC_GOLD + (100,), width=2
                )
        card = Image.alpha_composite(card, pattern)

        self._draw_gold_border(card)
        return self._add_back_logo(card)

    def _back_logo_font(self) -> ImageFont.FreeTypeFont:
        """뒷면 JP 로고 폰트 (macOS Helvetica, 없으면 기본 랭크 폰트)"""
        try:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 70)
        except OSError:
            return self.font_rank_large

    def _add_back_logo(self, card: Image.Image) -> Image.Image:
        """뒷면 중앙 원형 엠블럼 + JP 로고"""
        center_x = self.CARD_WIDTH // 2
        center_y = self.CARD_HEIGHT // 2

        logo_bg = Image.new("RGBA", card.size, (0, 0, 0, 0))
        logo_draw = ImageDraw.Draw(logo_bg)
        logo_draw.ellipse(
            [(center_x - 90, center_y - 90), (center_x + 90, center_y + 90)],
            fill=(20, 20, 40, 230),
            outline=self.METALLIC_GOLD,
            width=6,
        )
        logo_draw.ellipse(
            [(center_x - 80, center_y - 80), (center_x + 80, center_y + 80)],
            outline=self.PLATINUM,
            width=2,
        )
        card = Image.alpha_composite(card, logo_bg)

        logo_font = self._back_logo_font()
        text_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        text_pos = (center_x - 35, center_y - 40)
        # 그림자
        for dx, dy in [(4, 4), (3, 3), (2, 2)]:
            text_draw.text(
                (text_pos[0] + dx, text_pos[1] + dy),
                "JP",
                fill=(0, 0, 0, 120),
                font=logo_font,
            )
        # 메인 텍스트
        text_draw.text(text_pos, "JP", fill=self.METALLIC_GOLD, font=logo_font)

        return Image.alpha_composite(card, text_layer)

    def _create_velvet_background(self, width: int, height: int) -> Image.Image:
        """모던 그라데이션 배경 (네온 액센트)"""
        bg = Image.new("RGB", (width, height), self.theme.colors.background)

        if self.theme.has_gradient:
            draw = ImageDraw.Draw(bg)
            start = self.theme.colors.background
            end = self.theme.colors.table_color

            # 부드러운 그라데이션
            for y in range(height):
                ratio = y / height
                smooth_ratio = ratio * ratio * (3 - 2 * ratio)
                r = int(start[0] * (1 - smooth_ratio) + end[0] * smooth_ratio)
                g = int(start[1] * (1 - smooth_ratio) + end[1] * smooth_ratio)
                b = int(start[2] * (1 - smooth_ratio) + end[2] * smooth_ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # 미묘한 노이즈 패턴 (모던한 텍스처)
            import random

            noise = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            noise_draw = ImageDraw.Draw(noise)
            for _ in range(500):
                x = random.randint(0, width)
                y = random.randint(0, height)
                size = random.randint(1, 3)
                alpha = random.randint(5, 20)
                noise_draw.ellipse(
                    [(x, y), (x + size, y + size)], fill=(255, 255, 255, alpha)
                )
            bg = bg.convert("RGBA")
            bg = Image.alpha_composite(bg, noise)

        return bg.convert("RGBA")

    # ── 다른 렌더러(멀티 테이블)에서 재사용하는 공개 API ─────────────

    def card_image(self, card_str: str, face_down: bool = False) -> Image.Image:
        """카드 한 장 이미지 (CARD_WIDTH × CARD_HEIGHT, RGBA)"""
        if face_down:
            return self._create_casino_card_back()
        return self._create_casino_card_front(card_str)

    def background(self, width: int, height: int) -> Image.Image:
        """테마 배경 (RGBA)"""
        return self._create_velvet_background(width, height)

    def scaled_card(self, card_str: str, face_down: bool, scale: float) -> Image.Image:
        """축소한 카드 이미지 (카드·크기별 캐시 — 붙여넣기만 하고 수정하지 말 것)"""
        key = (card_str, face_down, scale)
        if key not in self._scaled_cache:
            image = self.card_image(card_str, face_down=face_down)
            size = (int(image.width * scale), int(image.height * scale))
            self._scaled_cache[key] = image.resize(size, Image.LANCZOS)
        return self._scaled_cache[key]

    def scaled_card_size(self, scale: float) -> Tuple[int, int]:
        """scaled_card가 돌려주는 카드 크기"""
        return int(self.CARD_WIDTH * scale), int(self.CARD_HEIGHT * scale)


_casino_renderers = {}


def get_casino_renderer(theme: Optional[Theme] = None) -> CasinoCardRenderer:
    """카지노 렌더러 가져오기"""
    theme_name = theme.name if theme else "Classic"

    if theme_name not in _casino_renderers:
        _casino_renderers[theme_name] = CasinoCardRenderer(theme)

    return _casino_renderers[theme_name]
