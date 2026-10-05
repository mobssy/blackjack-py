"""
JackPy - 이미지 텍스트 폰트
게임/테이블 이미지의 글자는 저장소에 포함된 Pretendard(OFL)로 그린다
— 한글·영문이 한 폰트에 있어 서버(리눅스)와 맥에서 같은 결과가 나온다.
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

FONT_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts" / "Pretendard"


class Weight(Enum):
    """저장소에 포함된 Pretendard 굵기"""

    REGULAR = "Regular"
    MEDIUM = "Medium"
    SEMIBOLD = "SemiBold"
    BOLD = "Bold"


@lru_cache(maxsize=None)
def pretendard(size: int, weight: Weight = Weight.REGULAR) -> ImageFont.FreeTypeFont:
    """크기·굵기별 Pretendard (한 번 연 폰트는 재사용)"""
    return ImageFont.truetype(str(FONT_DIR / f"Pretendard-{weight.value}.otf"), size)


def text_width(font: ImageFont.FreeTypeFont, text: str) -> int:
    """text를 font로 그렸을 때의 가로 픽셀"""
    left, _, right, _ = font.getbbox(text)
    return right - left


def fitting_pretendard(
    text: str, weight: Weight, size: int, max_width: int, min_size: int = 14
) -> ImageFont.FreeTypeFont:
    """max_width 안에 들어가는 가장 큰 크기 (size부터 줄여 가며, min_size가 하한)"""
    while size > min_size and text_width(pretendard(size, weight), text) > max_width:
        size -= 2
    return pretendard(max(size, min_size), weight)
