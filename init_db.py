#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
"""
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 모델 import 및 초기화
from models import init_db

if __name__ == "__main__":
    print("🗄️  데이터베이스 초기화 중...")
    init_db()
    print("✅ 완료!")
