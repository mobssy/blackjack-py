"""
JackPy - 게임 정산
1인 게임과 멀티 테이블이 공유하는 DB 정산 로직 (지갑 반영, 통계, 라운드 기록)
"""

from typing import Dict, List, Tuple

from models import get_db, User, Round, GameOutcome
from bot.utils.blackjack_game import BlackjackGame
from bot.utils.payouts import streak_bonus, update_streak


def apply_settlement(
    db,
    user: User,
    game: BlackjackGame,
    results: List[Tuple[GameOutcome, float]],
    chat_id: int,
) -> Dict:
    """
    한 플레이어의 게임 결과를 DB 세션에 반영 (커밋은 호출자 책임)

    여러 좌석을 한 트랜잭션으로 정산할 수 있도록 커밋하지 않는다.

    Args:
        db: DB 세션
        user: 정산 대상 사용자
        game: 게임 객체
        results: 핸드별 (outcome, payout) 리스트
        chat_id: 채팅 ID

    Returns:
        Dict: 렌더링에 필요한 정산 결과 정보
    """
    wins = losses = 0
    for (outcome, payout), hand, bet in zip(results, game.hands, game.bets):
        if outcome == GameOutcome.PUSH:
            user.add_wallet(bet)
        elif outcome == GameOutcome.SURRENDER:
            # 베팅액 절반 회수 (payout = -bet/2)
            user.add_wallet(bet + payout)
        elif payout > 0:
            user.add_wallet(bet + payout)

        if outcome in (GameOutcome.WIN, GameOutcome.BLACKJACK):
            wins += 1
        elif outcome in (GameOutcome.LOSS, GameOutcome.BUST, GameOutcome.SURRENDER):
            losses += 1

        db.add(
            Round(
                user_id=user.id,
                chat_id=chat_id,
                bet=bet,
                player_hand=hand,
                dealer_hand=list(game.dealer_hand),
                outcome=outcome,
                payout=payout,
            )
        )

    # 인슈어런스 정산 (가입 시 이미 차감됨 — 적중 시 원금 + 2:1 지급)
    insurance_net = game.insurance_net
    if game.insurance_bet and insurance_net > 0:
        user.add_wallet(game.insurance_bet + insurance_net)

    # 연승 스트릭 갱신 및 보너스 지급 (게임 전체 정산액 기준)
    total_payout = float(sum(payout for _, payout in results))
    prev_streak = (user.stats_json or {}).get("win_streak", 0)
    streak = update_streak(prev_streak, total_payout)
    bonus = streak_bonus(streak, total_payout)
    if bonus > 0:
        user.add_wallet(bonus)

    user.update_stats(
        total_games=len(results),
        wins=wins,
        losses=losses,
        total_bet=float(game.total_bet),
        total_profit=total_payout + bonus + insurance_net,
    )

    # win_streak은 누적이 아닌 절대값으로 저장
    stats = dict(user.stats_json or {})
    stats["win_streak"] = streak
    user.stats_json = stats

    return {
        "wallet": float(user.wallet),
        "streak": streak,
        "bonus": bonus,
        "insurance_bet": game.insurance_bet,
        "insurance_net": insurance_net,
    }


def settle_game(
    user_tg_id: int,
    game: BlackjackGame,
    results: List[Tuple[GameOutcome, float]],
    chat_id: int,
) -> Dict:
    """
    1인 게임 결과 DB 정산 및 커밋

    Args:
        user_tg_id: 사용자 텔레그램 ID
        game: 게임 객체
        results: 핸드별 (outcome, payout) 리스트
        chat_id: 채팅 ID

    Returns:
        Dict: 렌더링에 필요한 정산 결과 정보
    """
    with get_db() as db:
        user = User.find_by_tg_id(db, user_tg_id)
        settle_info = apply_settlement(db, user, game, results, chat_id)
        db.commit()
        return settle_info
