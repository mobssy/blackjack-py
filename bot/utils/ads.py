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
        "💎 VIP로 업그레이드하고 광고 없이 즐기세요! /vip",
        "🎯 비즈니스 플랜으로 그룹을 커스터마이징하세요! /business",
        "⚡️ VIP 회원만의 특별한 혜택을 누리세요! /vip",
        "🌟 월 $30로 VIP의 모든 기능을 이용하세요! /vip",
        "🏢 비즈니스 플랜: 월 $300로 완전한 브랜딩 가능! /business",
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


def get_ad_footer(show_ad: bool = False) -> str:
    """
    게임 결과에 광고 푸터 추가

    Args:
        show_ad: 광고 표시 여부

    Returns:
        str: 광고 푸터 (또는 빈 문자열)
    """
    if show_ad:
        ad_manager = AdManager()
        return ad_manager.format_ad()
    return ""


def should_show_game_ad(is_free_plan: bool, ad_probability: Optional[float] = None) -> bool:
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

    probability = ad_probability or AdManager.DEFAULT_AD_PROBABILITY
    ad_manager = AdManager(probability)
    return ad_manager.should_show_ad()
