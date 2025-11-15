"""
JackPy - 카드 애니메이션
카드 뒤집기 애니메이션 GIF 생성
"""
from PIL import Image, ImageDraw
from typing import List
import io
from pathlib import Path


class CardAnimationGenerator:
    """
    카드 애니메이션 생성기

    Single Responsibility Principle:
    - 카드 애니메이션 생성에만 집중
    """

    def __init__(self, card_width: int = 160, card_height: int = 240):
        """
        초기화

        Args:
            card_width: 카드 너비
            card_height: 카드 높이
        """
        self.card_width = card_width
        self.card_height = card_height
        self.cards_dir = Path(__file__).parent.parent.parent / "assets" / "cards"

    def _load_card_images(self, card_str: str) -> tuple:
        """
        카드 앞면/뒷면 이미지 로드

        Args:
            card_str: 카드 문자열

        Returns:
            (front_image, back_image) 튜플
        """
        # 뒷면
        back_path = self.cards_dir / "back.png"
        if back_path.exists():
            back = Image.open(back_path).convert('RGBA')
            back = back.resize((self.card_width, self.card_height), Image.LANCZOS)
        else:
            back = self._create_back_card()

        # 앞면
        front = self._get_front_card(card_str)

        return front, back

    def _create_back_card(self) -> Image.Image:
        """뒷면 카드 생성"""
        card = Image.new('RGBA', (self.card_width, self.card_height), (255, 255, 255))
        draw = ImageDraw.Draw(card)

        draw.rounded_rectangle(
            [(0, 0), (self.card_width - 1, self.card_height - 1)],
            radius=15,
            fill=(30, 60, 150),
            outline=(20, 40, 100),
            width=3
        )

        # 패턴
        for i in range(0, self.card_width, 20):
            draw.line([(i, 0), (i, self.card_height)], fill=(50, 80, 170), width=2)
        for i in range(0, self.card_height, 20):
            draw.line([(0, i), (self.card_width, i)], fill=(50, 80, 170), width=2)

        return card

    def _get_front_card(self, card_str: str) -> Image.Image:
        """
        앞면 카드 가져오기

        Args:
            card_str: 카드 문자열

        Returns:
            앞면 카드 이미지
        """
        # 카드 파일명 변환
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

        if filepath.exists():
            card = Image.open(filepath).convert('RGBA')
            card = card.resize((self.card_width, self.card_height), Image.LANCZOS)
            return card
        else:
            # 폴백: 간단한 카드 그리기
            return self._create_simple_front_card(card_str)

    def _create_simple_front_card(self, card_str: str) -> Image.Image:
        """간단한 앞면 카드 생성 (폴백)"""
        card = Image.new('RGBA', (self.card_width, self.card_height), (255, 255, 255))
        draw = ImageDraw.Draw(card)

        draw.rounded_rectangle(
            [(0, 0), (self.card_width - 1, self.card_height - 1)],
            radius=15,
            fill=(255, 255, 255),
            outline=(0, 0, 0),
            width=3
        )

        # 간단하게 중앙에 카드 문자열 표시
        text = card_str
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.card_width - text_width) // 2
        y = (self.card_height - text_height) // 2
        draw.text((x, y), text, fill=(0, 0, 0))

        return card

    def create_flip_animation(
        self,
        card_str: str,
        frames: int = 10,
        duration: int = 50
    ) -> bytes:
        """
        카드 뒤집기 애니메이션 생성

        Args:
            card_str: 카드 문자열
            frames: 프레임 수
            duration: 각 프레임 지속 시간 (ms)

        Returns:
            GIF 이미지 바이트
        """
        front, back = self._load_card_images(card_str)

        animation_frames = []

        # 뒤집기 애니메이션 (가로로 축소했다가 확대)
        for i in range(frames):
            # 0 -> 1 (뒷면에서 앞면으로)
            ratio = i / (frames - 1)

            # 중간 지점에서 이미지 전환
            if ratio < 0.5:
                # 뒷면 축소
                current_image = back
                scale = 1.0 - (ratio * 2)  # 1.0 -> 0.0
            else:
                # 앞면 확대
                current_image = front
                scale = (ratio - 0.5) * 2  # 0.0 -> 1.0

            # 가로 축소/확대
            new_width = int(self.card_width * scale)
            new_width = max(new_width, 1)  # 최소 1픽셀

            scaled = current_image.resize(
                (new_width, self.card_height),
                Image.LANCZOS
            )

            # 중앙 배치를 위한 프레임 생성
            frame = Image.new('RGBA', (self.card_width, self.card_height), (0, 0, 0, 0))
            x_offset = (self.card_width - new_width) // 2
            frame.paste(scaled, (x_offset, 0))

            animation_frames.append(frame)

        # GIF 저장
        img_byte_arr = io.BytesIO()
        animation_frames[0].save(
            img_byte_arr,
            format='GIF',
            save_all=True,
            append_images=animation_frames[1:],
            duration=duration,
            loop=0
        )
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    def create_deal_animation(
        self,
        cards: List[str],
        frames_per_card: int = 5,
        duration: int = 100
    ) -> bytes:
        """
        카드 딜 애니메이션 생성

        Args:
            cards: 카드 리스트
            frames_per_card: 카드당 프레임 수
            duration: 프레임 지속 시간 (ms)

        Returns:
            GIF 이미지 바이트
        """
        animation_frames = []

        # 배경 크기
        total_width = len(cards) * (self.card_width + 20) + 40
        total_height = self.card_height + 40

        # 각 카드를 순차적으로 나타나게 함
        for card_idx in range(len(cards) + 1):
            for frame_idx in range(frames_per_card):
                # 배경
                frame = Image.new('RGBA', (total_width, total_height), (34, 139, 34))

                # 이미 나타난 카드들
                x_offset = 20
                for i in range(card_idx):
                    card_img = self._get_front_card(cards[i])
                    frame.paste(card_img, (x_offset, 20), card_img)
                    x_offset += self.card_width + 20

                # 현재 나타나는 카드 (페이드 인)
                if card_idx < len(cards):
                    card_img = self._get_front_card(cards[card_idx])
                    alpha = int(255 * (frame_idx / frames_per_card))
                    card_img.putalpha(alpha)
                    frame.paste(card_img, (x_offset, 20), card_img)

                animation_frames.append(frame)

        # GIF 저장
        img_byte_arr = io.BytesIO()
        animation_frames[0].save(
            img_byte_arr,
            format='GIF',
            save_all=True,
            append_images=animation_frames[1:],
            duration=duration,
            loop=0
        )
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()


# 전역 인스턴스
_animation_generator = None


def get_animation_generator() -> CardAnimationGenerator:
    """애니메이션 생성기 싱글톤"""
    global _animation_generator
    if _animation_generator is None:
        _animation_generator = CardAnimationGenerator()
    return _animation_generator
