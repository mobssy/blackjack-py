"""
카드 이미지 다운로드 스크립트
무료 카드 이미지를 다운로드하여 assets/cards에 저장
"""

import requests
from pathlib import Path

# 카드 이미지 URL (무료 오픈소스)
# https://github.com/hayeah/playing-cards-assets 사용
BASE_URL = "https://raw.githubusercontent.com/hayeah/playing-cards-assets/master/png"

SUITS = ["hearts", "diamonds", "clubs", "spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king", "ace"]


def download_card_images():
    """카드 이미지 다운로드"""
    assets_dir = Path(__file__).parent.parent / "assets" / "cards"
    assets_dir.mkdir(parents=True, exist_ok=True)

    print("🎴 카드 이미지 다운로드 시작...")

    # 각 카드 다운로드
    for suit in SUITS:
        for rank in RANKS:
            filename = f"{rank}_of_{suit}.png"
            url = f"{BASE_URL}/{filename}"
            filepath = assets_dir / filename

            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(response.content)

                print(f"✅ {filename}")
            except Exception as e:
                print(f"❌ {filename}: {e}")

    # 뒷면 이미지 다운로드
    back_url = f"{BASE_URL}/back.png"
    back_path = assets_dir / "back.png"

    try:
        response = requests.get(back_url, timeout=10)
        response.raise_for_status()

        with open(back_path, "wb") as f:
            f.write(response.content)

        print("✅ back.png")
    except Exception as e:
        print(f"❌ back.png: {e}")

    print("🎉 카드 이미지 다운로드 완료!")


if __name__ == "__main__":
    download_card_images()
