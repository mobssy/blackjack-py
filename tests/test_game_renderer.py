"""
JackPy - 펠트 게임 이미지 렌더러 테스트
출력 형식·크기, 레이아웃 보조 로직, 폰트·펠트 그리기 도구
"""

import io

from PIL import Image

from bot.utils.felt import chip, felt_background
from bot.utils.fonts import Weight, fitting_pretendard, pretendard, text_width
from bot.utils.game_renderer import (
    FACE_DOWN,
    TONE_COLORS,
    GameLayout,
    GameScene,
    HandScene,
    ResultBanner,
    Tone,
    format_bet,
    get_game_renderer,
)

_FELT = ("BLACKJACK PAYS 6 TO 5", "DEALER MUST HIT SOFT 17")


def _scene(hands, result=None, dealer_total=None, dealer=("10D", "7C")):
    return GameScene(
        dealer=list(dealer),
        dealer_total=dealer_total,
        hands=hands,
        felt_lines=_FELT,
        bet_label="BET",
        result=result,
    )


def _decode(photo: bytes):
    with Image.open(io.BytesIO(photo)) as image:
        return image.format, image.size


class TestRender:
    def test_play_scene_is_jpeg_with_layout_size(self):
        layout = GameLayout()
        photo = get_game_renderer().render(
            _scene([HandScene(cards=["9S", "QH", FACE_DOWN], total=19, bet=100)])
        )
        assert _decode(photo) == ("JPEG", (layout.width, layout.height))

    def test_result_and_split_scenes(self):
        hands = [
            HandScene(["8S", "3D", "10H"], 21, 100, outcome="핸드1 승리!", tone=Tone.WIN),
            HandScene(["8H", "9C"], 17, 100, outcome="핸드2 패배", tone=Tone.LOSS),
        ]
        result = ResultBanner("스플릿 합계", "$0.00", Tone.PUSH, ["잔액 $1,100.00"])
        photo = get_game_renderer().render(_scene(hands, result, dealer_total=26))
        assert _decode(photo)[0] == "JPEG"

    def test_many_cards_and_long_text_do_not_crash(self):
        hand = HandScene(["2S", "3H", "2D", "4C", "AH", "2C", "3D", "AS"], 18, 12345.5)
        result = ResultBanner(
            "Surrender (half returned) " * 3,
            "-$6,172.75",
            Tone.LOSS,
            ["🔥 a long detail line " * 4] * 5,
        )
        dealer = ["10D", "6C", "2H", "AC", "3S", "4D", "AH"]
        photo = get_game_renderer().render(
            _scene([hand], result, dealer_total=27, dealer=dealer)
        )
        assert _decode(photo)[0] == "JPEG"


class TestLayoutHelpers:
    def test_format_bet(self):
        assert format_bet(100) == "$100"
        assert format_bet(12345.5) == "$12,345.50"
        assert format_bet(1000000.0) == "$1,000,000"

    def test_fan_overlaps_when_cards_exceed_width(self):
        renderer = get_game_renderer()
        scale = renderer.layout.card_scale
        card_w, _ = renderer.cards.scaled_card_size(scale)
        assert renderer._fan_step(2, scale, 2000) == card_w + renderer.layout.card_gap
        assert renderer._fan_width(8, scale, 800) <= 800

    def test_detail_lines_respect_width_and_line_limit(self):
        renderer = get_game_renderer()
        font = pretendard(30, Weight.MEDIUM)
        lines = renderer._detail_lines(["Balance $1,000.00"] + ["x" * 30] * 6, font)
        assert 1 <= len(lines) <= renderer.layout.details_max_lines
        assert lines[0].startswith("Balance")

    def test_detail_lines_drop_emoji_only_items(self):
        renderer = get_game_renderer()
        font = pretendard(30, Weight.MEDIUM)
        assert renderer._detail_lines(["🔥", "Balance $5"], font) == ["Balance $5"]

    def test_every_tone_has_a_color(self):
        assert set(TONE_COLORS) == set(Tone)


class TestFontsAndFelt:
    def test_pretendard_has_korean(self):
        from bot.utils.glyph_filter import has_glyph

        assert has_glyph(pretendard(30), "딜")

    def test_fitting_font_shrinks_to_width(self):
        text = "Surrender (half returned)  -$6,172.75"
        font = fitting_pretendard(text, Weight.BOLD, 60, 400)
        assert font.size < 60
        assert text_width(font, text) <= 400 or font.size == 14

    def test_felt_background_returns_fresh_copy(self):
        first = felt_background(120, 90)
        first.putpixel((0, 0), (255, 0, 0, 255))
        assert felt_background(120, 90).getpixel((0, 0)) != (255, 0, 0, 255)

    def test_chip_size(self):
        assert chip("21", (178, 34, 46), 96).size == (96, 96)
