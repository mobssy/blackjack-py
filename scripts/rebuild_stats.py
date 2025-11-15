#!/usr/bin/env python3
"""
JackPy - 통계 재계산 스크립트
Round 테이블의 기록을 기반으로 User.stats_json을 재계산합니다.
"""
import sys
import os
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .env 파일 로드
load_dotenv(os.path.join(project_root, ".env"))

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, project_root)

from models import get_db, User, Round, GameOutcome
from sqlalchemy import func


def rebuild_user_stats():
    """모든 사용자의 통계를 재계산"""
    with get_db() as db:
        # 모든 사용자 조회
        users = db.query(User).all()

        print(f"📊 총 {len(users)}명의 사용자 통계를 재계산합니다...\n")

        for user in users:
            # 해당 사용자의 모든 라운드 조회
            rounds = db.query(Round).filter(Round.user_id == user.id).all()

            if not rounds:
                print(f"⏭️  {user.display_name}: 게임 기록 없음")
                continue

            # 통계 계산
            total_games = len(rounds)
            wins = sum(
                1
                for r in rounds
                if r.outcome in (GameOutcome.WIN, GameOutcome.BLACKJACK)
            )
            losses = sum(
                1 for r in rounds if r.outcome in (GameOutcome.LOSS, GameOutcome.BUST)
            )
            total_bet = sum(float(r.bet) for r in rounds)
            total_profit = sum(float(r.payout) for r in rounds)

            # stats_json 업데이트
            user.stats_json = {
                "total_games": total_games,
                "wins": wins,
                "losses": losses,
                "total_bet": total_bet,
                "total_profit": total_profit,
            }

            win_rate = (wins / total_games * 100) if total_games > 0 else 0

            print(f"✅ {user.display_name}:")
            print(f"   총 게임: {total_games}회")
            print(f"   승/패: {wins}승 {losses}패 (승률: {win_rate:.1f}%)")
            print(f"   총 베팅: ${total_bet:,.2f}")
            print(f"   총 수익: ${total_profit:,.2f}\n")

        # 모든 변경사항 커밋
        db.commit()
        print("✨ 통계 재계산 완료!")


if __name__ == "__main__":
    rebuild_user_stats()
