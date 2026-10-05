"""
JackPy - 이미지 텍스트 글리프 필터
폰트에 글리프가 없는 문자(이모지 등)는 Pillow가 네모(☒)로 그리므로,
이미지에 그리기 전에 그런 문자를 걸러낸다.
"""

import re
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

# 어떤 폰트에도 없는 사설 영역 문자 — 이 문자의 렌더링 결과가 곧 .notdef(네모) 모양
_NOTDEF_PROBE = "\U0010fffd"
_MULTI_SPACE = re.compile(r" {2,}")

_glyph_cache: Dict[Tuple[str, int, str], bool] = {}
_notdef_cache: Dict[Tuple[str, int], bytes] = {}


def _render(font: ImageFont.FreeTypeFont, char: str) -> bytes:
    """문자 하나를 고정 크기 캔버스에 그린 비트맵"""
    side = int(font.size) * 2
    canvas = Image.new("L", (side, side), 0)
    ImageDraw.Draw(canvas).text((0, 0), char, fill=255, font=font)
    return canvas.tobytes()


def _font_key(font: ImageFont.FreeTypeFont) -> Tuple[str, int]:
    return (str(font.path), int(font.size))


def has_glyph(font: ImageFont.FreeTypeFont, char: str) -> bool:
    """font가 char를 네모가 아닌 실제 글리프로 그릴 수 있는지"""
    font_key = _font_key(font)
    key = font_key + (char,)
    if key not in _glyph_cache:
        if font_key not in _notdef_cache:
            _notdef_cache[font_key] = _render(font, _NOTDEF_PROBE)
        _glyph_cache[key] = _render(font, char) != _notdef_cache[font_key]
    return _glyph_cache[key]


def drawable_text(text: str, font) -> str:
    """
    font로 그릴 수 없는 문자를 제거한 문자열

    제거로 생긴 연속 공백은 하나로 합치고 양끝 공백은 잘라낸다
    ("🔥 3연승" → "3연승"). 기본 비트맵 폰트면 그대로 반환한다.
    """
    if not isinstance(font, ImageFont.FreeTypeFont):
        return text
    kept = "".join(ch for ch in text if ch.isspace() or has_glyph(font, ch))
    if kept == text:
        return text
    return _MULTI_SPACE.sub(" ", kept).strip()
