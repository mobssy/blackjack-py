"""
JackPy - 테마 시스템
다크 모드, 럭셔리 모드 등 다양한 테마 지원
"""

from enum import Enum
from typing import Tuple
from dataclasses import dataclass


class ThemeType(Enum):
    """테마 타입"""

    CLASSIC = "classic"
    DARK = "dark"
    LUXURY = "luxury"


@dataclass
class ColorScheme:
    """
    색상 스키마

    Attributes:
        background: 배경색 (R, G, B)
        table_color: 테이블 색상
        text_color: 텍스트 색상
        border_color: 테두리 색상
        accent_color: 강조 색상
        card_shadow: 카드 그림자 색상
    """

    background: Tuple[int, int, int]
    table_color: Tuple[int, int, int]
    text_color: Tuple[int, int, int]
    border_color: Tuple[int, int, int]
    accent_color: Tuple[int, int, int]
    card_shadow: Tuple[int, int, int, int]  # RGBA


@dataclass
class Theme:
    """
    테마 설정

    Attributes:
        name: 테마 이름
        colors: 색상 스키마
        card_style: 카드 스타일 (modern, classic)
        font_name: 폰트 이름
        has_gradient: 그라데이션 사용 여부
    """

    name: str
    colors: ColorScheme
    card_style: str
    font_name: str
    has_gradient: bool


class ThemeManager:
    """테마 관리자"""

    # 모던 다크 테마 (업그레이드된 기본 테마)
    CLASSIC = Theme(
        name="Classic",
        colors=ColorScheme(
            background=(15, 15, 20),  # 딥 블랙
            table_color=(25, 28, 35),  # 다크 차콜
            text_color=(255, 255, 255),
            border_color=(0, 229, 255),  # 시안 네온
            accent_color=(138, 43, 226),  # 바이올렛 네온
            card_shadow=(0, 229, 255, 120),  # 시안 글로우
        ),
        card_style="modern",
        font_name="Arial",
        has_gradient=True,
    )

    # 다크 테마
    DARK = Theme(
        name="Dark",
        colors=ColorScheme(
            background=(18, 18, 18),  # 다크 그레이
            table_color=(28, 28, 30),  # 조금 밝은 그레이
            text_color=(255, 255, 255),
            border_color=(142, 142, 147),  # 미디엄 그레이
            accent_color=(94, 92, 230),  # 보라색 액센트
            card_shadow=(0, 0, 0, 150),
        ),
        card_style="modern",
        font_name="Arial",
        has_gradient=True,
    )

    # 럭셔리 테마
    LUXURY = Theme(
        name="Luxury",
        colors=ColorScheme(
            background=(10, 10, 30),  # 딥 네이비
            table_color=(25, 25, 60),  # 로얄 블루
            text_color=(255, 223, 186),  # 크림 골드
            border_color=(212, 175, 55),  # 골드
            accent_color=(255, 215, 0),  # 브라이트 골드
            card_shadow=(212, 175, 55, 80),  # 골드 섀도우
        ),
        card_style="luxury",
        font_name="Arial",
        has_gradient=True,
    )

    @staticmethod
    def get_theme(theme_type: ThemeType) -> Theme:
        """
        테마 가져오기

        Args:
            theme_type: 테마 타입

        Returns:
            Theme: 테마 객체
        """
        themes = {
            ThemeType.CLASSIC: ThemeManager.CLASSIC,
            ThemeType.DARK: ThemeManager.DARK,
            ThemeType.LUXURY: ThemeManager.LUXURY,
        }
        return themes.get(theme_type, ThemeManager.CLASSIC)

    @staticmethod
    def get_theme_by_plan(is_vip: bool, is_business: bool) -> Theme:
        """
        플랜에 따른 테마 자동 선택

        Args:
            is_vip: VIP 여부
            is_business: 비즈니스 플랜 여부

        Returns:
            Theme: 테마 객체
        """
        if is_business:
            return ThemeManager.LUXURY
        elif is_vip:
            return ThemeManager.DARK
        else:
            return ThemeManager.CLASSIC
