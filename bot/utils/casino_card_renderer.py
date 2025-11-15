"""
JackPy - 카지노급 카드 렌더러
실제 카지노 카드처럼 K, Q, J, A 그림 포함
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Optional, Tuple
import io
from pathlib import Path
from bot.utils.themes import Theme, ThemeManager
import math


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
        'S': (20, 20, 20),
        'C': (25, 25, 25),
        'H': (220, 20, 60),
        'D': (255, 85, 0),
    }

    SUIT_GLOW_COLORS = {
        'S': (100, 100, 255),
        'C': (50, 255, 50),
        'H': (255, 50, 100),
        'D': (255, 200, 50),
    }

    SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}

    def __init__(self, theme: Optional[Theme] = None):
        """초기화"""
        self.theme = theme or ThemeManager.CLASSIC
        self.cards_dir = Path(__file__).parent.parent.parent / "assets" / "cards"
        self._load_fonts()

    def _load_fonts(self):
        """폰트 로드 - 한글 지원 폰트 사용"""
        fonts_dir = Path(__file__).parent.parent.parent / "assets" / "fonts" / "Poppins"

        # Poppins 폰트 경로 (영문용)
        poppins_bold = fonts_dir / "Poppins-Bold.ttf"
        poppins_semibold = fonts_dir / "Poppins-SemiBold.ttf"
        poppins_medium = fonts_dir / "Poppins-Medium.ttf"
        poppins_regular = fonts_dir / "Poppins-Regular.ttf"

        # 한글 지원 시스템 폰트 (폴백용)
        korean_fonts = [
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # macOS 기본 한글 폰트
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux
        ]

        # 영문 시스템 폰트
        system_fonts = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]

        # 한글 폰트를 찾아서 로드
        korean_font_path = None
        for font_path in korean_fonts:
            if Path(font_path).exists():
                korean_font_path = font_path
                break

        # Poppins 또는 시스템 폰트 로드
        english_font_loaded = False
        font_paths = [poppins_bold, poppins_semibold] + system_fonts

        for font_path in font_paths:
            try:
                if Path(font_path).exists():
                    # 랭크용 - 영문은 Poppins, 나머지는 한글 폰트
                    self.font_rank_large = ImageFont.truetype(str(poppins_semibold if poppins_semibold.exists() else korean_font_path), 72)
                    self.font_rank_small = ImageFont.truetype(str(poppins_semibold if poppins_semibold.exists() else korean_font_path), 48)

                    # 무늬용
                    self.font_suit_huge = ImageFont.truetype(str(poppins_regular if poppins_regular.exists() else korean_font_path), 180)
                    self.font_suit_large = ImageFont.truetype(str(poppins_regular if poppins_regular.exists() else korean_font_path), 100)
                    self.font_suit_medium = ImageFont.truetype(str(poppins_regular if poppins_regular.exists() else korean_font_path), 60)
                    self.font_suit_small = ImageFont.truetype(str(poppins_regular if poppins_regular.exists() else korean_font_path), 44)

                    # 페이스 카드 문자
                    self.font_face_letter = ImageFont.truetype(str(poppins_bold if poppins_bold.exists() else korean_font_path), 140)

                    # UI 텍스트 - 한글 지원 필수
                    if korean_font_path:
                        self.font_title = ImageFont.truetype(str(korean_font_path), 58)
                        self.font_value = ImageFont.truetype(str(korean_font_path), 50)
                        self.font_message = ImageFont.truetype(str(korean_font_path), 40)
                    else:
                        self.font_title = ImageFont.truetype(str(poppins_medium if poppins_medium.exists() else font_path), 58)
                        self.font_value = ImageFont.truetype(str(poppins_semibold if poppins_semibold.exists() else font_path), 50)
                        self.font_message = ImageFont.truetype(str(poppins_regular if poppins_regular.exists() else font_path), 40)

                    english_font_loaded = True
                    break
            except Exception:
                continue

        if not english_font_loaded:
            # 모든 폰트 로드 실패 시 기본 폰트
            default = ImageFont.load_default()
            self.font_rank_large = default
            self.font_rank_small = default
            self.font_suit_huge = default
            self.font_suit_large = default
            self.font_suit_medium = default
            self.font_suit_small = default
            self.font_face_letter = default
            self.font_title = default
            self.font_value = default
            self.font_message = default

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
            'A': 'A', '2': '2', '3': '3', '4': '4', '5': '5',
            '6': '6', '7': '7', '8': '8', '9': '9', 'T': '10',
            'J': 'J', 'Q': 'Q', 'K': 'K'
        }
        suit_map = {
            'S': 'spades', 'H': 'hearts', 'D': 'diamonds', 'C': 'clubs'
        }

        rank = card_str[:-1]
        suit = card_str[-1]

        rank_name = rank_map.get(rank, rank)
        suit_name = suit_map.get(suit, '')

        # 파일명: "A_of_hearts.png"
        filename = f"{rank_name}_of_{suit_name}.png"
        filepath = self.cards_dir / filename

        if filepath.exists():
            return filepath

        return None

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
                card_img = Image.open(card_path).convert('RGBA')

                # 카드 크기에 맞게 리사이즈
                card_img = card_img.resize(
                    (self.CARD_WIDTH, self.CARD_HEIGHT),
                    Image.LANCZOS
                )

                # 라운드 코너 적용
                mask = Image.new('L', (self.CARD_WIDTH, self.CARD_HEIGHT), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle(
                    [(0, 0), (self.CARD_WIDTH, self.CARD_HEIGHT)],
                    radius=self.CARD_RADIUS,
                    fill=255
                )

                # 마스크 적용
                result = Image.new('RGBA', card_img.size, (0, 0, 0, 0))
                result.paste(card_img, (0, 0), mask)

                # 골드 테두리 추가
                draw = ImageDraw.Draw(result)
                draw.rounded_rectangle(
                    [(5, 5), (self.CARD_WIDTH - 5, self.CARD_HEIGHT - 5)],
                    radius=self.CARD_RADIUS - 2,
                    outline=self.DARK_GOLD,
                    width=5
                )
                draw.rounded_rectangle(
                    [(10, 10), (self.CARD_WIDTH - 10, self.CARD_HEIGHT - 10)],
                    radius=self.CARD_RADIUS - 5,
                    outline=self.METALLIC_GOLD,
                    width=3
                )
                draw.rounded_rectangle(
                    [(14, 14), (self.CARD_WIDTH - 14, self.CARD_HEIGHT - 14)],
                    radius=self.CARD_RADIUS - 7,
                    outline=self.PLATINUM,
                    width=1
                )

                # 광택 효과
                gloss = Image.new('RGBA', result.size, (0, 0, 0, 0))
                gloss_draw = ImageDraw.Draw(gloss)
                gloss_draw.ellipse(
                    [(-self.CARD_WIDTH * 0.3, -self.CARD_HEIGHT * 0.4),
                     (self.CARD_WIDTH * 0.7, self.CARD_HEIGHT * 0.3)],
                    fill=(255, 255, 255, 40)
                )
                gloss = gloss.filter(ImageFilter.GaussianBlur(radius=60))
                result = Image.alpha_composite(result, gloss)

                return result

            except Exception as e:
                # 에러 발생 시 None 반환하여 폴백 렌더링 사용
                return None

        return None

    def _create_corner_index(self, rank: str, suit_symbol: str, color: Tuple) -> Image.Image:
        """코너 인덱스 (랭크 + 무늬)"""
        corner = Image.new('RGBA', (90, 130), (0, 0, 0, 0))
        draw = ImageDraw.Draw(corner)

        # 랭크
        draw.text((10, 5), rank, fill=color, font=self.font_rank_small)

        # 무늬
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_small)
        text_width = bbox[2] - bbox[0]
        draw.text((45 - text_width // 2, 70), suit_symbol, fill=color, font=self.font_suit_small)

        return corner

    def _draw_face_king(self, suit: str, color: Tuple, glow_color: Tuple) -> Image.Image:
        """킹 카드 중앙 그림"""
        center = Image.new('RGBA', (200, 260), (0, 0, 0, 0))
        draw = ImageDraw.Draw(center)

        suit_symbol = self.SUIT_SYMBOLS[suit]

        # 배경 실루엣 (왕관 모양)
        crown_points = [
            (100, 30),   # 정점
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
        bbox = draw.textbbox((0, 0), 'K', font=self.font_face_letter)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (200 - text_width) // 2
        y = 90

        # 그림자
        for offset in [(4, 4), (3, 3), (2, 2)]:
            draw.text((x + offset[0], y + offset[1]), 'K',
                     fill=(0, 0, 0, 80), font=self.font_face_letter)

        # 메인 'K'
        draw.text((x, y), 'K', fill=color, font=self.font_face_letter)

        # 하단 심볼
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_medium)
        text_width = bbox[2] - bbox[0]
        draw.text((100 - text_width // 2, 210), suit_symbol,
                 fill=color, font=self.font_suit_medium)

        return center

    def _draw_face_queen(self, suit: str, color: Tuple, glow_color: Tuple) -> Image.Image:
        """퀸 카드 중앙 그림"""
        center = Image.new('RGBA', (200, 260), (0, 0, 0, 0))
        draw = ImageDraw.Draw(center)

        suit_symbol = self.SUIT_SYMBOLS[suit]

        # 배경 하트 (여왕 상징)
        heart_center = (100, 50)
        draw.ellipse(
            [(heart_center[0] - 25, heart_center[1] - 15),
             (heart_center[0] + 25, heart_center[1] + 15)],
            fill=glow_color + (60,),
            outline=color,
            width=2
        )

        # 큰 'Q' 문자
        bbox = draw.textbbox((0, 0), 'Q', font=self.font_face_letter)
        text_width = bbox[2] - bbox[0]
        x = (200 - text_width) // 2
        y = 90

        # 그림자
        for offset in [(4, 4), (3, 3), (2, 2)]:
            draw.text((x + offset[0], y + offset[1]), 'Q',
                     fill=(0, 0, 0, 80), font=self.font_face_letter)

        # 메인 'Q'
        draw.text((x, y), 'Q', fill=color, font=self.font_face_letter)

        # 하단 심볼
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_medium)
        text_width = bbox[2] - bbox[0]
        draw.text((100 - text_width // 2, 210), suit_symbol,
                 fill=color, font=self.font_suit_medium)

        return center

    def _draw_face_jack(self, suit: str, color: Tuple, glow_color: Tuple) -> Image.Image:
        """잭 카드 중앙 그림"""
        center = Image.new('RGBA', (200, 260), (0, 0, 0, 0))
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
        bbox = draw.textbbox((0, 0), 'J', font=self.font_face_letter)
        text_width = bbox[2] - bbox[0]
        x = (200 - text_width) // 2
        y = 90

        # 그림자
        for offset in [(4, 4), (3, 3), (2, 2)]:
            draw.text((x + offset[0], y + offset[1]), 'J',
                     fill=(0, 0, 0, 80), font=self.font_face_letter)

        # 메인 'J'
        draw.text((x, y), 'J', fill=color, font=self.font_face_letter)

        # 하단 심볼
        bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_medium)
        text_width = bbox[2] - bbox[0]
        draw.text((100 - text_width // 2, 210), suit_symbol,
                 fill=color, font=self.font_suit_medium)

        return center

    def _draw_ace_center(self, suit: str, color: Tuple, glow_color: Tuple) -> Image.Image:
        """에이스 중앙 (초대형 심볼)"""
        center = Image.new('RGBA', (200, 280), (0, 0, 0, 0))
        draw = ImageDraw.Draw(center)

        suit_symbol = self.SUIT_SYMBOLS[suit]

        # 글로우 효과
        glow_layer = Image.new('RGBA', center.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.ellipse(
            [(20, 20), (180, 260)],
            fill=glow_color + (40,)
        )
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
            draw.text((x + offset[0], y + offset[1]), suit_symbol,
                     fill=(0, 0, 0, 100), font=self.font_suit_huge)

        # 골드 외곽선
        for dx in [-3, -2, -1, 0, 1, 2, 3]:
            for dy in [-3, -2, -1, 0, 1, 2, 3]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), suit_symbol,
                             fill=self.DARK_GOLD + (80,), font=self.font_suit_huge)

        # 메인 심볼
        draw.text((x, y), suit_symbol, fill=color, font=self.font_suit_huge)

        # 하이라이트
        draw.text((x - 3, y - 3), suit_symbol,
                 fill=(255, 255, 255, 60), font=self.font_suit_huge)

        return center

    def _draw_number_symbols(self, rank: str, suit: str, color: Tuple) -> Image.Image:
        """숫자 카드 심볼 배치"""
        center = Image.new('RGBA', (180, 260), (0, 0, 0, 0))
        draw = ImageDraw.Draw(center)

        suit_symbol = self.SUIT_SYMBOLS[suit]
        num = int(rank) if rank != 'T' else 10

        # 심볼 위치 정의
        positions = {
            2: [(90, 50), (90, 210)],
            3: [(90, 40), (90, 130), (90, 220)],
            4: [(50, 50), (130, 50), (50, 210), (130, 210)],
            5: [(50, 50), (130, 50), (90, 130), (50, 210), (130, 210)],
            6: [(50, 50), (130, 50), (50, 130), (130, 130), (50, 210), (130, 210)],
            7: [(50, 40), (130, 40), (90, 90), (50, 140), (130, 140), (50, 220), (130, 220)],
            8: [(50, 40), (130, 40), (90, 80), (50, 130), (130, 130), (90, 180), (50, 220), (130, 220)],
            9: [(50, 40), (130, 40), (50, 95), (130, 95), (90, 130), (50, 165), (130, 165), (50, 220), (130, 220)],
            10: [(50, 30), (130, 30), (90, 70), (50, 110), (130, 110), (50, 150), (130, 150), (90, 190), (50, 230), (130, 230)],
        }

        if num in positions:
            for x, y in positions[num]:
                bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit_small)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # 그림자
                draw.text((x - text_width // 2 + 2, y - text_height // 2 + 2),
                         suit_symbol, fill=(0, 0, 0, 60), font=self.font_suit_small)

                # 메인
                draw.text((x - text_width // 2, y - text_height // 2),
                         suit_symbol, fill=color, font=self.font_suit_small)

        return center

    def _create_casino_card_front(self, card_str: str) -> Image.Image:
        """카지노급 앞면 카드"""

        # ===  실제 카드 이미지 먼저 시도 ===
        real_card = self._load_real_card_image(card_str)
        if real_card is not None:
            return real_card

        # === 실제 이미지 없으면 그려서 생성 ===
        card = Image.new('RGBA', (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))

        rank = card_str[:-1]
        suit = card_str[-1]
        suit_color = self.SUIT_COLORS.get(suit, (0, 0, 0))
        suit_symbol = self.SUIT_SYMBOLS.get(suit, suit)
        glow_color = self.SUIT_GLOW_COLORS.get(suit, (255, 255, 255))

        # 펄 화이트 베이스
        base = Image.new('RGBA', card.size, (255, 255, 255, 255))

        # 미세 펄 효과
        for y in range(0, self.CARD_HEIGHT, 5):
            alpha = int(15 + 10 * math.sin(y * 0.1))
            draw_base = ImageDraw.Draw(base)
            draw_base.line([(0, y), (self.CARD_WIDTH, y)],
                          fill=(248, 248, 255, alpha))

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

        # 골드 테두리 (3중)
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle(
            [(5, 5), (self.CARD_WIDTH - 5, self.CARD_HEIGHT - 5)],
            radius=self.CARD_RADIUS - 2,
            outline=self.DARK_GOLD,
            width=5
        )
        draw.rounded_rectangle(
            [(10, 10), (self.CARD_WIDTH - 10, self.CARD_HEIGHT - 10)],
            radius=self.CARD_RADIUS - 5,
            outline=self.METALLIC_GOLD,
            width=3
        )
        draw.rounded_rectangle(
            [(14, 14), (self.CARD_WIDTH - 14, self.CARD_HEIGHT - 14)],
            radius=self.CARD_RADIUS - 7,
            outline=self.PLATINUM,
            width=1
        )

        # 코너 인덱스
        corner = self._create_corner_index(rank, suit_symbol, suit_color)
        card.paste(corner, (20, 25), corner)

        # 하단 코너 (회전)
        corner_bottom = corner.rotate(180)
        card.paste(corner_bottom,
                  (self.CARD_WIDTH - corner.width - 20,
                   self.CARD_HEIGHT - corner.height - 25),
                  corner_bottom)

        # 중앙 그림
        if rank == 'K':
            center = self._draw_face_king(suit, suit_color, glow_color)
        elif rank == 'Q':
            center = self._draw_face_queen(suit, suit_color, glow_color)
        elif rank == 'J':
            center = self._draw_face_jack(suit, suit_color, glow_color)
        elif rank == 'A':
            center = self._draw_ace_center(suit, suit_color, glow_color)
        else:
            center = self._draw_number_symbols(rank, suit, suit_color)

        # 중앙 배치
        center_x = (self.CARD_WIDTH - center.width) // 2
        center_y = (self.CARD_HEIGHT - center.height) // 2
        card.paste(center, (center_x, center_y), center)

        # 최종 광택
        gloss = Image.new('RGBA', card.size, (0, 0, 0, 0))
        gloss_draw = ImageDraw.Draw(gloss)
        gloss_draw.ellipse(
            [(-self.CARD_WIDTH * 0.3, -self.CARD_HEIGHT * 0.4),
             (self.CARD_WIDTH * 0.7, self.CARD_HEIGHT * 0.3)],
            fill=(255, 255, 255, 50)
        )
        gloss = gloss.filter(ImageFilter.GaussianBlur(radius=60))
        card = Image.alpha_composite(card, gloss)

        return card

    def _create_casino_card_back(self) -> Image.Image:
        """카지노급 뒷면"""

        # === 실제 뒷면 이미지 먼저 시도 ===
        back_path = self.cards_dir / "back.png"
        if back_path.exists():
            try:
                card_img = Image.open(back_path).convert('RGBA')
                card_img = card_img.resize(
                    (self.CARD_WIDTH, self.CARD_HEIGHT),
                    Image.LANCZOS
                )

                # 라운드 코너
                mask = Image.new('L', (self.CARD_WIDTH, self.CARD_HEIGHT), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle(
                    [(0, 0), (self.CARD_WIDTH, self.CARD_HEIGHT)],
                    radius=self.CARD_RADIUS,
                    fill=255
                )

                result = Image.new('RGBA', card_img.size, (0, 0, 0, 0))
                result.paste(card_img, (0, 0), mask)

                # 골드 테두리
                draw = ImageDraw.Draw(result)
                for i in range(4):
                    offset = 5 + i * 4
                    draw.rounded_rectangle(
                        [(offset, offset),
                         (self.CARD_WIDTH - offset, self.CARD_HEIGHT - offset)],
                        radius=self.CARD_RADIUS - i * 2,
                        outline=self.METALLIC_GOLD + (255 - i * 40,),
                        width=3
                    )

                return result
            except Exception as e:
                print(f"뒷면 이미지 로드 실패: {e}")

        # === 실제 이미지 없으면 그려서 생성 ===
        card = Image.new('RGBA', (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))

        # 다크 그라데이션
        base = Image.new('RGBA', card.size, (0, 0, 0, 0))
        draw_base = ImageDraw.Draw(base)

        for y in range(self.CARD_HEIGHT):
            ratio = y / self.CARD_HEIGHT
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

        # 다이아몬드 패턴
        pattern = Image.new('RGBA', card.size, (0, 0, 0, 0))
        pattern_draw = ImageDraw.Draw(pattern)

        spacing = 40
        for y in range(0, self.CARD_HEIGHT + spacing, spacing):
            for x in range(0, self.CARD_WIDTH + spacing, spacing):
                points = [(x, y - 10), (x + 10, y), (x, y + 10), (x - 10, y)]
                pattern_draw.polygon(points, outline=self.METALLIC_GOLD + (100,), width=2)

        card = Image.alpha_composite(card, pattern)

        # 골드 테두리
        draw = ImageDraw.Draw(card)
        for i in range(4):
            offset = 5 + i * 4
            draw.rounded_rectangle(
                [(offset, offset),
                 (self.CARD_WIDTH - offset, self.CARD_HEIGHT - offset)],
                radius=self.CARD_RADIUS - i * 2,
                outline=self.METALLIC_GOLD + (255 - i * 40,),
                width=3
            )

        # 중앙 로고
        center_x = self.CARD_WIDTH // 2
        center_y = self.CARD_HEIGHT // 2

        logo_bg = Image.new('RGBA', card.size, (0, 0, 0, 0))
        logo_draw = ImageDraw.Draw(logo_bg)

        logo_draw.ellipse(
            [(center_x - 90, center_y - 90), (center_x + 90, center_y + 90)],
            fill=(20, 20, 40, 230),
            outline=self.METALLIC_GOLD,
            width=6
        )
        logo_draw.ellipse(
            [(center_x - 80, center_y - 80), (center_x + 80, center_y + 80)],
            outline=self.PLATINUM,
            width=2
        )

        card = Image.alpha_composite(card, logo_bg)

        # JP 로고
        try:
            logo_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 70)
        except:
            logo_font = self.font_rank_large

        text_layer = Image.new('RGBA', card.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)

        # 그림자
        for offset in [(4, 4), (3, 3), (2, 2)]:
            text_draw.text(
                (center_x - 35 + offset[0], center_y - 40 + offset[1]),
                "JP",
                fill=(0, 0, 0, 120),
                font=logo_font
            )

        # 메인 텍스트
        text_draw.text(
            (center_x - 35, center_y - 40),
            "JP",
            fill=self.METALLIC_GOLD,
            font=logo_font
        )

        card = Image.alpha_composite(card, text_layer)

        return card

    def _add_dramatic_shadow(self, card: Image.Image) -> Image.Image:
        """드라마틱 그림자"""
        shadow_offset = 15
        shadow_size = (card.width + shadow_offset * 2, card.height + shadow_offset * 2)

        shadow = Image.new('RGBA', shadow_size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)

        for i in range(3):
            offset = shadow_offset + i * 2
            alpha = 180 - i * 40
            shadow_draw.rounded_rectangle(
                [(offset, offset), (card.width + offset, card.height + offset)],
                radius=self.CARD_RADIUS + 5,
                fill=(0, 0, 0, alpha)
            )

        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
        shadow.paste(card, (0, 0), card)

        return shadow

    def _create_velvet_background(self, width: int, height: int) -> Image.Image:
        """모던 그라데이션 배경 (네온 액센트)"""
        bg = Image.new('RGB', (width, height), self.theme.colors.background)

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
            noise = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            noise_draw = ImageDraw.Draw(noise)
            for _ in range(500):
                x = random.randint(0, width)
                y = random.randint(0, height)
                size = random.randint(1, 3)
                alpha = random.randint(5, 20)
                noise_draw.ellipse(
                    [(x, y), (x + size, y + size)],
                    fill=(255, 255, 255, alpha)
                )
            bg = bg.convert('RGBA')
            bg = Image.alpha_composite(bg, noise)

        return bg.convert('RGBA')

    def generate_game_image(
        self,
        player_hand: List[str],
        dealer_hand: List[str],
        player_value: int,
        dealer_value: Optional[int] = None,
        hide_dealer_first: bool = True,
        message: str = ""
    ) -> bytes:
        """카지노급 게임 이미지 생성"""

        message_lines = message.split('\n') if message else []

        max_cards = max(len(player_hand), len(dealer_hand), 1)
        shadow_extra = 30
        card_visual_width = self.CARD_WIDTH + shadow_extra

        card_area_width = (max_cards * card_visual_width +
                          (max_cards - 1) * self.CARD_SPACING + 150)

        total_width = max(card_area_width, 1150)
        section_height = self.CARD_HEIGHT + shadow_extra + 260
        msg_height = len(message_lines) * 52 + 100 if message_lines else 100
        total_height = section_height * 2 + msg_height

        # 배경
        image = self._create_velvet_background(total_width, total_height)
        draw = ImageDraw.Draw(image)

        # 네온 글로우 프레임
        border_color = self.theme.colors.border_color
        accent_color = self.theme.colors.accent_color

        # 외부 글로우 (네온 효과)
        glow_layer = Image.new('RGBA', (total_width, total_height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        for i in range(10, 0, -1):
            offset = 15 + i * 3
            alpha = int(80 - i * 7)
            glow_draw.rounded_rectangle(
                [(offset, offset), (total_width - offset, total_height - offset)],
                radius=50 - i,
                outline=border_color + (alpha,),
                width=i * 2
            )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=15))
        image = Image.alpha_composite(image, glow_layer)
        draw = ImageDraw.Draw(image)

        # 메인 테두리
        for i in range(3):
            offset = 20 + i * 3
            alpha = 255 - i * 40
            draw.rounded_rectangle(
                [(offset, offset), (total_width - offset, total_height - offset)],
                radius=38 - i * 2,
                outline=border_color + (alpha,),
                width=3
            )

        # 액센트 라인
        draw.rounded_rectangle(
            [(25, 25), (total_width - 25, total_height - 25)],
            radius=35,
            outline=accent_color + (180,),
            width=1
        )

        # 딜러 섹션
        dealer_y = 60
        panel_width = total_width - 120
        panel_height = section_height - 80

        # Glassmorphism 스타일 패널
        panel = Image.new('RGBA', (panel_width, panel_height), (0, 0, 0, 0))
        panel_draw = ImageDraw.Draw(panel)
        panel_draw.rounded_rectangle(
            [(0, 0), (panel_width, panel_height)],
            radius=30,
            fill=(255, 255, 255, 15)
        )

        # 네온 테두리 글로우 (축소)
        panel_glow = Image.new('RGBA', (panel_width, panel_height), (0, 0, 0, 0))
        panel_glow_draw = ImageDraw.Draw(panel_glow)
        for i in range(4, 0, -1):
            alpha = int(35 - i * 6)
            panel_glow_draw.rounded_rectangle(
                [(0, 0), (panel_width, panel_height)],
                radius=30,
                outline=border_color + (alpha,),
                width=i * 2
            )
        panel_glow = panel_glow.filter(ImageFilter.GaussianBlur(radius=5))
        panel = Image.alpha_composite(panel, panel_glow)

        panel_draw = ImageDraw.Draw(panel)
        panel_draw.rounded_rectangle(
            [(0, 0), (panel_width, panel_height)],
            radius=30,
            outline=border_color + (180,),
            width=2
        )
        panel_draw.rounded_rectangle(
            [(2, 2), (panel_width - 2, panel_height - 2)],
            radius=28,
            outline=accent_color + (100,),
            width=1
        )

        image.paste(panel, (60, dealer_y), panel)

        # 딜러 라벨 (네온 스타일)
        label_x = 100
        label_y = dealer_y + 30

        label_bg = Image.new('RGBA', (260, 80), (0, 0, 0, 0))
        label_bg_draw = ImageDraw.Draw(label_bg)

        # 네온 글로우
        for i in range(6, 0, -1):
            alpha = int(60 - i * 8)
            label_bg_draw.rounded_rectangle(
                [(0, 0), (260, 80)],
                radius=22,
                outline=border_color + (alpha,),
                width=i * 2
            )
        label_bg = label_bg.filter(ImageFilter.GaussianBlur(radius=6))

        label_bg_draw = ImageDraw.Draw(label_bg)
        label_bg_draw.rounded_rectangle(
            [(0, 0), (260, 80)],
            radius=22,
            fill=(20, 20, 30, 220),
            outline=border_color,
            width=3
        )
        label_bg_draw.rounded_rectangle(
            [(3, 3), (257, 77)],
            radius=20,
            outline=accent_color + (150,),
            width=1
        )

        image.paste(label_bg, (label_x, label_y), label_bg)

        # 텍스트 중앙 정렬 계산
        dealer_text = "🤖 딜러"
        temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        dealer_bbox = temp_draw.textbbox((0, 0), dealer_text, font=self.font_title)
        dealer_text_width = dealer_bbox[2] - dealer_bbox[0]
        dealer_text_height = dealer_bbox[3] - dealer_bbox[1]
        dealer_text_x = label_x + (260 - dealer_text_width) // 2
        dealer_text_y = label_y + (80 - dealer_text_height) // 2 - 5

        # 텍스트 글로우 효과
        text_glow = Image.new('RGBA', image.size, (0, 0, 0, 0))
        text_glow_draw = ImageDraw.Draw(text_glow)
        for offset in [(2, 2), (1, 1), (-1, -1), (-2, -2)]:
            text_glow_draw.text(
                (dealer_text_x + offset[0], dealer_text_y + offset[1]),
                dealer_text,
                fill=border_color + (100,),
                font=self.font_title
            )
        text_glow = text_glow.filter(ImageFilter.GaussianBlur(radius=3))
        image = Image.alpha_composite(image, text_glow)
        draw = ImageDraw.Draw(image)

        draw.text((dealer_text_x, dealer_text_y), dealer_text,
                 fill=(255, 255, 255), font=self.font_title)

        # 딜러 카드
        cards_y = label_y + 110
        x_offset = 100

        for i, card_str in enumerate(dealer_hand):
            if i == 0 and hide_dealer_first:
                card_img = self._create_casino_card_back()
            else:
                card_img = self._create_casino_card_front(card_str)

            card_with_shadow = self._add_dramatic_shadow(card_img)
            image.paste(card_with_shadow, (x_offset, cards_y), card_with_shadow)
            x_offset += card_visual_width + self.CARD_SPACING

        # 딜러 값
        if dealer_value is not None:
            chip = self._create_value_chip(f"합: {dealer_value}")
            chip_x = total_width - chip.width - 120
            chip_y = cards_y + (self.CARD_HEIGHT - chip.height) // 2
            image.paste(chip, (chip_x, chip_y), chip)

        # 플레이어 섹션
        player_y = dealer_y + section_height - 20

        # Glassmorphism 패널
        panel2 = Image.new('RGBA', (panel_width, panel_height), (0, 0, 0, 0))
        panel2_draw = ImageDraw.Draw(panel2)
        panel2_draw.rounded_rectangle(
            [(0, 0), (panel_width, panel_height)],
            radius=30,
            fill=(255, 255, 255, 15)
        )

        # 네온 글로우 (축소)
        panel2_glow = Image.new('RGBA', (panel_width, panel_height), (0, 0, 0, 0))
        panel2_glow_draw = ImageDraw.Draw(panel2_glow)
        for i in range(4, 0, -1):
            alpha = int(35 - i * 6)
            panel2_glow_draw.rounded_rectangle(
                [(0, 0), (panel_width, panel_height)],
                radius=30,
                outline=accent_color + (alpha,),
                width=i * 2
            )
        panel2_glow = panel2_glow.filter(ImageFilter.GaussianBlur(radius=5))
        panel2 = Image.alpha_composite(panel2, panel2_glow)

        panel2_draw = ImageDraw.Draw(panel2)
        panel2_draw.rounded_rectangle(
            [(0, 0), (panel_width, panel_height)],
            radius=30,
            outline=accent_color + (180,),
            width=2
        )
        panel2_draw.rounded_rectangle(
            [(2, 2), (panel_width - 2, panel_height - 2)],
            radius=28,
            outline=border_color + (100,),
            width=1
        )

        image.paste(panel2, (60, player_y), panel2)

        # 플레이어 라벨 (네온 스타일)
        label_bg2 = Image.new('RGBA', (310, 80), (0, 0, 0, 0))
        label_bg2_draw = ImageDraw.Draw(label_bg2)

        # 네온 글로우
        for i in range(6, 0, -1):
            alpha = int(60 - i * 8)
            label_bg2_draw.rounded_rectangle(
                [(0, 0), (310, 80)],
                radius=22,
                outline=accent_color + (alpha,),
                width=i * 2
            )
        label_bg2 = label_bg2.filter(ImageFilter.GaussianBlur(radius=6))

        label_bg2_draw = ImageDraw.Draw(label_bg2)
        label_bg2_draw.rounded_rectangle(
            [(0, 0), (310, 80)],
            radius=22,
            fill=(20, 20, 30, 220),
            outline=accent_color,
            width=3
        )
        label_bg2_draw.rounded_rectangle(
            [(3, 3), (307, 77)],
            radius=20,
            outline=border_color + (150,),
            width=1
        )

        image.paste(label_bg2, (label_x, player_y + 30), label_bg2)

        # 텍스트 중앙 정렬 계산
        player_text = "🎯 플레이어"
        temp_draw2 = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        player_bbox = temp_draw2.textbbox((0, 0), player_text, font=self.font_title)
        player_text_width = player_bbox[2] - player_bbox[0]
        player_text_height = player_bbox[3] - player_bbox[1]
        player_text_x = label_x + (310 - player_text_width) // 2
        player_text_y = player_y + 30 + (80 - player_text_height) // 2 - 5

        # 텍스트 글로우
        text_glow2 = Image.new('RGBA', image.size, (0, 0, 0, 0))
        text_glow2_draw = ImageDraw.Draw(text_glow2)
        for offset in [(2, 2), (1, 1), (-1, -1), (-2, -2)]:
            text_glow2_draw.text(
                (player_text_x + offset[0], player_text_y + offset[1]),
                player_text,
                fill=accent_color + (100,),
                font=self.font_title
            )
        text_glow2 = text_glow2.filter(ImageFilter.GaussianBlur(radius=3))
        image = Image.alpha_composite(image, text_glow2)
        draw = ImageDraw.Draw(image)

        draw.text((player_text_x, player_text_y), player_text,
                 fill=(255, 255, 255), font=self.font_title)

        # 플레이어 카드
        cards_y = player_y + 140
        x_offset = 100

        for card_str in player_hand:
            # "BACK" 카드는 뒷면으로 표시
            if card_str == "BACK":
                card_img = self._create_casino_card_back()
            else:
                card_img = self._create_casino_card_front(card_str)
            card_with_shadow = self._add_dramatic_shadow(card_img)
            image.paste(card_with_shadow, (x_offset, cards_y), card_with_shadow)
            x_offset += card_visual_width + self.CARD_SPACING

        # 플레이어 값
        chip = self._create_value_chip(f"합: {player_value}")
        chip_x = total_width - chip.width - 120
        chip_y = cards_y + (self.CARD_HEIGHT - chip.height) // 2
        image.paste(chip, (chip_x, chip_y), chip)

        # 메시지 (네온 스타일)
        if message_lines:
            msg_y = player_y + panel_height + 20
            msg_panel_height = len(message_lines) * 52 + 70

            # 베이스 패널
            msg_panel = Image.new('RGBA', (panel_width, msg_panel_height), (0, 0, 0, 0))
            msg_draw = ImageDraw.Draw(msg_panel)
            msg_draw.rounded_rectangle(
                [(0, 0), (panel_width, msg_panel_height)],
                radius=25,
                fill=(10, 10, 20, 230)
            )

            # 네온 글로우 (별도 레이어, 축소)
            msg_glow = Image.new('RGBA', (panel_width, msg_panel_height), (0, 0, 0, 0))
            msg_glow_draw = ImageDraw.Draw(msg_glow)
            for i in range(4, 0, -1):
                alpha = int(35 - i * 6)
                msg_glow_draw.rounded_rectangle(
                    [(0, 0), (panel_width, msg_panel_height)],
                    radius=25,
                    outline=border_color + (alpha,),
                    width=i * 2
                )
            msg_glow = msg_glow.filter(ImageFilter.GaussianBlur(radius=5))
            msg_panel = Image.alpha_composite(msg_panel, msg_glow)

            # 테두리
            msg_draw = ImageDraw.Draw(msg_panel)
            msg_draw.rounded_rectangle(
                [(0, 0), (panel_width, msg_panel_height)],
                radius=25,
                outline=border_color,
                width=3
            )
            msg_draw.rounded_rectangle(
                [(3, 3), (panel_width - 3, msg_panel_height - 3)],
                radius=23,
                outline=accent_color + (120,),
                width=1
            )

            # 텍스트
            for i, line in enumerate(message_lines):
                msg_draw.text(
                    (45, 25 + i * 52),
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
        """네온 스타일 값 칩"""
        width, height = 250, 85
        chip = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(chip)

        border_color = self.theme.colors.border_color
        accent_color = self.theme.colors.accent_color

        # 네온 글로우
        for i in range(8, 0, -1):
            alpha = int(70 - i * 7)
            draw.rounded_rectangle(
                [(0, 0), (width, height)],
                radius=38,
                outline=accent_color + (alpha,),
                width=i * 2
            )
        chip = chip.filter(ImageFilter.GaussianBlur(radius=8))

        draw = ImageDraw.Draw(chip)

        # 다크 그라데이션 배경
        bg = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg)
        for y in range(height):
            ratio = y / height
            alpha = int(200 + 55 * ratio)
            bg_draw.line([(0, y), (width, y)], fill=(15, 15, 25, alpha))

        # 라운드 마스크
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (width, height)], radius=38, fill=255)

        result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        result.paste(bg, (0, 0), mask)
        chip = Image.alpha_composite(chip, result)

        draw = ImageDraw.Draw(chip)
        draw.rounded_rectangle(
            [(0, 0), (width - 1, height - 1)],
            radius=38,
            outline=accent_color,
            width=3
        )
        draw.rounded_rectangle(
            [(3, 3), (width - 4, height - 4)],
            radius=36,
            outline=border_color + (180,),
            width=1
        )

        # 텍스트 글로우
        bbox = draw.textbbox((0, 0), text, font=self.font_value)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2 - 5

        # 글로우 효과
        for offset in [(2, 2), (1, 1), (-1, -1), (-2, -2)]:
            draw.text(
                (text_x + offset[0], text_y + offset[1]),
                text,
                fill=accent_color + (120,),
                font=self.font_value
            )

        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=self.font_value)

        return chip


_casino_renderers = {}


def get_casino_renderer(theme: Optional[Theme] = None) -> CasinoCardRenderer:
    """카지노 렌더러 가져오기"""
    theme_name = theme.name if theme else "Classic"

    if theme_name not in _casino_renderers:
        _casino_renderers[theme_name] = CasinoCardRenderer(theme)

    return _casino_renderers[theme_name]
