"""
게임 정산 테스트 (1인 게임/테이블 공용 apply_settlement, settle_game)
- 결과별 지갑 반영 (베팅은 정산 전에 이미 차감된 상태)
- 인슈어런스, 연승 보너스, 통계, 라운드 기록
- 딜러 블랙잭(피크) 시 처음 건 베팅만 잃는지
"""

from contextlib import contextmanager
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.handlers import settlement
from bot.handlers.settlement import apply_settlement, settle_game
from bot.utils.blackjack_game import BlackjackGame
from bot.utils.deck import Deck
from models.base import Base
from models.round import GameOutcome, Round
from models.user import User

CHAT_ID = -1001234567890
BET = 100.0


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _user(db, wallet: float = 1000.0, streak: int = 0) -> User:
    user = User.create_new(1, None, "P1")
    user.wallet = Decimal(str(wallet))
    user.stats_json = {**user.stats_json, "win_streak": streak}
    db.add(user)
    db.commit()
    return user


def _game(player_hand, dealer_hand, bet: float = BET) -> BlackjackGame:
    deck = Deck(num_decks=1)
    deck.cards = ["9C"] * 20  # 더블/스플릿용 카드
    game = BlackjackGame(user_id=1, bet=bet, deck=deck)
    game.hands[0] = list(player_hand)
    game.dealer_hand[:] = list(dealer_hand)
    return game


def _settle(db, user: User, game: BlackjackGame, results=None) -> dict:
    """베팅 차감(게임 진행 중 이미 일어난 일) 후 정산·커밋"""
    user.deduct_wallet(game.total_bet + (game.insurance_bet or 0))
    db.commit()
    info = apply_settlement(db, user, game, results or game.get_results(), CHAT_ID)
    db.commit()
    return info


def _wallet(user: User) -> float:
    return float(user.wallet)


class TestWalletByOutcome:
    def test_win_returns_bet_and_winnings(self, db):
        user = _user(db)
        _settle(db, user, _game(["KS", "9H"], ["KD", "8C"]))  # 19 vs 18
        assert _wallet(user) == 1100.0

    def test_loss_keeps_bet(self, db):
        user = _user(db)
        _settle(db, user, _game(["KS", "7H"], ["KD", "8C"]))  # 17 vs 18
        assert _wallet(user) == 900.0

    def test_push_returns_bet(self, db):
        user = _user(db)
        _settle(db, user, _game(["KS", "8H"], ["KD", "8C"]))
        assert _wallet(user) == 1000.0

    def test_bust_keeps_bet(self, db):
        user = _user(db)
        _settle(db, user, _game(["KS", "8H", "5C"], ["KD", "8C"]))
        assert _wallet(user) == 900.0

    def test_blackjack_pays_6_to_5(self, db):
        user = _user(db)
        _settle(db, user, _game(["AS", "KH"], ["KD", "8C"]))
        assert _wallet(user) == 1120.0

    def test_surrender_returns_half(self, db):
        user = _user(db)
        game = _game(["KS", "6H"], ["KD", "8C"])
        _settle(db, user, game, [game.surrender_result()])
        assert _wallet(user) == 950.0

    def test_double_win_pays_doubled_bet(self, db):
        user = _user(db)
        game = _game(["5S", "6H"], ["KD", "8C"])
        game.player_double()  # 9C → 20
        _settle(db, user, game)
        assert _wallet(user) == 1200.0

    def test_split_settles_each_hand(self, db):
        user = _user(db)
        game = _game(["8S", "8H"], ["KD", "8C"])
        game.split()  # 핸드1: 8+9=17 → 18에 패배
        game.hands[1] = ["8H", "KC"]  # 핸드2: 18 → 푸시
        _settle(db, user, game)
        assert _wallet(user) == 900.0  # 핸드1 -100, 핸드2 원금 반환


