"""
JackPy - 프리미엄 카드 렌더러
아름답고 고급스러운 카드 디자인
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Optional, Tuple
import io
from pathlib import Path
from bot.utils.themes import Theme, ThemeManager


class PremiumCardRenderer:
    """
    프리미엄 카드 렌더러

    고급스럽고 현대적인 카드 디자인:
    - 3D 효과
    - 광택 효과
    - 그라데이션 배경
    - 정교한 테두리
    - 부드러운 그림자
    """

    # 카드 크기
    CARD_WIDTH = 200
    CARD_HEIGHT = 300
    CARD_SPACING = 30
    CARD_RADIUS = 20

    # 무늬 색상 (더 선명하게)
    SUIT_COLORS = {
        "S": (0, 0, 0),  # 스페이드 - 블랙
        "C": (0, 0, 0),  # 클로버 - 블랙
        "H": (220, 20, 60),  # 하트 - 크림슨
        "D": (255, 69, 0),  # 다이아몬드 - 오렌지레드
    }

    # 무늬 유니코드
    SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}

    # 랭크 표시명
    RANK_NAMES = {
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

    def __init__(self, theme: Optional[Theme] = None):
        """
        초기화

        Args:
            theme: 테마 (None이면 클래식 테마)
        """
        self.theme = theme or ThemeManager.CLASSIC
        self._load_fonts()

    def _load_fonts(self):
        """폰트 로드"""
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

        loaded = False
        for font_path in font_paths:
            try:
                if Path(font_path).exists():
                    self.font_rank = ImageFont.truetype(font_path, 50)
                    self.font_rank_small = ImageFont.truetype(font_path, 35)
                    self.font_suit = ImageFont.truetype(font_path, 120)
                    self.font_title = ImageFont.truetype(font_path, 52)
                    self.font_value = ImageFont.truetype(font_path, 45)
                    self.font_message = ImageFont.truetype(font_path, 36)
                    loaded = True
                    break
            except Exception:
                continue

        if not loaded:
            # 폴백
            self.font_rank = ImageFont.load_default()
            self.font_rank_small = ImageFont.load_default()
            self.font_suit = ImageFont.load_default()
            self.font_title = ImageFont.load_default()
            self.font_value = ImageFont.load_default()
            self.font_message = ImageFont.load_default()

    def _create_glossy_card(self, card_str: str) -> Image.Image:
        """
        광택 효과가 있는 고급 카드 생성

        Args:
            card_str: 카드 문자열 (예: "AS", "KH")

        Returns:
            PIL Image 객체
        """
        # 카드 베이스
        card = Image.new("RGBA", (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))

        # 그림자 레이어
        shadow = Image.new(
            "RGBA", (self.CARD_WIDTH + 20, self.CARD_HEIGHT + 20), (0, 0, 0, 0)
        )
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            [(10, 10), (self.CARD_WIDTH + 10, self.CARD_HEIGHT + 10)],
            radius=self.CARD_RADIUS,
            fill=(0, 0, 0, 120),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))

        # 카드 본체 (그라데이션 화이트)
        draw = ImageDraw.Draw(card)

        # 베이스 카드
        draw.rounded_rectangle(
            [(0, 0), (self.CARD_WIDTH, self.CARD_HEIGHT)],
            radius=self.CARD_RADIUS,
            fill=(255, 255, 255, 255),
        )

        # 골드 테두리 (다중)
        for i in range(3):
            draw.rounded_rectangle(
                [(i * 2, i * 2), (self.CARD_WIDTH - i * 2, self.CARD_HEIGHT - i * 2)],
                radius=self.CARD_RADIUS - i,
                outline=(218, 165, 32, 255 - i * 50),
                width=2,
            )

        # 카드 정보
        rank = card_str[:-1]
        suit = card_str[-1]
        color = self.SUIT_COLORS.get(suit, (0, 0, 0))
        suit_symbol = self.SUIT_SYMBOLS.get(suit, suit)
        rank_display = self.RANK_NAMES.get(rank, rank)

        # 좌상단 랭크
        draw.text((15, 10), rank_display, fill=color, font=self.font_rank)

        # 좌상단 작은 무늬
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_rank_small)
        draw.text((15, 65), suit_symbol, fill=color, font=self.font_rank_small)

        # 중앙 큰 무늬 (3D 효과)
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.CARD_WIDTH - text_width) // 2
        y = (self.CARD_HEIGHT - text_height) // 2 - 10

        # 그림자 효과 (무늬)
        for offset in [(2, 2), (1, 1)]:
            shadow_color = tuple([c // 3 for c in color])
            draw.text(
                (x + offset[0], y + offset[1]),
                suit_symbol,
                fill=shadow_color + (100,),
                font=self.font_suit,
            )

        # 실제 무늬
        draw.text((x, y), suit_symbol, fill=color, font=self.font_suit)

        # 우하단 랭크 (거꾸로)
        rotated_text = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        rotated_draw = ImageDraw.Draw(rotated_text)
        rotated_draw.text((0, 0), rank_display, fill=color, font=self.font_rank)
        rotated_text = rotated_text.rotate(180, expand=False)
        card.paste(
            rotated_text, (self.CARD_WIDTH - 75, self.CARD_HEIGHT - 70), rotated_text
        )

        # 우하단 작은 무늬 (거꾸로)
        rotated_suit = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        rotated_draw = ImageDraw.Draw(rotated_suit)
        rotated_draw.text((0, 0), suit_symbol, fill=color, font=self.font_rank_small)
        rotated_suit = rotated_suit.rotate(180, expand=False)
        card.paste(
            rotated_suit, (self.CARD_WIDTH - 75, self.CARD_HEIGHT - 125), rotated_suit
        )

        # 광택 효과 (좌상단 하이라이트)
        highlight = Image.new("RGBA", (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))
        highlight_draw = ImageDraw.Draw(highlight)

        # 대각선 그라데이션 하이라이트
        for i in range(100):
            alpha = int(30 * (1 - i / 100))
            highlight_draw.rounded_rectangle(
                [(0, 0), (self.CARD_WIDTH - i * 2, self.CARD_HEIGHT - i * 2)],
                radius=self.CARD_RADIUS,
                fill=(255, 255, 255, alpha),
            )

        card = Image.alpha_composite(card, highlight)

        return card

    def _create_card_back(self) -> Image.Image:
        """
        고급스러운 카드 뒷면 생성

        Returns:
            PIL Image 객체
        """
        card = Image.new("RGBA", (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)

        # 그라데이션 배경 (남색 -> 보라색)
        for y in range(self.CARD_HEIGHT):
            ratio = y / self.CARD_HEIGHT
            r = int(20 + (80 * ratio))
            g = int(30 + (20 * ratio))
            b = int(100 + (50 * ratio))
            draw.line([(0, y), (self.CARD_WIDTH, y)], fill=(r, g, b))

        # 라운드 마스크 적용
        mask = Image.new("L", (self.CARD_WIDTH, self.CARD_HEIGHT), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [(0, 0), (self.CARD_WIDTH, self.CARD_HEIGHT)],
            radius=self.CARD_RADIUS,
            fill=255,
        )

        result = Image.new("RGBA", (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))
        result.paste(card, (0, 0), mask)
        card = result

        draw = ImageDraw.Draw(card)

        # 골드 테두리
        for i in range(3):
            draw.rounded_rectangle(
                [(i * 2, i * 2), (self.CARD_WIDTH - i * 2, self.CARD_HEIGHT - i * 2)],
                radius=self.CARD_RADIUS - i,
                outline=(218, 165, 32, 255 - i * 50),
                width=2,
            )

        # 다이아몬드 패턴
        spacing = 30
        for x in range(0, self.CARD_WIDTH, spacing):
            for y in range(0, self.CARD_HEIGHT, spacing):
                points = [
                    (x + spacing // 2, y),
                    (x + spacing, y + spacing // 2),
                    (x + spacing // 2, y + spacing),
                    (x, y + spacing // 2),
                ]
                draw.polygon(points, outline=(255, 215, 0, 100), width=1)

        # 중앙 로고 영역
        center_x = self.CARD_WIDTH // 2
        center_y = self.CARD_HEIGHT // 2

        # 중앙 원
        draw.ellipse(
            [(center_x - 50, center_y - 50), (center_x + 50, center_y + 50)],
            fill=(30, 40, 120, 200),
            outline=(218, 165, 32, 255),
            width=3,
        )

        # "JP" 텍스트
        try:
            logo_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
        except:
            logo_font = self.font_rank

        bbox = draw.textbbox((0, 0), "JP", font=logo_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text(
            (center_x - text_width // 2, center_y - text_height // 2),
            "JP",
            fill=(255, 215, 0),
            font=logo_font,
        )

        return card

    def _add_premium_shadow(self, card: Image.Image) -> Image.Image:
        """
        프리미엄 그림자 효과

        Args:
            card: 카드 이미지

        Returns:
            그림자가 추가된 카드
        """
        shadow_offset = 12
        shadow = Image.new(
            "RGBA",
            (card.width + shadow_offset * 2, card.height + shadow_offset * 2),
            (0, 0, 0, 0),
        )

        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            [
                (shadow_offset, shadow_offset),
                (card.width + shadow_offset, card.height + shadow_offset),
            ],
            radius=self.CARD_RADIUS,
            fill=(0, 0, 0, 150),
        )

        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
        shadow.paste(card, (0, 0), card)

        return shadow

    def _create_game_background(self, width: int, height: int) -> Image.Image:
        """
        고급스러운 게임 배경

        Args:
            width: 배경 너비
            height: 배경 높이

        Returns:
            배경 이미지
        """
        bg = Image.new("RGB", (width, height), self.theme.colors.background)

        if self.theme.has_gradient:
            draw = ImageDraw.Draw(bg)
            start = self.theme.colors.background
            end = self.theme.colors.table_color

            for y in range(height):
                ratio = y / height
                r = int(start[0] * (1 - ratio) + end[0] * ratio)
                g = int(start[1] * (1 - ratio) + end[1] * ratio)
                b = int(start[2] * (1 - ratio) + end[2] * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 미묘한 패턴 추가
        draw = ImageDraw.Draw(bg, "RGBA")
        for x in range(0, width, 100):
            for y in range(0, height, 100):
                draw.ellipse([(x, y), (x + 50, y + 50)], fill=(255, 255, 255, 5))

        return bg

    def generate_game_image(
        self,
        player_hand: List[str],
        dealer_hand: List[str],
        player_value: int,
        dealer_value: Optional[int] = None,
        hide_dealer_first: bool = True,
        message: str = "",
    ) -> bytes:
        """
        프리미엄 게임 이미지 생성

        Args:
            player_hand: 플레이어 카드
            dealer_hand: 딜러 카드
            player_value: 플레이어 값
            dealer_value: 딜러 값
            hide_dealer_first: 딜러 첫 카드 숨김
            message: 메시지

        Returns:
            PNG 이미지 바이트
        """
        max_cards = max(len(player_hand), len(dealer_hand))
        card_shadow_size = 24

        card_area_width = (
            max_cards * (self.CARD_WIDTH + card_shadow_size)
            + (max_cards - 1) * self.CARD_SPACING
            + 100
        )

        total_width = max(card_area_width, 900)
        section_height = self.CARD_HEIGHT + card_shadow_size + 200
        total_height = section_height * 2 + 250

        # 배경
        image = self._create_game_background(total_width, total_height)
        image = image.convert("RGBA")
        draw = ImageDraw.Draw(image)

        # 고급스러운 테두리
        border_gradient = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border_gradient)

        for i in range(8):
            alpha = 255 - i * 30
            border_draw.rectangle(
                [
                    (10 + i * 2, 10 + i * 2),
                    (total_width - 10 - i * 2, total_height - 10 - i * 2),
                ],
                outline=self.theme.colors.border_color + (alpha,),
                width=2,
            )

        image = Image.alpha_composite(image, border_gradient)
        draw = ImageDraw.Draw(image)

        # === 딜러 섹션 ===
        y_offset = 50

        # 딜러 라벨 배경
        label_bg = Image.new("RGBA", (250, 70), (0, 0, 0, 0))
        label_draw = ImageDraw.Draw(label_bg)
        label_draw.rounded_rectangle(
            [(0, 0), (250, 70)],
            radius=15,
            fill=self.theme.colors.accent_color + (50,),
            outline=self.theme.colors.accent_color,
            width=2,
        )
        image.paste(label_bg, (50, y_offset), label_bg)

        draw.text(
            (60, y_offset + 10),
            "🤖 딜러",
            fill=self.theme.colors.text_color,
            font=self.font_title,
        )
        y_offset += 100

        # 딜러 카드
        x_offset = 50
        for i, card_str in enumerate(dealer_hand):
            if i == 0 and hide_dealer_first:
                card = self._create_card_back()
            else:
                card = self._create_glossy_card(card_str)

            card_with_shadow = self._add_premium_shadow(card)
            image.paste(card_with_shadow, (x_offset, y_offset), card_with_shadow)
            x_offset += self.CARD_WIDTH + card_shadow_size + self.CARD_SPACING

        # 딜러 값
        if dealer_value is not None:
            value_bg = Image.new("RGBA", (150, 60), (0, 0, 0, 0))
            value_draw = ImageDraw.Draw(value_bg)
            value_draw.rounded_rectangle(
                [(0, 0), (150, 60)],
                radius=10,
                fill=(0, 0, 0, 150),
                outline=self.theme.colors.accent_color,
                width=2,
            )
            image.paste(value_bg, (x_offset + 20, y_offset + 120), value_bg)

            draw.text(
                (x_offset + 40, y_offset + 125),
                f"합: {dealer_value}",
                fill=self.theme.colors.accent_color,
                font=self.font_value,
            )

        # === 플레이어 섹션 ===
        y_offset += section_height

        # 플레이어 라벨 배경
        label_bg = Image.new("RGBA", (280, 70), (0, 0, 0, 0))
        label_draw = ImageDraw.Draw(label_bg)
        label_draw.rounded_rectangle(
            [(0, 0), (280, 70)],
            radius=15,
            fill=self.theme.colors.accent_color + (50,),
            outline=self.theme.colors.accent_color,
            width=2,
        )
        image.paste(label_bg, (50, y_offset), label_bg)

        draw.text(
            (60, y_offset + 10),
            "🎯 플레이어",
            fill=self.theme.colors.text_color,
            font=self.font_title,
        )
        y_offset += 100

        # 플레이어 카드
        x_offset = 50
        for card_str in player_hand:
            card = self._create_glossy_card(card_str)
            card_with_shadow = self._add_premium_shadow(card)
            image.paste(card_with_shadow, (x_offset, y_offset), card_with_shadow)
            x_offset += self.CARD_WIDTH + card_shadow_size + self.CARD_SPACING

        # 플레이어 값
        value_bg = Image.new("RGBA", (150, 60), (0, 0, 0, 0))
        value_draw = ImageDraw.Draw(value_bg)
        value_draw.rounded_rectangle(
            [(0, 0), (150, 60)],
            radius=10,
            fill=(0, 0, 0, 150),
            outline=self.theme.colors.accent_color,
            width=2,
        )
        image.paste(value_bg, (x_offset + 20, y_offset + 120), value_bg)

        draw.text(
            (x_offset + 40, y_offset + 125),
            f"합: {player_value}",
            fill=self.theme.colors.accent_color,
            font=self.font_value,
        )

        # === 메시지 ===
        if message:
            y_offset += self.CARD_HEIGHT + card_shadow_size + 50

            # 메시지 배경
            lines = message.split("\n")
            msg_height = len(lines) * 45 + 20
            msg_bg = Image.new("RGBA", (total_width - 100, msg_height), (0, 0, 0, 0))
            msg_draw = ImageDraw.Draw(msg_bg)
            msg_draw.rounded_rectangle(
                [(0, 0), (total_width - 100, msg_height)],
                radius=15,
                fill=(0, 0, 0, 180),
                outline=self.theme.colors.border_color,
                width=2,
            )
            image.paste(msg_bg, (50, y_offset), msg_bg)

            for i, line in enumerate(lines):
                draw.text(
                    (70, y_offset + 10 + i * 45),
                    line,
                    fill=self.theme.colors.text_color,
                    font=self.font_message,
                )

        # 이미지를 바이트로 변환
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG", quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()


# 전역 인스턴스
_premium_renderers = {}


def get_premium_renderer(theme: Optional[Theme] = None) -> PremiumCardRenderer:
    """
    프리미엄 렌더러 가져오기

    Args:
        theme: 테마

    Returns:
        PremiumCardRenderer 인스턴스
    """
    theme_name = theme.name if theme else "Classic"

    if theme_name not in _premium_renderers:
        _premium_renderers[theme_name] = PremiumCardRenderer(theme)

    return _premium_renderers[theme_name]
