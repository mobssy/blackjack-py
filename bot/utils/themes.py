"""
JackPy - 테마 시스템
카드 이미지 색상 테마 (현재 Classic 하나 — 확장 시 ThemeType/ThemeManager에 추가)
"""

from enum import Enum
from typing import Tuple
from dataclasses import dataclass


class ThemeType(Enum):
    """테마 타입"""

    CLASSIC = "classic"


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
        }
        return themes.get(theme_type, ThemeManager.CLASSIC)
