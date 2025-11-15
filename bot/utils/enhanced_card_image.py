"""
JackPy - 개선된 카드 이미지 생성
실제 카드 이미지, 애니메이션, 테마 지원
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Optional, Tuple
import io
from pathlib import Path
from bot.utils.themes import Theme, ThemeManager, ThemeType


class EnhancedCardImageGenerator:
    """
    개선된 카드 이미지 생성기

    Single Responsibility Principle:
    - 카드 이미지 생성과 합성에만 집중
    - 테마는 ThemeManager에 위임
    - 카드 로직은 Deck에 위임
    """

    # 카드 크기
    CARD_WIDTH = 160
    CARD_HEIGHT = 240
    CARD_SPACING = 25
    SHADOW_OFFSET = 8
    CARD_RADIUS = 22
    CARD_SHADOW_EXTRA = 26

    SUIT_COLORS = {
        'S': (20, 20, 20),
        'C': (25, 25, 25),
        'H': (220, 32, 64),
        'D': (255, 85, 0),
    }

    SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}

    RANK_DISPLAY = {
        'A': 'A', '2': '2', '3': '3', '4': '4', '5': '5',
        '6': '6', '7': '7', '8': '8', '9': '9', 'T': '10',
        'J': 'J', 'Q': 'Q', 'K': 'K'
    }

    def __init__(self, theme: Optional[Theme] = None):
        """
        초기화

        Args:
            theme: 테마 (None이면 클래식 테마 사용)
        """
        self.theme = theme or ThemeManager.CLASSIC
        self.cards_dir = Path(__file__).parent.parent.parent / "assets" / "cards"
        self._load_fonts()

    def _load_fonts(self):
        """폰트 로드"""
        try:
            self.font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            self.font_value = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
            self.font_message = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            self.font_result = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
        except Exception:
            # 폰트 로드 실패 시 기본 폰트
            self.font_title = ImageFont.load_default()
            self.font_value = ImageFont.load_default()
            self.font_message = ImageFont.load_default()
            self.font_result = ImageFont.load_default()

    def _ensure_rgba(self, color: Tuple[int, ...], alpha: int = 255) -> Tuple[int, int, int, int]:
        """RGB 또는 RGBA 값을 RGBA로 보정"""
        if isinstance(color, tuple) and len(color) == 4:
            return color
        return (color[0], color[1], color[2], alpha)

    def _color_with_alpha(self, color: Tuple[int, int, int], alpha: int) -> Tuple[int, int, int, int]:
        """알파값이 적용된 색상 생성"""
        return (color[0], color[1], color[2], alpha)

    def _create_linear_gradient(
        self,
        size: Tuple[int, int],
        start_color: Tuple[int, ...],
        end_color: Tuple[int, ...],
        horizontal: bool = False
    ) -> Image.Image:
        """선형 그라데이션 이미지 생성"""
        width, height = size
        gradient = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)
        steps = width if horizontal else height
        steps = max(steps - 1, 1)

        start_color = self._ensure_rgba(start_color)
        end_color = self._ensure_rgba(end_color)

        for i in range(steps + 1):
            ratio = i / steps
            color = tuple(int(start_color[j] * (1 - ratio) + end_color[j] * ratio) for j in range(4))
            if horizontal:
                draw.line([(i, 0), (i, height)], fill=color)
            else:
                draw.line([(0, i), (width, i)], fill=color)

        return gradient

    def _create_rounded_mask(self, width: int, height: int, radius: int) -> Image.Image:
        """라운드 마스크 생성"""
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            [(0, 0), (width, height)],
            radius=radius,
            fill=255
        )
        return mask

    def _get_suit_color(self, suit: str) -> Tuple[int, int, int]:
        """무늬에 따른 기본 색상"""
        return self.SUIT_COLORS.get(suit, (30, 30, 30))

    def _get_tinted_color(self, color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """밝게 틴트된 색상"""
        return tuple(int(255 - (255 - c) * 0.35) for c in color)

    def _create_corner_badge(self, rank: str, suit_symbol: str, color: Tuple[int, int, int]) -> Image.Image:
        """상단/하단 코너 배지 생성"""
        badge = Image.new('RGBA', (80, 120), (0, 0, 0, 0))
        tint = self._get_tinted_color(color)
        gradient = self._create_linear_gradient(
            badge.size,
            self._color_with_alpha((255, 255, 255), 235),
            self._color_with_alpha(tint, 190)
        )
        mask = self._create_rounded_mask(80, 120, 20)
        badge.paste(gradient, (0, 0), mask)

        draw = ImageDraw.Draw(badge)
        draw.text((12, 8), rank, fill=color, font=self.font_value)
        draw.text((15, 62), suit_symbol, fill=color, font=self.font_value)
        draw.rounded_rectangle(
            [(2, 2), (78, 118)],
            radius=18,
            outline=self._color_with_alpha(color, 120),
            width=1
        )

        return badge

    def _get_card_image_path(self, card_str: str) -> Optional[Path]:
        """
        카드 이미지 파일 경로 가져오기

        Args:
            card_str: 카드 문자열 (예: "AS", "KH")

        Returns:
            카드 이미지 파일 경로 (없으면 None)
        """
        # 카드 파일명 변환: AS -> ace_of_spades.png
        rank_map = {
            'A': 'ace', '2': '2', '3': '3', '4': '4', '5': '5',
            '6': '6', '7': '7', '8': '8', '9': '9', 'T': '10',
            'J': 'jack', 'Q': 'queen', 'K': 'king'
        }
        suit_map = {
            'S': 'spades', 'H': 'hearts', 'D': 'diamonds', 'C': 'clubs'
        }

        rank = card_str[:-1]
        suit = card_str[-1]

        rank_name = rank_map.get(rank, rank.lower())
        suit_name = suit_map.get(suit, suit.lower())

        filename = f"{rank_name}_of_{suit_name}.png"
        filepath = self.cards_dir / filename

        return filepath if filepath.exists() else None

    def _load_card_image(self, card_str: str, hidden: bool = False) -> Image.Image:
        """
        카드 이미지 로드 (실제 이미지 또는 생성)

        Args:
            card_str: 카드 문자열
            hidden: 뒷면 표시 여부

        Returns:
            PIL Image 객체
        """
        if hidden:
            # 뒷면 카드
            back_path = self.cards_dir / "back.png"
            if back_path.exists():
                card = Image.open(back_path).convert('RGBA')
                card = card.resize((self.CARD_WIDTH, self.CARD_HEIGHT), Image.LANCZOS)
                return card
            else:
                return self._draw_back_card()
        else:
            # 앞면 카드
            card_path = self._get_card_image_path(card_str)
            if card_path:
                card = Image.open(card_path).convert('RGBA')
                card = card.resize((self.CARD_WIDTH, self.CARD_HEIGHT), Image.LANCZOS)
                return card
            else:
                # 실제 이미지 없으면 그려서 생성
                return self._draw_front_card(card_str)

    def _draw_back_card(self) -> Image.Image:
        """뒷면 카드 그리기"""
        card = Image.new('RGBA', (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))

        gradient = self._create_linear_gradient(
            card.size,
            self._color_with_alpha(self.theme.colors.table_color, 255),
            self._color_with_alpha(self.theme.colors.background, 255)
        )
        mask = self._create_rounded_mask(self.CARD_WIDTH, self.CARD_HEIGHT, self.CARD_RADIUS)
        card.paste(gradient, (0, 0), mask)

        # 대각선 패턴
        pattern = Image.new('RGBA', card.size, (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern)
        accent = self._color_with_alpha(self.theme.colors.accent_color, 55)
        spacing = 22
        for x in range(-self.CARD_HEIGHT, self.CARD_WIDTH, spacing):
            p_draw.line([(x, 0), (x + self.CARD_HEIGHT, self.CARD_HEIGHT)], fill=accent, width=2)
        pattern = pattern.filter(ImageFilter.GaussianBlur(radius=1.5))
        card = Image.alpha_composite(card, pattern)

        draw = ImageDraw.Draw(card)
        for i in range(3):
            draw.rounded_rectangle(
                [(4 + i * 2, 4 + i * 2),
                 (self.CARD_WIDTH - 4 - i * 2, self.CARD_HEIGHT - 4 - i * 2)],
                radius=self.CARD_RADIUS - i,
                outline=self._color_with_alpha(self.theme.colors.border_color, 220 - i * 50),
                width=2
            )

        # 중앙 엠블럼
        emblem = Image.new('RGBA', card.size, (0, 0, 0, 0))
        e_draw = ImageDraw.Draw(emblem)
        center = (self.CARD_WIDTH // 2, self.CARD_HEIGHT // 2)
        e_draw.ellipse(
            [(center[0] - 60, center[1] - 60), (center[0] + 60, center[1] + 60)],
            fill=self._color_with_alpha(self.theme.colors.background, 210),
            outline=self._color_with_alpha(self.theme.colors.accent_color, 220),
            width=3
        )

        try:
            logo_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        except Exception:
            logo_font = self.font_value

        bbox = e_draw.textbbox((0, 0), "JP", font=logo_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        e_draw.text(
            (center[0] - text_width // 2, center[1] - text_height // 2),
            "JP",
            fill=self.theme.colors.accent_color,
            font=logo_font
        )

        emblem = emblem.filter(ImageFilter.GaussianBlur(radius=0.6))
        card = Image.alpha_composite(card, emblem)

        return card

    def _draw_front_card(self, card_str: str) -> Image.Image:
        """앞면 카드 그리기 (폴백)"""
        card = Image.new('RGBA', (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))

        # 카드 정보
        rank = card_str[:-1]
        suit = card_str[-1]
        rank_display = self.RANK_DISPLAY.get(rank, rank)
        suit_color = self._get_suit_color(suit)
        suit_symbol = self.SUIT_SYMBOLS.get(suit, suit)

        # 베이스 그라데이션
        gradient = self._create_linear_gradient(
            card.size,
            self._color_with_alpha((255, 255, 255), 255),
            self._color_with_alpha(self._get_tinted_color(suit_color), 255)
        )
        mask = self._create_rounded_mask(self.CARD_WIDTH, self.CARD_HEIGHT, self.CARD_RADIUS)
        card.paste(gradient, (0, 0), mask)

        # 미세 패턴
        pattern = Image.new('RGBA', card.size, (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern)
        stripe_color = self._color_with_alpha(suit_color, 35)
        for x in range(-self.CARD_HEIGHT, self.CARD_WIDTH, 12):
            p_draw.line([(x, 0), (x + self.CARD_HEIGHT, self.CARD_HEIGHT)], fill=stripe_color, width=2)
        pattern = pattern.filter(ImageFilter.GaussianBlur(radius=1))
        card = Image.alpha_composite(card, pattern)

        # 광택 효과
        highlight = Image.new('RGBA', card.size, (0, 0, 0, 0))
        h_draw = ImageDraw.Draw(highlight)
        h_draw.ellipse(
            [(-self.CARD_WIDTH * 0.2, -self.CARD_HEIGHT * 0.3),
             (self.CARD_WIDTH * 0.8, self.CARD_HEIGHT * 0.6)],
            fill=self._color_with_alpha((255, 255, 255), 90)
        )
        highlight = highlight.filter(ImageFilter.GaussianBlur(radius=30))
        card = Image.alpha_composite(card, highlight)

        # 테두리
        border_layer = Image.new('RGBA', card.size, (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border_layer)
        border_draw.rounded_rectangle(
            [(2, 2), (self.CARD_WIDTH - 2, self.CARD_HEIGHT - 2)],
            radius=self.CARD_RADIUS,
            outline=self._color_with_alpha((255, 255, 255), 220),
            width=3
        )
        border_draw.rounded_rectangle(
            [(8, 8), (self.CARD_WIDTH - 8, self.CARD_HEIGHT - 8)],
            radius=self.CARD_RADIUS - 4,
            outline=self._color_with_alpha(self.theme.colors.border_color, 200),
            width=2
        )
        card = Image.alpha_composite(card, border_layer)

        # 코너 배지
        badge = self._create_corner_badge(rank_display, suit_symbol, suit_color)
        card.paste(badge, (12, 14), badge)
        bottom_badge = badge.rotate(180, expand=False)
        card.paste(
            bottom_badge,
            (self.CARD_WIDTH - badge.width - 12, self.CARD_HEIGHT - badge.height - 14),
            bottom_badge
        )

        # 중앙 심볼 + 글로우
        glow = Image.new('RGBA', card.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse(
            [(self.CARD_WIDTH * 0.2, self.CARD_HEIGHT * 0.15),
             (self.CARD_WIDTH * 0.8, self.CARD_HEIGHT * 0.9)],
            fill=self._color_with_alpha(self._get_tinted_color(suit_color), 70)
        )
        glow = glow.filter(ImageFilter.GaussianBlur(radius=25))
        card = Image.alpha_composite(card, glow)

        text_layer = Image.new('RGBA', card.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        bbox = text_draw.textbbox((0, 0), suit_symbol, font=self.font_result)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.CARD_WIDTH - text_width) // 2
        y = (self.CARD_HEIGHT - text_height) // 2 - 8
        text_draw.text((x + 4, y + 4), suit_symbol, fill=self._color_with_alpha((0, 0, 0), 80), font=self.font_result)
        text_draw.text((x, y), suit_symbol, fill=suit_color, font=self.font_result)
        card = Image.alpha_composite(card, text_layer)

        return card

    def _add_card_shadow(self, card: Image.Image) -> Image.Image:
        """
        카드에 그림자 추가

        Args:
            card: 카드 이미지

        Returns:
            그림자가 추가된 카드
        """
        width = self.CARD_WIDTH + self.CARD_SHADOW_EXTRA
        height = self.CARD_HEIGHT + self.CARD_SHADOW_EXTRA
        shadow = Image.new('RGBA', (width, height), (0, 0, 0, 0))

        draw = ImageDraw.Draw(shadow)
        draw.rounded_rectangle(
            [(self.SHADOW_OFFSET, self.SHADOW_OFFSET),
             (self.CARD_WIDTH + self.SHADOW_OFFSET + 12,
              self.CARD_HEIGHT + self.SHADOW_OFFSET + 12)],
            radius=self.CARD_RADIUS + 6,
            fill=self.theme.colors.card_shadow
        )

        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
        shadow.paste(card, (0, 0), card)

        return shadow

    def _create_gradient_background(self, width: int, height: int) -> Image.Image:
        """
        그라데이션 배경 생성

        Args:
            width: 배경 너비
            height: 배경 높이

        Returns:
            그라데이션 배경 이미지
        """
        background = Image.new('RGB', (width, height), self.theme.colors.background)

        if self.theme.has_gradient:
            draw = ImageDraw.Draw(background)
            start_color = self.theme.colors.background
            end_color = self.theme.colors.table_color

            for y in range(height):
                ratio = y / height
                r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
                g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
                b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

        return background

    def _apply_light_overlay(self, image: Image.Image) -> Image.Image:
        """부드러운 조명 오버레이 적용"""
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        width, height = image.size

        accent = self._color_with_alpha(self.theme.colors.accent_color, 70)
        border_glow = self._color_with_alpha(self.theme.colors.border_color, 60)

        draw.ellipse(
            [(-int(width * 0.15), int(height * 0.05)),
             (int(width * 0.35), int(height * 0.55))],
            fill=accent
        )
        draw.ellipse(
            [(int(width * 0.55), -int(height * 0.2)),
             (int(width * 1.1), int(height * 0.35))],
            fill=border_glow
        )

        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=120))
        return Image.alpha_composite(image, overlay)

    def _create_section_panel(self, width: int, height: int) -> Image.Image:
        """반투명 섹션 패널 생성"""
        panel = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        gradient = self._create_linear_gradient(
            panel.size,
            self._color_with_alpha((255, 255, 255), 35),
            self._color_with_alpha(self.theme.colors.table_color, 90)
        )
        mask = self._create_rounded_mask(width, height, 32)
        panel.paste(gradient, (0, 0), mask)

        draw = ImageDraw.Draw(panel)
        draw.rounded_rectangle(
            [(2, 2), (width - 2, height - 2)],
            radius=30,
            outline=self._color_with_alpha(self.theme.colors.border_color, 140),
            width=2
        )
        draw.rounded_rectangle(
            [(10, 10), (width - 10, height - 10)],
            radius=26,
            outline=self._color_with_alpha(self.theme.colors.border_color, 70),
            width=1
        )

        return panel

    def _create_value_chip(self, text: str) -> Image.Image:
        """합계 정보를 위한 글라스모픽 칩"""
        width, height = 220, 70
        chip = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        gradient = self._create_linear_gradient(
            chip.size,
            self._color_with_alpha((255, 255, 255), 80),
            self._color_with_alpha(self.theme.colors.background, 140)
        )
        mask = self._create_rounded_mask(width, height, 32)
        chip.paste(gradient, (0, 0), mask)

        draw = ImageDraw.Draw(chip)
        draw.rounded_rectangle(
            [(0, 0), (width - 1, height - 1)],
            radius=32,
            outline=self._color_with_alpha(self.theme.colors.accent_color, 200),
            width=2
        )

        bbox = draw.textbbox((0, 0), text, font=self.font_value)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text(
            ((width - text_width) // 2, (height - text_height) // 2 - 4),
            text,
            fill=self.theme.colors.text_color,
            font=self.font_value
        )

        return chip

    def generate_game_image(
        self,
        player_hand: List[str],
        dealer_hand: List[str],
        player_value: int,
        dealer_value: Optional[int] = None,
        hide_dealer_first: bool = True,
        message: str = ""
    ) -> bytes:
        """
        게임 전체 이미지 생성

        Args:
            player_hand: 플레이어 카드
            dealer_hand: 딜러 카드
            player_value: 플레이어 핸드 값
            dealer_value: 딜러 핸드 값
            hide_dealer_first: 딜러 첫 카드 숨김
            message: 메시지

        Returns:
            PNG 이미지 바이트
        """
        message_lines = message.split('\n') if message else []

        # 이미지 크기 계산
        max_cards = max(len(player_hand), len(dealer_hand), 1)
        card_visual_width = self.CARD_WIDTH + self.CARD_SHADOW_EXTRA
        spacing_width = max(0, max_cards - 1) * self.CARD_SPACING
        card_area_width = max_cards * card_visual_width + spacing_width + 200

        total_width = max(card_area_width, 920)
        section_height = self.CARD_HEIGHT + self.CARD_SHADOW_EXTRA + 220
        estimated_msg_height = len(message_lines) * 45 + 80 if message_lines else 0
        total_height = section_height * 2 + max(180, estimated_msg_height + 80)

        # 배경 생성
        image = self._create_gradient_background(total_width, total_height)
        image = image.convert('RGBA')
        image = self._apply_light_overlay(image)
        draw = ImageDraw.Draw(image)

        # 외곽 테두리
        draw.rounded_rectangle(
            [(20, 20), (total_width - 20, total_height - 20)],
            radius=30,
            outline=self.theme.colors.border_color,
            width=4
        )

        panel_padding = 40
        panel_width = total_width - panel_padding * 2
        panel_height = section_height - 40

        # === 딜러 섹션 ===
        dealer_panel_y = 40
        dealer_panel = self._create_section_panel(panel_width, panel_height)
        image.paste(dealer_panel, (panel_padding, dealer_panel_y), dealer_panel)

        label_x = panel_padding + 40
        dealer_label_y = dealer_panel_y + 25
        draw.text(
            (label_x, dealer_label_y),
            "🤖 딜러",
            fill=self.theme.colors.text_color,
            font=self.font_title
        )

        dealer_cards_y = dealer_label_y + 80
        x_offset = panel_padding + 40
        for i, card_str in enumerate(dealer_hand):
            hidden = (i == 0 and hide_dealer_first)
            card = self._load_card_image(card_str, hidden)
            card_with_shadow = self._add_card_shadow(card)
            image.paste(card_with_shadow, (x_offset, dealer_cards_y), card_with_shadow)
            x_offset += card_visual_width + self.CARD_SPACING

        if dealer_value is not None:
            chip = self._create_value_chip(f"합: {dealer_value}")
            chip_x = min(panel_padding + panel_width - chip.width - 30, x_offset + 10)
            chip_y = dealer_cards_y + self.CARD_HEIGHT // 2 - chip.height // 2
            image.paste(chip, (chip_x, chip_y), chip)

        # === 플레이어 섹션 ===
        player_panel_y = dealer_panel_y + section_height
        player_panel = self._create_section_panel(panel_width, panel_height)
        image.paste(player_panel, (panel_padding, player_panel_y), player_panel)

        draw.text(
            (label_x, player_panel_y + 25),
            "🎯 플레이어",
            fill=self.theme.colors.text_color,
            font=self.font_title
        )

        player_cards_y = player_panel_y + 105
        x_offset = panel_padding + 40
        for card_str in player_hand:
            card = self._load_card_image(card_str, False)
            card_with_shadow = self._add_card_shadow(card)
            image.paste(card_with_shadow, (x_offset, player_cards_y), card_with_shadow)
            x_offset += card_visual_width + self.CARD_SPACING

        chip = self._create_value_chip(f"합: {player_value}")
        chip_x = min(panel_padding + panel_width - chip.width - 30, x_offset + 10)
        chip_y = player_cards_y + self.CARD_HEIGHT // 2 - chip.height // 2
        image.paste(chip, (chip_x, chip_y), chip)

        # === 메시지 ===
        if message_lines:
            message_y = player_panel_y + panel_height + 40
            msg_height = len(message_lines) * 45 + 50
            msg_panel = Image.new('RGBA', (panel_width, msg_height), (0, 0, 0, 0))
            msg_gradient = self._create_linear_gradient(
                msg_panel.size,
                self._color_with_alpha(self.theme.colors.border_color, 30),
                self._color_with_alpha(self.theme.colors.background, 140)
            )
            mask = self._create_rounded_mask(panel_width, msg_height, 24)
            msg_panel.paste(msg_gradient, (0, 0), mask)

            msg_draw = ImageDraw.Draw(msg_panel)
            msg_draw.rounded_rectangle(
                [(0, 0), (panel_width - 1, msg_height - 1)],
                radius=24,
                outline=self._color_with_alpha(self.theme.colors.accent_color, 180),
                width=2
            )

            for i, line in enumerate(message_lines):
                msg_draw.text(
                    (30, 15 + i * 45),
                    line,
                    fill=self.theme.colors.text_color,
                    font=self.font_message
                )

            image.paste(msg_panel, (panel_padding, message_y), msg_panel)

        # 이미지를 바이트로 변환
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()


# 전역 인스턴스
_enhanced_generators = {}


def get_enhanced_card_generator(theme: Optional[Theme] = None) -> EnhancedCardImageGenerator:
    """
    개선된 카드 생성기 가져오기

    Args:
        theme: 테마

    Returns:
        EnhancedCardImageGenerator 인스턴스
    """
    theme_name = theme.name if theme else "Classic"

    if theme_name not in _enhanced_generators:
        _enhanced_generators[theme_name] = EnhancedCardImageGenerator(theme)

    return _enhanced_generators[theme_name]
