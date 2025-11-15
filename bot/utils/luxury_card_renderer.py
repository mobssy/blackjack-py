"""
JackPy - 럭셔리 카드 렌더러
라스베가스 카지노급 고급 디자인
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from typing import List, Optional, Tuple
import io
from pathlib import Path
from bot.utils.themes import Theme, ThemeManager
import math


class LuxuryCardRenderer:
    """
    럭셔리 카드 렌더러

    특징:
    - 3D 입체 효과
    - 메탈릭 골드 테두리
    - 글래스모피즘 (유리 질감)
    - 네온 글로우 효과
    - 홀로그램 반짝임
    - 다이아몬드 패턴
    """

    # 카드 크기 (더 크게)
    CARD_WIDTH = 220
    CARD_HEIGHT = 320
    CARD_SPACING = 35
    CARD_RADIUS = 25

    # 고급 색상 팔레트
    METALLIC_GOLD = (255, 215, 0)
    DARK_GOLD = (184, 134, 11)
    PLATINUM = (229, 228, 226)
    OBSIDIAN = (15, 15, 20)

    # 무늬 색상 (더 선명하고 풍부하게)
    SUIT_COLORS = {
        'S': (20, 20, 20),        # 블랙
        'C': (25, 25, 25),        # 블랙
        'H': (220, 20, 60),       # 크림슨
        'D': (255, 85, 0),        # 다이아몬드 오렌지
    }

    # 무늬별 강조 색상
    SUIT_GLOW_COLORS = {
        'S': (100, 100, 255),     # 블루 글로우
        'C': (50, 255, 50),       # 그린 글로우
        'H': (255, 50, 100),      # 핑크 글로우
        'D': (255, 200, 50),      # 골드 글로우
    }

    SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}

    RANK_DISPLAY = {
        'A': 'A', '2': '2', '3': '3', '4': '4', '5': '5',
        '6': '6', '7': '7', '8': '8', '9': '9', 'T': '10',
        'J': 'J', 'Q': 'Q', 'K': 'K'
    }

    def __init__(self, theme: Optional[Theme] = None):
        """초기화"""
        self.theme = theme or ThemeManager.CLASSIC
        self._load_fonts()

    def _load_fonts(self):
        """폰트 로드"""
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]

        for font_path in font_paths:
            try:
                if Path(font_path).exists():
                    self.font_rank = ImageFont.truetype(font_path, 60)
                    self.font_suit_large = ImageFont.truetype(font_path, 140)
                    self.font_suit_small = ImageFont.truetype(font_path, 50)
                    self.font_title = ImageFont.truetype(font_path, 58)
                    self.font_value = ImageFont.truetype(font_path, 48)
                    self.font_message = ImageFont.truetype(font_path, 38)
                    break
            except Exception:
                continue
        else:
            # 폴백
            default = ImageFont.load_default()
            self.font_rank = default
            self.font_suit_large = default
            self.font_suit_small = default
            self.font_title = default
            self.font_value = default
            self.font_message = default

    def _create_holographic_pattern(self, width: int, height: int) -> Image.Image:
        """홀로그램 반짝임 패턴"""
        pattern = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pattern)

        # 대각선 홀로그램 라인
        colors = [
            (255, 100, 200, 40),
            (100, 200, 255, 40),
            (200, 255, 100, 40),
            (255, 200, 100, 40),
        ]

        spacing = 15
        for i, x in enumerate(range(-height, width, spacing)):
            color = colors[i % len(colors)]
            draw.line([(x, 0), (x + height, height)], fill=color, width=3)

        return pattern.filter(ImageFilter.GaussianBlur(radius=1.5))

    def _create_diamond_pattern(self, width: int, height: int, color: Tuple) -> Image.Image:
        """다이아몬드 패턴"""
        pattern = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pattern)

        spacing = 40
        for y in range(0, height + spacing, spacing):
            for x in range(0, width + spacing, spacing):
                # 다이아몬드 모양
                points = [
                    (x, y - 10),
                    (x + 10, y),
                    (x, y + 10),
                    (x - 10, y)
                ]
                draw.polygon(points, outline=color, width=1)

        return pattern

    def _create_metallic_gradient(
        self,
        size: Tuple[int, int],
        base_color: Tuple[int, int, int]
    ) -> Image.Image:
        """메탈릭 그라데이션"""
        width, height = size
        gradient = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)

        for y in range(height):
            # 메탈릭 효과를 위한 복잡한 그라데이션
            ratio = y / height
            wave = math.sin(ratio * math.pi * 3) * 0.2 + 0.8

            r = int(base_color[0] * wave)
            g = int(base_color[1] * wave)
            b = int(base_color[2] * wave)

            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        return gradient

    def _create_luxury_card_front(self, card_str: str) -> Image.Image:
        """럭셔리 앞면 카드"""
        card = Image.new('RGBA', (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))

        rank = card_str[:-1]
        suit = card_str[-1]
        rank_display = self.RANK_DISPLAY.get(rank, rank)
        suit_color = self.SUIT_COLORS.get(suit, (0, 0, 0))
        suit_symbol = self.SUIT_SYMBOLS.get(suit, suit)
        glow_color = self.SUIT_GLOW_COLORS.get(suit, (255, 255, 255))

        # === 베이스: 펄 화이트 그라데이션 ===
        base = Image.new('RGBA', card.size, (255, 255, 255, 255))

        # 미세한 펄 효과
        pearl = Image.new('RGBA', card.size, (0, 0, 0, 0))
        pearl_draw = ImageDraw.Draw(pearl)
        for y in range(0, self.CARD_HEIGHT, 5):
            alpha = int(15 + 10 * math.sin(y * 0.1))
            pearl_draw.line([(0, y), (self.CARD_WIDTH, y)],
                          fill=(248, 248, 255, alpha))

        base = Image.alpha_composite(base, pearl)

        # 라운드 마스크 적용
        mask = Image.new('L', card.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [(0, 0), (self.CARD_WIDTH, self.CARD_HEIGHT)],
            radius=self.CARD_RADIUS,
            fill=255
        )

        result = Image.new('RGBA', card.size, (0, 0, 0, 0))
        result.paste(base, (0, 0), mask)
        card = result

        # === 홀로그램 패턴 ===
        holo = self._create_holographic_pattern(self.CARD_WIDTH, self.CARD_HEIGHT)
        card = Image.alpha_composite(card, holo)

        # === 다이아몬드 패턴 (아주 은은하게) ===
        diamond = self._create_diamond_pattern(
            self.CARD_WIDTH,
            self.CARD_HEIGHT,
            (200, 200, 200, 30)
        )
        card = Image.alpha_composite(card, diamond)

        # === 골드 테두리 (3중) ===
        draw = ImageDraw.Draw(card)

        # 외곽 - 다크 골드
        draw.rounded_rectangle(
            [(4, 4), (self.CARD_WIDTH - 4, self.CARD_HEIGHT - 4)],
            radius=self.CARD_RADIUS - 2,
            outline=self.DARK_GOLD,
            width=4
        )

        # 중간 - 브라이트 골드
        draw.rounded_rectangle(
            [(8, 8), (self.CARD_WIDTH - 8, self.CARD_HEIGHT - 8)],
            radius=self.CARD_RADIUS - 4,
            outline=self.METALLIC_GOLD,
            width=3
        )

        # 내부 - 플래티넘
        draw.rounded_rectangle(
            [(12, 12), (self.CARD_WIDTH - 12, self.CARD_HEIGHT - 12)],
            radius=self.CARD_RADIUS - 6,
            outline=self.PLATINUM,
            width=1
        )

        # === 중앙 무늬 글로우 ===
        glow_layer = Image.new('RGBA', card.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)

        # 큰 글로우
        glow_draw.ellipse(
            [(self.CARD_WIDTH * 0.15, self.CARD_HEIGHT * 0.2),
             (self.CARD_WIDTH * 0.85, self.CARD_HEIGHT * 0.8)],
            fill=glow_color + (30,)
        )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=40))
        card = Image.alpha_composite(card, glow_layer)

        # === 코너 장식 (좌상단) ===
        corner = Image.new('RGBA', (110, 140), (0, 0, 0, 0))
        corner_draw = ImageDraw.Draw(corner)

        # 골드 배경 박스
        corner_draw.rounded_rectangle(
            [(0, 0), (110, 140)],
            radius=20,
            fill=(255, 250, 240, 240),
            outline=self.METALLIC_GOLD,
            width=3
        )

        # 내부 테두리
        corner_draw.rounded_rectangle(
            [(5, 5), (105, 135)],
            radius=17,
            outline=self.DARK_GOLD + (150,),
            width=2
        )

        # 랭크
        corner_draw.text((20, 15), rank_display, fill=suit_color, font=self.font_rank)

        # 작은 무늬
        corner_draw.text((25, 80), suit_symbol, fill=suit_color, font=self.font_suit_small)

        card.paste(corner, (15, 20), corner)

        # === 코너 장식 (우하단, 180도 회전) ===
        corner_rotated = corner.rotate(180)
        card.paste(corner_rotated,
                  (self.CARD_WIDTH - corner.width - 15,
                   self.CARD_HEIGHT - corner.height - 20),
                  corner_rotated)

        # === 중앙 큰 무늬 (입체 효과) ===
        symbol_layer = Image.new('RGBA', card.size, (0, 0, 0, 0))
        symbol_draw = ImageDraw.Draw(symbol_layer)

        # 텍스트 크기 계산
        bbox = symbol_draw.textbbox((0, 0), suit_symbol, font=self.font_suit_large)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.CARD_WIDTH - text_width) // 2
        y = (self.CARD_HEIGHT - text_height) // 2 - 15

        # 깊은 그림자 (3D 효과)
        for offset in [(8, 8), (6, 6), (4, 4), (2, 2)]:
            shadow_alpha = 80 - offset[0] * 10
            symbol_draw.text(
                (x + offset[0], y + offset[1]),
                suit_symbol,
                fill=(0, 0, 0, shadow_alpha),
                font=self.font_suit_large
            )

        # 외곽선 (골드)
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    symbol_draw.text(
                        (x + dx, y + dy),
                        suit_symbol,
                        fill=self.DARK_GOLD + (100,),
                        font=self.font_suit_large
                    )

        # 메인 무늬
        symbol_draw.text((x, y), suit_symbol, fill=suit_color, font=self.font_suit_large)

        # 하이라이트 (입체감)
        symbol_draw.text(
            (x - 2, y - 2),
            suit_symbol,
            fill=(255, 255, 255, 80),
            font=self.font_suit_large
        )

        card = Image.alpha_composite(card, symbol_layer)

        # === 최종 광택 효과 ===
        gloss = Image.new('RGBA', card.size, (0, 0, 0, 0))
        gloss_draw = ImageDraw.Draw(gloss)
        gloss_draw.ellipse(
            [(-self.CARD_WIDTH * 0.3, -self.CARD_HEIGHT * 0.4),
             (self.CARD_WIDTH * 0.7, self.CARD_HEIGHT * 0.3)],
            fill=(255, 255, 255, 60)
        )
        gloss = gloss.filter(ImageFilter.GaussianBlur(radius=50))
        card = Image.alpha_composite(card, gloss)

        return card

    def _create_luxury_card_back(self) -> Image.Image:
        """럭셔리 뒷면 카드"""
        card = Image.new('RGBA', (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))

        # === 베이스: 다크 그라데이션 ===
        base = Image.new('RGBA', card.size, (0, 0, 0, 0))
        draw_base = ImageDraw.Draw(base)

        for y in range(self.CARD_HEIGHT):
            ratio = y / self.CARD_HEIGHT
            # 다크 블루에서 블랙으로
            r = int(10 + (30 * ratio))
            g = int(10 + (40 * ratio))
            b = int(50 + (70 * ratio))
            draw_base.line([(0, y), (self.CARD_WIDTH, y)], fill=(r, g, b, 255))

        # 라운드 마스크
        mask = Image.new('L', card.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [(0, 0), (self.CARD_WIDTH, self.CARD_HEIGHT)],
            radius=self.CARD_RADIUS,
            fill=255
        )

        result = Image.new('RGBA', card.size, (0, 0, 0, 0))
        result.paste(base, (0, 0), mask)
        card = result

        # === 다이아몬드 패턴 (골드) ===
        diamond = self._create_diamond_pattern(
            self.CARD_WIDTH,
            self.CARD_HEIGHT,
            self.METALLIC_GOLD + (120,)
        )
        card = Image.alpha_composite(card, diamond)

        # === 홀로그램 효과 ===
        holo = self._create_holographic_pattern(self.CARD_WIDTH, self.CARD_HEIGHT)
        card = Image.alpha_composite(card, holo)

        # === 골드 테두리 ===
        draw = ImageDraw.Draw(card)

        for i in range(4):
            offset = 4 + i * 3
            draw.rounded_rectangle(
                [(offset, offset),
                 (self.CARD_WIDTH - offset, self.CARD_HEIGHT - offset)],
                radius=self.CARD_RADIUS - i * 2,
                outline=self.METALLIC_GOLD + (255 - i * 40,),
                width=3
            )

        # === 중앙 로고 ===
        center_x = self.CARD_WIDTH // 2
        center_y = self.CARD_HEIGHT // 2

        # 로고 배경 (원형)
        logo_bg = Image.new('RGBA', card.size, (0, 0, 0, 0))
        logo_draw = ImageDraw.Draw(logo_bg)

        # 외부 원 (골드)
        logo_draw.ellipse(
            [(center_x - 80, center_y - 80), (center_x + 80, center_y + 80)],
            fill=(20, 20, 40, 220),
            outline=self.METALLIC_GOLD,
            width=5
        )

        # 내부 원 (플래티넘)
        logo_draw.ellipse(
            [(center_x - 70, center_y - 70), (center_x + 70, center_y + 70)],
            outline=self.PLATINUM,
            width=2
        )

        card = Image.alpha_composite(card, logo_bg)

        # "JP" 텍스트 (골드)
        try:
            logo_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
        except:
            logo_font = self.font_rank

        text_layer = Image.new('RGBA', card.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)

        # 텍스트 그림자
        for offset in [(3, 3), (2, 2), (1, 1)]:
            text_draw.text(
                (center_x - 30 + offset[0], center_y - 35 + offset[1]),
                "JP",
                fill=(0, 0, 0, 100),
                font=logo_font
            )

        # 메인 텍스트
        text_draw.text(
            (center_x - 30, center_y - 35),
            "JP",
            fill=self.METALLIC_GOLD,
            font=logo_font
        )

        card = Image.alpha_composite(card, text_layer)

        return card

    def _add_dramatic_shadow(self, card: Image.Image) -> Image.Image:
        """드라마틱한 그림자"""
        shadow_offset = 15
        shadow_size = (
            card.width + shadow_offset * 2,
            card.height + shadow_offset * 2
        )

        shadow = Image.new('RGBA', shadow_size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)

        # 다층 그림자
        for i in range(3):
            offset = shadow_offset + i * 2
            alpha = 180 - i * 40
            shadow_draw.rounded_rectangle(
                [(offset, offset),
                 (card.width + offset, card.height + offset)],
                radius=self.CARD_RADIUS + 5,
                fill=(0, 0, 0, alpha)
            )

        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
        shadow.paste(card, (0, 0), card)

        return shadow

    def _create_velvet_background(self, width: int, height: int) -> Image.Image:
        """벨벳 질감 배경"""
        bg = Image.new('RGB', (width, height), self.theme.colors.background)

        if self.theme.has_gradient:
            draw = ImageDraw.Draw(bg)
            start = self.theme.colors.background
            end = self.theme.colors.table_color

            for y in range(height):
                ratio = y / height
                # 부드러운 S-커브
                smooth_ratio = ratio * ratio * (3 - 2 * ratio)

                r = int(start[0] * (1 - smooth_ratio) + end[0] * smooth_ratio)
                g = int(start[1] * (1 - smooth_ratio) + end[1] * smooth_ratio)
                b = int(start[2] * (1 - smooth_ratio) + end[2] * smooth_ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 벨벳 질감 노이즈
        noise = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        noise_draw = ImageDraw.Draw(noise)

        import random
        random.seed(42)  # 일관성을 위해
        for _ in range(width * height // 100):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            brightness = random.randint(0, 30)
            noise_draw.point((x, y), fill=(brightness, brightness, brightness, 20))

        bg = bg.convert('RGBA')
        bg = Image.alpha_composite(bg, noise)

        return bg

    def generate_game_image(
        self,
        player_hand: List[str],
        dealer_hand: List[str],
        player_value: int,
        dealer_value: Optional[int] = None,
        hide_dealer_first: bool = True,
        message: str = ""
    ) -> bytes:
        """럭셔리 게임 이미지 생성"""

        message_lines = message.split('\n') if message else []

        # 크기 계산
        max_cards = max(len(player_hand), len(dealer_hand), 1)
        shadow_extra = 30
        card_visual_width = self.CARD_WIDTH + shadow_extra

        card_area_width = (max_cards * card_visual_width +
                          (max_cards - 1) * self.CARD_SPACING + 150)

        total_width = max(card_area_width, 1100)
        section_height = self.CARD_HEIGHT + shadow_extra + 250
        msg_height = len(message_lines) * 50 + 100 if message_lines else 100
        total_height = section_height * 2 + msg_height

        # === 벨벳 배경 ===
        image = self._create_velvet_background(total_width, total_height)
        draw = ImageDraw.Draw(image)

        # === 외곽 골드 프레임 ===
        frame_padding = 25
        for i in range(5):
            offset = frame_padding + i * 4
            alpha = 255 - i * 30
            draw.rounded_rectangle(
                [(offset, offset), (total_width - offset, total_height - offset)],
                radius=40 - i * 2,
                outline=self.METALLIC_GOLD + (alpha,),
                width=3
            )

        # === 딜러 섹션 ===
        dealer_y = 60

        # 섹션 패널
        panel_width = total_width - 120
        panel_height = section_height - 80
        panel = Image.new('RGBA', (panel_width, panel_height), (0, 0, 0, 0))
        panel_draw = ImageDraw.Draw(panel)

        # 글래스모픽 배경
        panel_draw.rounded_rectangle(
            [(0, 0), (panel_width, panel_height)],
            radius=30,
            fill=(255, 255, 255, 25)
        )

        # 골드 테두리
        for i in range(3):
            panel_draw.rounded_rectangle(
                [(i * 3, i * 3), (panel_width - i * 3, panel_height - i * 3)],
                radius=28 - i,
                outline=self.METALLIC_GOLD + (200 - i * 40,),
                width=2
            )

        image.paste(panel, (60, dealer_y), panel)

        # 딜러 라벨
        label_x = 100
        label_y = dealer_y + 30

        # 라벨 배경 (골드)
        label_bg = Image.new('RGBA', (250, 75), (0, 0, 0, 0))
        label_bg_draw = ImageDraw.Draw(label_bg)
        label_bg_draw.rounded_rectangle(
            [(0, 0), (250, 75)],
            radius=20,
            fill=self.DARK_GOLD + (180,),
            outline=self.METALLIC_GOLD,
            width=3
        )
        image.paste(label_bg, (label_x, label_y), label_bg)

        draw.text(
            (label_x + 30, label_y + 15),
            "🤖 딜러",
            fill=(255, 255, 255),
            font=self.font_title
        )

        # 딜러 카드
        cards_y = label_y + 100
        x_offset = 100

        for i, card_str in enumerate(dealer_hand):
            if i == 0 and hide_dealer_first:
                card_img = self._create_luxury_card_back()
            else:
                card_img = self._create_luxury_card_front(card_str)

            card_with_shadow = self._add_dramatic_shadow(card_img)
            image.paste(card_with_shadow, (x_offset, cards_y), card_with_shadow)
            x_offset += card_visual_width + self.CARD_SPACING

        # 딜러 값
        if dealer_value is not None:
            chip = self._create_value_chip(f"합: {dealer_value}")
            chip_x = total_width - chip.width - 120
            chip_y = cards_y + (self.CARD_HEIGHT - chip.height) // 2
            image.paste(chip, (chip_x, chip_y), chip)

        # === 플레이어 섹션 ===
        player_y = dealer_y + section_height

        panel2 = Image.new('RGBA', (panel_width, panel_height), (0, 0, 0, 0))
        panel2_draw = ImageDraw.Draw(panel2)

        panel2_draw.rounded_rectangle(
            [(0, 0), (panel_width, panel_height)],
            radius=30,
            fill=(255, 255, 255, 25)
        )

        for i in range(3):
            panel2_draw.rounded_rectangle(
                [(i * 3, i * 3), (panel_width - i * 3, panel_height - i * 3)],
                radius=28 - i,
                outline=self.METALLIC_GOLD + (200 - i * 40,),
                width=2
            )

        image.paste(panel2, (60, player_y), panel2)

        # 플레이어 라벨
        label_bg2 = Image.new('RGBA', (300, 75), (0, 0, 0, 0))
        label_bg2_draw = ImageDraw.Draw(label_bg2)
        label_bg2_draw.rounded_rectangle(
            [(0, 0), (300, 75)],
            radius=20,
            fill=self.DARK_GOLD + (180,),
            outline=self.METALLIC_GOLD,
            width=3
        )
        image.paste(label_bg2, (label_x, player_y + 30), label_bg2)

        draw.text(
            (label_x + 30, player_y + 45),
            "🎯 플레이어",
            fill=(255, 255, 255),
            font=self.font_title
        )

        # 플레이어 카드
        cards_y = player_y + 135
        x_offset = 100

        for card_str in player_hand:
            card_img = self._create_luxury_card_front(card_str)
            card_with_shadow = self._add_dramatic_shadow(card_img)
            image.paste(card_with_shadow, (x_offset, cards_y), card_with_shadow)
            x_offset += card_visual_width + self.CARD_SPACING

        # 플레이어 값
        chip = self._create_value_chip(f"합: {player_value}")
        chip_x = total_width - chip.width - 120
        chip_y = cards_y + (self.CARD_HEIGHT - chip.height) // 2
        image.paste(chip, (chip_x, chip_y), chip)

        # === 메시지 ===
        if message_lines:
            msg_y = player_y + panel_height + 60
            msg_panel_height = len(message_lines) * 50 + 60

            msg_panel = Image.new('RGBA', (panel_width, msg_panel_height), (0, 0, 0, 0))
            msg_draw = ImageDraw.Draw(msg_panel)

            msg_draw.rounded_rectangle(
                [(0, 0), (panel_width, msg_panel_height)],
                radius=25,
                fill=(0, 0, 0, 200)
            )

            msg_draw.rounded_rectangle(
                [(0, 0), (panel_width, msg_panel_height)],
                radius=25,
                outline=self.METALLIC_GOLD,
                width=3
            )

            for i, line in enumerate(message_lines):
                msg_draw.text(
                    (40, 20 + i * 50),
                    line,
                    fill=(255, 255, 255),
                    font=self.font_message
                )

            image.paste(msg_panel, (60, msg_y), msg_panel)

        # 바이트 변환
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG', quality=98)
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    def _create_value_chip(self, text: str) -> Image.Image:
        """값 표시 칩 (골드)"""
        width, height = 240, 80
        chip = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(chip)

        # 메탈릭 골드 그라데이션
        for y in range(height):
            ratio = y / height
            wave = math.sin(ratio * math.pi) * 0.3 + 0.7
            r = int(self.METALLIC_GOLD[0] * wave)
            g = int(self.METALLIC_GOLD[1] * wave)
            b = int(self.METALLIC_GOLD[2] * wave)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        # 라운드 마스크
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (width, height)], radius=35, fill=255)

        result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        result.paste(chip, (0, 0), mask)
        chip = result

        draw = ImageDraw.Draw(chip)

        # 테두리
        draw.rounded_rectangle(
            [(0, 0), (width - 1, height - 1)],
            radius=35,
            outline=self.OBSIDIAN,
            width=4
        )

        draw.rounded_rectangle(
            [(3, 3), (width - 4, height - 4)],
            radius=33,
            outline=self.PLATINUM,
            width=2
        )

        # 텍스트
        bbox = draw.textbbox((0, 0), text, font=self.font_value)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2 - 5

        # 텍스트 그림자
        draw.text((text_x + 2, text_y + 2), text, fill=(0, 0, 0, 180), font=self.font_value)

        # 메인 텍스트
        draw.text((text_x, text_y), text, fill=self.OBSIDIAN, font=self.font_value)

        return chip


# 전역 인스턴스
_luxury_renderers = {}


def get_luxury_renderer(theme: Optional[Theme] = None) -> LuxuryCardRenderer:
    """럭셔리 렌더러 가져오기"""
    theme_name = theme.name if theme else "Classic"

    if theme_name not in _luxury_renderers:
        _luxury_renderers[theme_name] = LuxuryCardRenderer(theme)

    return _luxury_renderers[theme_name]
