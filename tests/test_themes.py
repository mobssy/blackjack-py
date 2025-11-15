"""
테마 시스템 테스트
"""

import pytest
from bot.utils.themes import ThemeManager, ThemeType, Theme


class TestThemeManager:
    """ThemeManager 테스트"""

    def test_get_classic_theme(self):
        """클래식 테마 가져오기 테스트 (모던 다크 네온)"""
        theme = ThemeManager.get_theme(ThemeType.CLASSIC)

        assert theme is not None
        assert theme.name == "Classic"
        assert theme.colors.background == (15, 15, 20)  # 모던 다크로 업데이트됨
        assert theme.has_gradient is True  # 그라데이션 활성화됨

    def test_get_dark_theme(self):
        """다크 테마 가져오기 테스트"""
        theme = ThemeManager.get_theme(ThemeType.DARK)

        assert theme is not None
        assert theme.name == "Dark"
        assert theme.colors.background == (18, 18, 18)
        assert theme.has_gradient is True

    def test_get_luxury_theme(self):
        """럭셔리 테마 가져오기 테스트"""
        theme = ThemeManager.get_theme(ThemeType.LUXURY)

        assert theme is not None
        assert theme.name == "Luxury"
        assert theme.colors.background == (10, 10, 30)
        assert theme.has_gradient is True

    def test_get_theme_by_plan_free(self):
        """무료 플랜 테마 테스트"""
        theme = ThemeManager.get_theme_by_plan(is_vip=False, is_business=False)

        assert theme.name == "Classic"

    def test_get_theme_by_plan_vip(self):
        """VIP 플랜 테마 테스트"""
        theme = ThemeManager.get_theme_by_plan(is_vip=True, is_business=False)

        assert theme.name == "Dark"

    def test_get_theme_by_plan_business(self):
        """비즈니스 플랜 테마 테스트"""
        theme = ThemeManager.get_theme_by_plan(is_vip=False, is_business=True)

        assert theme.name == "Luxury"

    def test_theme_colors_are_rgb_tuples(self):
        """테마 색상이 RGB 튜플인지 테스트"""
        for theme_type in [ThemeType.CLASSIC, ThemeType.DARK, ThemeType.LUXURY]:
            theme = ThemeManager.get_theme(theme_type)

            assert isinstance(theme.colors.background, tuple)
            assert len(theme.colors.background) == 3
            assert all(0 <= c <= 255 for c in theme.colors.background)

            assert isinstance(theme.colors.text_color, tuple)
            assert len(theme.colors.text_color) == 3
            assert all(0 <= c <= 255 for c in theme.colors.text_color)

    def test_card_shadow_is_rgba(self):
        """카드 그림자가 RGBA 튜플인지 테스트"""
        theme = ThemeManager.get_theme(ThemeType.CLASSIC)

        assert isinstance(theme.colors.card_shadow, tuple)
        assert len(theme.colors.card_shadow) == 4
        assert all(0 <= c <= 255 for c in theme.colors.card_shadow)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
