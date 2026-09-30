#!/usr/bin/env python3
"""
JackPy - 통계 재계산 스크립트
Round 테이블의 기록을 기반으로 User.stats_json의 게임 통계를 재계산합니다.

- 재계산 대상: total_games, wins, losses, total_bet, total_profit
- 보존: daily_streak, win_streak, last_rescue_at 등 Round로 복원할 수 없는 키
- total_profit은 Round의 핸드별 정산액 합계라서, 실시간 통계에 포함되는
  연승 보너스·인슈어런스 손익은 빠진다 (정산 로직과 차이가 생길 수 있음)

사용법: ./venv/bin/python scripts/rebuild_stats.py [--dry-run]
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

from models import get_db, User, Round, GameOutcome  # noqa: E402

# 정산(bot/handlers/settlement.py)과 같은 승패 분류
WIN_OUTCOMES = (GameOutcome.WIN, GameOutcome.BLACKJACK)
LOSS_OUTCOMES = (GameOutcome.LOSS, GameOutcome.BUST, GameOutcome.SURRENDER)


def rebuild_user_stats(dry_run: bool = False) -> None:
    """
    모든 사용자의 게임 통계를 재계산

    Args:
        dry_run: True면 결과만 출력하고 DB에 반영하지 않음
    """
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
            wins = sum(1 for r in rounds if r.outcome in WIN_OUTCOMES)
            losses = sum(1 for r in rounds if r.outcome in LOSS_OUTCOMES)
            total_bet = sum(float(r.bet) for r in rounds)
            total_profit = sum(float(r.payout) for r in rounds)

            # 게임 통계만 교체하고 나머지 키(스트릭, 구제 시각 등)는 보존
            new_stats = dict(user.stats_json or {})
            new_stats.update(
                {
                    "total_games": total_games,
                    "wins": wins,
                    "losses": losses,
                    "total_bet": total_bet,
                    "total_profit": total_profit,
                }
            )
            user.stats_json = new_stats

            win_rate = (wins / total_games * 100) if total_games > 0 else 0

            print(f"✅ {user.display_name}:")
            print(f"   총 게임: {total_games}회")
            print(f"   승/패: {wins}승 {losses}패 (승률: {win_rate:.1f}%)")
            print(f"   총 베팅: ${total_bet:,.2f}")
            print(f"   총 수익: ${total_profit:,.2f}\n")

        if dry_run:
            db.rollback()
            print("🔍 --dry-run: DB에 반영하지 않았습니다.")
            return

        # 모든 변경사항 커밋
        db.commit()
        print("✨ 통계 재계산 완료!")


if __name__ == "__main__":
    rebuild_user_stats(dry_run="--dry-run" in sys.argv)
