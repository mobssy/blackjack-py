"""
JackPy - 이미지 텍스트 글리프 필터 테스트
폰트에 없는 문자(이모지)가 네모로 그려지지 않도록 걸러지는지 확인
"""

from PIL import ImageFont

from bot.utils.fonts import pretendard
from bot.utils.glyph_filter import drawable_text, has_glyph


def _font(size=40):
    # Pretendard: 라틴·한글은 있고 이모지는 없음
    return pretendard(size)


def test_has_glyph_for_latin_and_digits():
    font = _font()
    for char in "Ab9$:":
        assert has_glyph(font, char)


def test_has_no_glyph_for_emoji():
    font = _font()
    for char in "🔥🤖✅":
        assert not has_glyph(font, char)


def test_drawable_text_keeps_renderable_text_unchanged():
    assert drawable_text("Bet: $100.00", _font()) == "Bet: $100.00"


def test_drawable_text_keeps_internal_spacing_when_nothing_removed():
    assert drawable_text("  a  b ", _font()) == "  a  b "


def test_drawable_text_strips_leading_emoji_and_space():
    assert drawable_text("🔥 3 win streak!", _font()) == "3 win streak!"


def test_drawable_text_collapses_gap_left_by_emoji():
    assert drawable_text("Result 🎉 Win", _font()) == "Result Win"


def test_drawable_text_drops_variation_selector():
    assert drawable_text("🛡️ Insurance", _font()) == "Insurance"


def test_drawable_text_drops_zero_width_joiner():
    """ZWJ 이모지 시퀀스 — 이모지를 지운 뒤 폭 0 문자가 남지 않아야 함"""
    assert drawable_text("👨\u200d👩\u200d👧 Family", _font()) == "Family"


def test_zero_width_chars_are_not_drawable():
    """아무것도 그리지 않는 문자는 글리프가 있어도 그릴 수 없는 문자로 취급
    (Linux FreeType은 U+FE0F를 네모 대신 빈 그림으로 그린다)"""
    font = _font()
    for char in ("\u200d", "\u200b", "\u2060", "\ufe0f"):
        assert not has_glyph(font, char)


def test_drawable_text_emoji_only_becomes_empty():
    assert drawable_text("🤖", _font()) == ""


def test_drawable_text_cache_is_per_font_size():
    assert drawable_text("Dealer 🤖", _font(20)) == "Dealer"
    assert drawable_text("Dealer 🤖", _font(60)) == "Dealer"


def test_drawable_text_passes_through_bitmap_font():
    # 폰트 로드 실패 시 쓰는 비트맵 폰트는 글리프 검사 없이 그대로 둔다
    assert drawable_text("🔥 hi", ImageFont.ImageFont()) == "🔥 hi"