class TestDealerBlackjack:
    """딜러 블랙잭 — 피크 규칙과 같게 처음 건 베팅만 잃는다"""

    def test_original_bet_lost(self, db):
        user = _user(db)
        _settle(db, user, _game(["KS", "7H"], ["AS", "KH"]))
        assert _wallet(user) == 900.0

    def test_double_extra_refunded(self, db):
        user = _user(db)
        game = _game(["5S", "6H"], ["AS", "KH"])
        game.player_double()
        _settle(db, user, game)
        assert _wallet(user) == 900.0

    def test_split_extra_refunded(self, db):
        user = _user(db)
        game = _game(["8S", "8H"], ["AS", "KH"])
        game.split()
        _settle(db, user, game)
        assert _wallet(user) == 900.0

    def test_player_blackjack_pushes(self, db):
        user = _user(db)
        _settle(db, user, _game(["AD", "QH"], ["AS", "KH"]))
        assert _wallet(user) == 1000.0

    def test_insurance_pays_2_to_1(self, db):
        """업카드 A + 인슈어런스 — 보험 +100, 본 베팅 -100 → 본전"""
        user = _user(db)
        game = _game(["KS", "7H"], ["KD", "AH"])
        game.take_insurance()
        info = _settle(db, user, game)
        assert _wallet(user) == 1000.0
        assert info["insurance_net"] == 100.0
        assert user.stats_json["total_profit"] == 0.0


class TestInsuranceMiss:
    def test_insurance_lost_when_no_blackjack(self, db):
        user = _user(db)
        game = _game(["KS", "9H"], ["8D", "AH"])  # 19 vs 19 → 푸시
        game.take_insurance()
        info = _settle(db, user, game)
        assert _wallet(user) == 950.0
        assert info["insurance_net"] == -50.0


class TestStreakAndStats:
    def test_streak_bonus_on_third_win(self, db):
        user = _user(db, streak=2)
        info = _settle(db, user, _game(["KS", "9H"], ["KD", "8C"]))
        assert info["streak"] == 3
        assert info["bonus"] == 10.0  # 승리 정산액 100의 10%
        assert _wallet(user) == 1110.0

    def test_loss_resets_streak(self, db):
        user = _user(db, streak=4)
        info = _settle(db, user, _game(["KS", "7H"], ["KD", "8C"]))
        assert info["streak"] == 0
        assert user.stats_json["win_streak"] == 0

    def test_push_keeps_streak(self, db):
        user = _user(db, streak=4)
        info = _settle(db, user, _game(["KS", "8H"], ["KD", "8C"]))
        assert info["streak"] == 4

    def test_stats_accumulate(self, db):
        user = _user(db)
        _settle(db, user, _game(["KS", "9H"], ["KD", "8C"]))
        _settle(db, user, _game(["KS", "7H"], ["KD", "8C"]))
        stats = user.stats_json
        assert stats["total_games"] == 2
        assert stats["wins"] == 1
        assert stats["losses"] == 1
        assert stats["total_bet"] == 200.0
        assert stats["total_profit"] == 0.0

    def test_surrender_counts_as_loss(self, db):
        user = _user(db)
        game = _game(["KS", "6H"], ["KD", "8C"])
        _settle(db, user, game, [game.surrender_result()])
        assert user.stats_json["losses"] == 1
        assert user.stats_json["total_profit"] == -50.0


class TestRoundRecords:
    def test_one_round_per_hand(self, db):
        user = _user(db)
        game = _game(["8S", "8H"], ["KD", "8C"])
        game.split()
        _settle(db, user, game)
        rounds = db.query(Round).order_by(Round.id).all()
        assert len(rounds) == 2
        assert all(r.chat_id == CHAT_ID for r in rounds)
        assert rounds[0].player_hand == game.hands[0]
        assert rounds[0].dealer_hand == ["KD", "8C"]

    def test_round_stores_payout(self, db):
        user = _user(db)
        _settle(db, user, _game(["AS", "KH"], ["KD", "8C"]))
        round_ = db.query(Round).one()
        assert round_.outcome == GameOutcome.BLACKJACK
        assert float(round_.bet) == 100.0
        assert float(round_.payout) == 120.0


class TestSettleGame:
    def test_commits_with_own_session(self, db, monkeypatch):
        """settle_game은 사용자를 조회해 정산하고 커밋한다"""

        @contextmanager
        def fake_get_db():
            yield db

        monkeypatch.setattr(settlement, "get_db", fake_get_db)
        user = _user(db)
        user.deduct_wallet(BET)
        db.commit()
        game = _game(["KS", "9H"], ["KD", "8C"])

        info = settle_game(1, game, game.get_results(), CHAT_ID)

        db.rollback()  # 커밋되지 않았다면 여기서 사라진다
        assert _wallet(user) == 1100.0
        assert info["wallet"] == 1100.0
        assert db.query(Round).count() == 1
