"""
개선된 카드 이미지 생성 테스트
"""
import pytest
from pathlib import Path
from PIL import Image
import io
from bot.utils.enhanced_card_image import (
    EnhancedCardImageGenerator,
    get_enhanced_card_generator
)
from bot.utils.themes import ThemeManager, ThemeType


class TestEnhancedCardImageGenerator:
    """EnhancedCardImageGenerator 테스트"""

    def test_generator_initialization(self):
        """생성기 초기화 테스트"""
        gen = EnhancedCardImageGenerator()

        assert gen is not None
        assert gen.theme is not None
        assert gen.cards_dir.exists()

    def test_generator_with_theme(self):
        """테마 적용 생성기 테스트"""
        theme = ThemeManager.get_theme(ThemeType.DARK)
        gen = EnhancedCardImageGenerator(theme)

        assert gen.theme.name == "Dark"

    def test_card_image_path_conversion(self):
        """카드 경로 변환 테스트"""
        gen = EnhancedCardImageGenerator()

        # AS -> ace_of_spades.png
        path = gen._get_card_image_path("AS")
        assert path is not None
        assert "ace_of_spades" in str(path)

        # KH -> king_of_hearts.png
        path = gen._get_card_image_path("KH")
        assert path is not None
        assert "king_of_hearts" in str(path)

    def test_generate_game_image(self):
        """게임 이미지 생성 테스트"""
        gen = EnhancedCardImageGenerator()

        player_hand = ["AS", "KH"]
        dealer_hand = ["7D", "8C"]

        image_bytes = gen.generate_game_image(
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            player_value=21,
            dealer_value=15,
            hide_dealer_first=False,
            message="Test message"
        )

        assert image_bytes is not None
        assert len(image_bytes) > 0

        # 이미지 유효성 확인
        img = Image.open(io.BytesIO(image_bytes))
        assert img.format == "PNG"
        assert img.size[0] > 0
        assert img.size[1] > 0

    def test_generate_game_image_with_hidden_card(self):
        """숨겨진 카드가 있는 게임 이미지 생성 테스트"""
        gen = EnhancedCardImageGenerator()

        player_hand = ["AS", "KH"]
        dealer_hand = ["7D", "8C"]

        image_bytes = gen.generate_game_image(
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            player_value=21,
            dealer_value=None,
            hide_dealer_first=True,
            message="Dealer's first card is hidden"
        )

        assert image_bytes is not None
        assert len(image_bytes) > 0

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        gen1 = get_enhanced_card_generator()
        gen2 = get_enhanced_card_generator()

        assert gen1 is gen2

    def test_theme_specific_generators(self):
        """테마별 생성기 테스트"""
        theme_dark = ThemeManager.get_theme(ThemeType.DARK)
        theme_luxury = ThemeManager.get_theme(ThemeType.LUXURY)

        gen_dark = get_enhanced_card_generator(theme_dark)
        gen_luxury = get_enhanced_card_generator(theme_luxury)

        assert gen_dark is not gen_luxury
        assert gen_dark.theme.name == "Dark"
        assert gen_luxury.theme.name == "Luxury"

    def test_gradient_background(self):
        """그라데이션 배경 생성 테스트"""
        theme = ThemeManager.get_theme(ThemeType.DARK)
        gen = EnhancedCardImageGenerator(theme)

        bg = gen._create_gradient_background(800, 600)

        assert bg is not None
        assert bg.size == (800, 600)
        assert bg.mode == "RGB"

    def test_card_shadow(self):
        """카드 그림자 추가 테스트"""
        gen = EnhancedCardImageGenerator()

        # 간단한 카드 이미지 생성
        card = Image.new('RGBA', (160, 240), (255, 255, 255))

        card_with_shadow = gen._add_card_shadow(card)

        assert card_with_shadow is not None
        # 그림자가 추가되어 크기가 커짐
        assert card_with_shadow.size[0] > card.size[0]
        assert card_with_shadow.size[1] > card.size[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
