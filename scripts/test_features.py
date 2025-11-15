"""
개선된 기능 테스트 스크립트
pytest 없이 기본 테스트 실행
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_themes():
    """테마 시스템 테스트"""
    print("🎨 테마 시스템 테스트...")

    from bot.utils.themes import ThemeManager, ThemeType

    # Classic 테마
    theme = ThemeManager.get_theme(ThemeType.CLASSIC)
    assert theme.name == "Classic", "Classic 테마 이름 오류"
    assert theme.has_gradient is False, "Classic 테마 그라데이션 오류"
    print("  ✅ Classic 테마: OK")

    # Dark 테마
    theme = ThemeManager.get_theme(ThemeType.DARK)
    assert theme.name == "Dark", "Dark 테마 이름 오류"
    assert theme.has_gradient is True, "Dark 테마 그라데이션 오류"
    print("  ✅ Dark 테마: OK")

    # Luxury 테마
    theme = ThemeManager.get_theme(ThemeType.LUXURY)
    assert theme.name == "Luxury", "Luxury 테마 이름 오류"
    assert theme.has_gradient is True, "Luxury 테마 그라데이션 오류"
    print("  ✅ Luxury 테마: OK")

    # 플랜별 테마
    theme = ThemeManager.get_theme_by_plan(False, False)
    assert theme.name == "Classic", "무료 플랜 테마 오류"
    print("  ✅ 무료 플랜 테마: OK")

    theme = ThemeManager.get_theme_by_plan(True, False)
    assert theme.name == "Dark", "VIP 플랜 테마 오류"
    print("  ✅ VIP 플랜 테마: OK")

    theme = ThemeManager.get_theme_by_plan(False, True)
    assert theme.name == "Luxury", "비즈니스 플랜 테마 오류"
    print("  ✅ 비즈니스 플랜 테마: OK")

    print("✅ 테마 시스템 테스트 완료!\n")


def test_enhanced_card_image():
    """개선된 카드 이미지 생성 테스트"""
    print("🃏 카드 이미지 생성 테스트...")

    from bot.utils.enhanced_card_image import (
        EnhancedCardImageGenerator,
        get_enhanced_card_generator
    )
    from bot.utils.themes import ThemeManager, ThemeType

    # 생성기 초기화
    gen = EnhancedCardImageGenerator()
    assert gen is not None, "생성기 초기화 오류"
    print("  ✅ 생성기 초기화: OK")

    # 카드 경로 변환
    path = gen._get_card_image_path("AS")
    assert path is not None, "카드 경로 변환 오류"
    assert "ace_of_spades" in str(path), "카드 경로 이름 오류"
    print("  ✅ 카드 경로 변환: OK")

    # 게임 이미지 생성
    player_hand = ["AS", "KH"]
    dealer_hand = ["7D", "8C"]

    image_bytes = gen.generate_game_image(
        player_hand=player_hand,
        dealer_hand=dealer_hand,
        player_value=21,
        dealer_value=15,
        hide_dealer_first=False,
        message="Test"
    )

    assert image_bytes is not None, "이미지 생성 오류"
    assert len(image_bytes) > 0, "이미지 크기 오류"
    print("  ✅ 게임 이미지 생성: OK")

    # 싱글톤 패턴
    gen1 = get_enhanced_card_generator()
    gen2 = get_enhanced_card_generator()
    assert gen1 is gen2, "싱글톤 패턴 오류"
    print("  ✅ 싱글톤 패턴: OK")

    # 테마별 생성기
    theme_dark = ThemeManager.get_theme(ThemeType.DARK)
    theme_luxury = ThemeManager.get_theme(ThemeType.LUXURY)

    gen_dark = get_enhanced_card_generator(theme_dark)
    gen_luxury = get_enhanced_card_generator(theme_luxury)

    assert gen_dark is not gen_luxury, "테마별 생성기 오류"
    assert gen_dark.theme.name == "Dark", "Dark 생성기 테마 오류"
    assert gen_luxury.theme.name == "Luxury", "Luxury 생성기 테마 오류"
    print("  ✅ 테마별 생성기: OK")

    print("✅ 카드 이미지 생성 테스트 완료!\n")


def test_card_animation():
    """카드 애니메이션 테스트"""
    print("🎬 카드 애니메이션 테스트...")

    from bot.utils.card_animation import (
        CardAnimationGenerator,
        get_animation_generator
    )

    # 생성기 초기화
    gen = CardAnimationGenerator()
    assert gen is not None, "애니메이션 생성기 초기화 오류"
    print("  ✅ 애니메이션 생성기 초기화: OK")

    # 뒤집기 애니메이션 생성
    gif_bytes = gen.create_flip_animation("AS", frames=5, duration=100)
    assert gif_bytes is not None, "뒤집기 애니메이션 생성 오류"
    assert len(gif_bytes) > 0, "뒤집기 애니메이션 크기 오류"
    print("  ✅ 뒤집기 애니메이션: OK")

    # 딜 애니메이션 생성
    gif_bytes = gen.create_deal_animation(["AS", "KH"], frames_per_card=3, duration=100)
    assert gif_bytes is not None, "딜 애니메이션 생성 오류"
    assert len(gif_bytes) > 0, "딜 애니메이션 크기 오류"
    print("  ✅ 딜 애니메이션: OK")

    # 싱글톤 패턴
    gen1 = get_animation_generator()
    gen2 = get_animation_generator()
    assert gen1 is gen2, "애니메이션 생성기 싱글톤 패턴 오류"
    print("  ✅ 싱글톤 패턴: OK")

    print("✅ 카드 애니메이션 테스트 완료!\n")


def test_payouts():
    """정산 메시지 테스트"""
    print("💰 정산 메시지 테스트...")

    from bot.utils.payouts import PayoutCalculator
    from models.round import GameOutcome

    # 블랙잭 메시지
    msg = PayoutCalculator.get_outcome_message(GameOutcome.BLACKJACK)
    assert "블랙잭" in msg, "블랙잭 메시지 오류"
    print("  ✅ 블랙잭 메시지: OK")

    # 승리 메시지
    msg = PayoutCalculator.get_outcome_message(GameOutcome.WIN)
    assert "승리" in msg, "승리 메시지 오류"
    print("  ✅ 승리 메시지: OK")

    # 패배 메시지
    msg = PayoutCalculator.get_outcome_message(GameOutcome.LOSS)
    assert "패배" in msg, "패배 메시지 오류"
    print("  ✅ 패배 메시지: OK")

    # 무승부 메시지
    msg = PayoutCalculator.get_outcome_message(GameOutcome.PUSH)
    assert "무승부" in msg, "무승부 메시지 오류"
    print("  ✅ 무승부 메시지: OK")

    # 버스트 메시지
    msg = PayoutCalculator.get_outcome_message(GameOutcome.BUST)
    assert "버스트" in msg, "버스트 메시지 오류"
    print("  ✅ 버스트 메시지: OK")

    print("✅ 정산 메시지 테스트 완료!\n")


def main():
    """메인 함수"""
    print("=" * 50)
    print("🧪 JackPy 개선 기능 테스트")
    print("=" * 50)
    print()

    try:
        test_themes()
        test_enhanced_card_image()
        test_card_animation()
        test_payouts()

        print("=" * 50)
        print("🎉 모든 테스트 통과!")
        print("=" * 50)
        return 0

    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
