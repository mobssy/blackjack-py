"""
JackPy - 카드 이미지 생성
PIL을 사용하여 카드 이미지 생성
"""

from PIL import Image, ImageDraw, ImageFont
from typing import List
import io


class CardImageGenerator:
    """카드 이미지 생성기"""

    # 카드 크기
    CARD_WIDTH = 140
    CARD_HEIGHT = 200
    CARD_SPACING = 20

    # 색상
    COLOR_RED = (220, 20, 60)
    COLOR_BLACK = (40, 40, 40)
    COLOR_WHITE = (255, 255, 255)
    COLOR_BACKGROUND = (34, 139, 34)  # 녹색 배경

    # 무늬별 색상
    SUIT_COLORS = {
        "S": COLOR_BLACK,  # 스페이드
        "C": COLOR_BLACK,  # 클로버
        "H": COLOR_RED,  # 하트
        "D": COLOR_RED,  # 다이아몬드
    }

    # 무늬 유니코드
    SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}

    def __init__(self):
        """초기화"""
        try:
            # 시스템 폰트 사용
            self.font_large = ImageFont.truetype(
                "/System/Library/Fonts/Helvetica.ttc", 60
            )
            self.font_small = ImageFont.truetype(
                "/System/Library/Fonts/Helvetica.ttc", 40
            )
            self.font_suit = ImageFont.truetype(
                "/System/Library/Fonts/Helvetica.ttc", 80
            )
        except:
            # 폰트 로드 실패 시 기본 폰트
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_suit = ImageFont.load_default()

    def draw_single_card(self, card_str: str, hidden: bool = False) -> Image.Image:
        """
        단일 카드 이미지 생성

        Args:
            card_str: 카드 문자열 (예: "AS", "KH")
            hidden: 뒷면 표시 여부

        Returns:
            PIL Image 객체
        """
        # 카드 배경 생성
        card = Image.new("RGBA", (self.CARD_WIDTH, self.CARD_HEIGHT), self.COLOR_WHITE)
        draw = ImageDraw.Draw(card)

        if hidden:
            # 뒷면 카드
            # 테두리
            draw.rectangle(
                [(5, 5), (self.CARD_WIDTH - 5, self.CARD_HEIGHT - 5)],
                fill=(50, 50, 150),
                outline=self.COLOR_BLACK,
                width=3,
            )
            # 패턴
            for i in range(0, self.CARD_WIDTH, 20):
                draw.line([(i, 0), (i, self.CARD_HEIGHT)], fill=(70, 70, 170), width=2)
            for i in range(0, self.CARD_HEIGHT, 20):
                draw.line([(0, i), (self.CARD_WIDTH, i)], fill=(70, 70, 170), width=2)
        else:
            # 앞면 카드
            rank = card_str[:-1]
            suit = card_str[-1]
            color = self.SUIT_COLORS.get(suit, self.COLOR_BLACK)
            suit_symbol = self.SUIT_SYMBOLS.get(suit, suit)

            # 카드 테두리
            draw.rounded_rectangle(
                [(2, 2), (self.CARD_WIDTH - 2, self.CARD_HEIGHT - 2)],
                radius=10,
                fill=self.COLOR_WHITE,
                outline=self.COLOR_BLACK,
                width=3,
            )

            # 랭크 (좌상단)
            draw.text((15, 10), rank, fill=color, font=self.font_small)

            # 무늬 중앙
            # 텍스트 크기 계산
            bbox = draw.textbbox((0, 0), suit_symbol, font=self.font_suit)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x = (self.CARD_WIDTH - text_width) // 2
            y = (self.CARD_HEIGHT - text_height) // 2 - 10
            draw.text((x, y), suit_symbol, fill=color, font=self.font_suit)

            # 랭크 (우하단, 거꾸로)
            draw.text(
                (self.CARD_WIDTH - 35, self.CARD_HEIGHT - 50),
                rank,
                fill=color,
                font=self.font_small,
            )

        return card

    def generate_hand_image(
        self, cards: List[str], hide_first: bool = False, title: str = ""
    ) -> bytes:
        """
        핸드 전체 이미지 생성

        Args:
            cards: 카드 리스트 (예: ["AS", "KH", "7D"])
            hide_first: 첫 카드 숨김 여부
            title: 제목 (예: "플레이어", "딜러")

        Returns:
            PNG 이미지 바이트
        """
        # 전체 이미지 크기 계산
        num_cards = len(cards)
        total_width = (
            num_cards * self.CARD_WIDTH + (num_cards - 1) * self.CARD_SPACING + 40
        )
        total_height = self.CARD_HEIGHT + 100  # 제목 공간

        # 배경 생성
        image = Image.new("RGBA", (total_width, total_height), self.COLOR_BACKGROUND)
        draw = ImageDraw.Draw(image)

        # 제목 그리기
        if title:
            draw.text((20, 20), title, fill=self.COLOR_WHITE, font=self.font_large)

        # 카드 배치
        x_offset = 20
        y_offset = 80

        for i, card_str in enumerate(cards):
            hidden = i == 0 and hide_first
            card_img = self.draw_single_card(card_str, hidden)
            image.paste(card_img, (x_offset, y_offset))
            x_offset += self.CARD_WIDTH + self.CARD_SPACING

        # 이미지를 바이트로 변환
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    def generate_game_image(
        self,
        player_hand: List[str],
        dealer_hand: List[str],
        player_value: int,
        dealer_value: int = None,
        hide_dealer_first: bool = True,
        message: str = "",
        game_result: str = None,  # "WIN", "LOSE", "PUSH", "BLACKJACK"
    ) -> bytes:
        """
        게임 전체 이미지 생성 (플레이어 + 딜러)

        Args:
            player_hand: 플레이어 카드
            dealer_hand: 딜러 카드
            player_value: 플레이어 핸드 값
            dealer_value: 딜러 핸드 값
            hide_dealer_first: 딜러 첫 카드 숨김
            message: 하단 메시지
            game_result: 게임 결과 ("WIN", "LOSE", "PUSH", "BLACKJACK")

        Returns:
            PNG 이미지 바이트
        """
        # 각 핸드의 최대 너비 계산
        max_cards = max(len(player_hand), len(dealer_hand))
        card_area_width = (
            max_cards * self.CARD_WIDTH + (max_cards - 1) * self.CARD_SPACING + 40
        )

        total_width = max(card_area_width, 600)
        total_height = (self.CARD_HEIGHT + 120) * 2 + 120  # 딜러 + 플레이어 + 메시지 + 결과

        # 배경색 (결과에 따라 변경)
        bg_color = self.COLOR_BACKGROUND
        if game_result == "WIN" or game_result == "BLACKJACK":
            bg_color = (20, 100, 20)  # 진한 녹색
        elif game_result == "LOSE":
            bg_color = (100, 20, 20)  # 진한 빨간색

        # 배경
        image = Image.new("RGBA", (total_width, total_height), bg_color)
        draw = ImageDraw.Draw(image)

        # 딜러 섹션
        y_offset = 20
        draw.text((20, y_offset), "🃏 딜러", fill=self.COLOR_WHITE, font=self.font_large)
        y_offset += 60

        # 딜러 카드
        x_offset = 20
        for i, card_str in enumerate(dealer_hand):
            hidden = i == 0 and hide_dealer_first
            card_img = self.draw_single_card(card_str, hidden)
            image.paste(card_img, (x_offset, y_offset))
            x_offset += self.CARD_WIDTH + self.CARD_SPACING

        # 딜러 값
        if dealer_value is not None:
            draw.text(
                (x_offset + 20, y_offset + 80),
                f"합: {dealer_value}",
                fill=self.COLOR_WHITE,
                font=self.font_small,
            )

        # 플레이어 섹션
        y_offset += self.CARD_HEIGHT + 60
        draw.text((20, y_offset), "🎴 플레이어", fill=self.COLOR_WHITE, font=self.font_large)
        y_offset += 60

        # 플레이어 카드
        x_offset = 20
        for card_str in player_hand:
            card_img = self.draw_single_card(card_str, False)
            image.paste(card_img, (x_offset, y_offset))
            x_offset += self.CARD_WIDTH + self.CARD_SPACING

        # 플레이어 값
        draw.text(
            (x_offset + 20, y_offset + 80),
            f"합: {player_value}",
            fill=self.COLOR_WHITE,
            font=self.font_small,
        )

        # 하단 메시지
        if message:
            y_offset += self.CARD_HEIGHT + 40
            draw.text(
                (20, y_offset), message, fill=self.COLOR_WHITE, font=self.font_small
            )

        # 게임 결과 표시 (큰 텍스트)
        if game_result:
            result_text = ""
            result_color = self.COLOR_WHITE

            if game_result == "BLACKJACK":
                result_text = "★ BLACKJACK ★"
                result_color = (255, 215, 0)  # 금색
            elif game_result == "WIN":
                result_text = "YOU WIN!"
                result_color = (50, 255, 50)  # 밝은 녹색
            elif game_result == "LOSE":
                result_text = "YOU LOSE"
                result_color = (255, 50, 50)  # 밝은 빨간색
            elif game_result == "PUSH":
                result_text = "PUSH"
                result_color = (200, 200, 200)  # 회색

            # 결과 텍스트 크기 계산 및 중앙 배치
            try:
                result_font = ImageFont.truetype(
                    "/System/Library/Fonts/Helvetica.ttc", 100
                )
            except:
                result_font = self.font_suit

            bbox = draw.textbbox((0, 0), result_text, font=result_font)
            text_width = bbox[2] - bbox[0]
            text_x = (total_width - text_width) // 2
            text_y = total_height // 2 - 50

            # 반투명 배경 박스
            padding = 30
            box_coords = [
                (text_x - padding, text_y - padding),
                (text_x + text_width + padding, text_y + 100),
            ]
            draw.rectangle(
                box_coords, fill=(0, 0, 0, 200), outline=result_color, width=5
            )

            # 결과 텍스트
            draw.text(
                (text_x, text_y), result_text, fill=result_color, font=result_font
            )

        # 이미지를 바이트로 변환
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()


# 전역 인스턴스
_card_generator = None


def get_card_generator() -> CardImageGenerator:
    """카드 생성기 싱글톤"""
    global _card_generator
    if _card_generator is None:
        _card_generator = CardImageGenerator()
    return _card_generator
