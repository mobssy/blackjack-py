"""
JackPy - 광고 시스템
무료 플랜 그룹의 광고 표시 관리
"""

import random
from typing import Optional


class AdManager:
    """
    광고 관리자

    무료 플랜 그룹에서 일정 확률로 광고를 표시합니다.
    """

    # 광고 메시지 템플릿
    AD_MESSAGES = [
        "JackPy를 즐겨주셔서 감사합니다!",
        "매일 접속하여 일일 보상을 받아가세요!",
        "친구들과 함께 블랙잭을 즐기세요!",
        "행운을 빕니다!",
    ]

    # 광고 표시 확률 (0.0 ~ 1.0)
    DEFAULT_AD_PROBABILITY = 0.15  # 15%

    def __init__(self, probability: float = DEFAULT_AD_PROBABILITY):
        """
        광고 매니저 초기화

        Args:
            probability: 광고 표시 확률 (0.0 ~ 1.0)
        """
        self.probability = probability

    def should_show_ad(self) -> bool:
        """
        광고 표시 여부 결정

        Returns:
            bool: 광고 표시 여부
        """
        return random.random() < self.probability

    def get_ad_message(self) -> str:
        """
        랜덤 광고 메시지 가져오기

        Returns:
            str: 광고 메시지
        """
        return random.choice(self.AD_MESSAGES)

    def format_ad(self) -> str:
        """
        포맷팅된 광고 메시지

        Returns:
            str: 포맷팅된 광고
        """
        message = self.get_ad_message()
        return f"\n\n───────────────\n{message}\n───────────────"


_default_ad_manager = AdManager()


def get_ad_footer(show_ad: bool = False) -> str:
    """
    게임 결과에 광고 푸터 추가

    Args:
        show_ad: 광고 표시 여부

    Returns:
        str: 광고 푸터 (또는 빈 문자열)
    """
    if show_ad:
        return _default_ad_manager.format_ad()
    return ""


def should_show_game_ad(
    is_free_plan: bool, ad_probability: Optional[float] = None
) -> bool:
    """
    게임 후 광고 표시 여부 결정

    Args:
        is_free_plan: 무료 플랜 여부
        ad_probability: 커스텀 광고 확률 (선택)

    Returns:
        bool: 광고 표시 여부
    """
    if not is_free_plan:
        return False

    manager = AdManager(ad_probability) if ad_probability else _default_ad_manager
    return manager.should_show_ad()
