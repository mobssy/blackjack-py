"""
JackPy - 게임 이미지 인코딩
텔레그램은 사진을 어차피 JPEG로 재압축하므로 PNG 대신 JPEG로 보낸다
(PNG 대비 용량 약 35~40%↓, 인코딩 시간 약 1/8).
"""

import io

from PIL import Image

JPEG_QUALITY = 88


def encode_photo(image: Image.Image) -> bytes:
    """렌더링된 이미지를 텔레그램 전송용 JPEG 바이트로 (알파 채널은 버림)"""
    buffer = io.BytesIO()
    image.convert("RGB").save(
        buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True
    )
    return buffer.getvalue()
