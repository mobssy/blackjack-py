"""
JackPy - 1인 게임 카드 렌더러 테스트
카드 PNG가 골드 테두리 안쪽에 비율을 유지한 채 배치되는지 확인
"""

from PIL import Image

from bot.utils.casino_card_renderer import CasinoCardRenderer, get_casino_renderer
from bot.utils.deck import Card

_ALL_CARDS = [f"{rank}{suit}" for suit in Card.SUITS for rank in Card.RANKS]


def _art(width=266, height=376):
    """카드 PNG 모양: 반투명 외곽선 + 흰 바탕 + 왼쪽 위 모서리 숫자 자리(검정)"""
    art = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    for x in range(width):
        art.putpixel((x, 0), (229, 229, 229, 200))
        art.putpixel((x, 2), (255, 255, 255, 238))
    art.paste((0, 0, 0, 255), (8, 8, 30, 40))
    return art


def test_card_image_has_card_size():
    renderer = get_casino_renderer()
    for card in ("10D", "AS", "KH"):
        image = renderer.card_image(card)
        assert image.size == (
            CasinoCardRenderer.CARD_WIDTH,
            CasinoCardRenderer.CARD_HEIGHT,
        )


def test_card_interior_is_opaque_for_every_card():
    # 그림 경계의 반투명 픽셀이 카드에 구멍(배경이 비치는 줄)을 내면 안 된다
    renderer = get_casino_renderer()
    inset = CasinoCardRenderer._ART_INSET
    for card in _ALL_CARDS:
        image = renderer.card_image(card)
        interior = image.crop((inset, inset, image.width - inset, image.height - inset))
        assert interior.getextrema()[3] == (255, 255), card


def test_fit_card_art_keeps_aspect_ratio():
    renderer = get_casino_renderer()
    fitted = renderer._fit_card_art(_art())
    dark = fitted.convert("L").point(lambda v: 255 if v < 128 else 0).getbbox()
    width, height = dark[2] - dark[0], dark[3] - dark[1]
    # 원본 22x32 영역이 같은 배율로 줄어야 함 (늘려서 찌그러뜨리지 않음)
    assert abs(width / height - 22 / 32) < 0.08


def test_fit_card_art_keeps_corner_index_inside_frame():
    # 모서리 숫자가 골드 테두리(바깥 15px)에 가려지지 않아야 한다
    renderer = get_casino_renderer()
    fitted = renderer._fit_card_art(_art())
    dark = fitted.convert("L").point(lambda v: 255 if v < 128 else 0).getbbox()
    assert dark[0] >= CasinoCardRenderer._ART_INSET
    assert dark[1] >= CasinoCardRenderer._ART_INSET


def test_card_corners_stay_transparent():
    # 광택 효과가 둥근 모서리 바깥에 번져 테이블 위에 흰 얼룩이 생기면 안 된다
    renderer = get_casino_renderer()
    for card in ("7C", "10D", "KH"):
        image = renderer.card_image(card)
        right, bottom = image.width - 1, image.height - 1
        for corner in ((0, 0), (right, 0), (0, bottom), (right, bottom)):
            assert image.getpixel(corner)[3] == 0, (card, corner)


def test_face_down_cards_share_one_cached_back():
    # 뒷면은 어떤 카드든 같은 그림 — 카드마다 따로 캐시하지 않는다
    renderer = get_casino_renderer()
    assert renderer.scaled_card("AS", True, 0.5) is renderer.scaled_card(
        "KD", True, 0.5
    )
    assert renderer.scaled_card("AS", False, 0.5) is not renderer.scaled_card(
        "AS", True, 0.5
    )
