"""
JackPy - 세션 영속화 테스트
BlackjackGame 직렬화 및 session_store 저장/복원 테스트
"""

from bot.utils.blackjack_game import BlackjackGame
from bot.utils import session_store
from bot.utils.deck import calculate_hand_value


def _make_game(bet: float = 100.0) -> BlackjackGame:
    game = BlackjackGame(user_id=1, bet=bet)
    game.deal_initial()
    return game


class TestGameSerialization:
    """BlackjackGame to_dict/from_dict 테스트"""

    def test_roundtrip_basic(self):
        """기본 게임 상태 왕복 직렬화"""
        game = _make_game(bet=250.0)
        restored = BlackjackGame.from_dict(game.to_dict())

        assert restored.user_id == game.user_id
        assert restored.hands == game.hands
        assert restored.bets == [250.0]
        assert restored.dealer_hand == game.dealer_hand
        assert restored.deck.cards == game.deck.cards
        assert restored.is_split is False

    def test_roundtrip_split_state(self):
        """스플릿 진행 상태 왕복 직렬화 (활성 핸드 유지)"""
        game = _make_game(bet=100.0)
        game.hands[0] = ["8S", "8H"]
        game.split()
        game.advance_hand()

        restored = BlackjackGame.from_dict(game.to_dict())
        assert restored.is_split is True
        assert restored.split_rank == "8"
        assert restored.hand_count == 2
        assert restored.active_index == 1
        assert restored.bets == [100.0, 100.0]

    def test_restored_game_playable(self):
        """복원된 게임에서 히트/딜러 플레이가 정상 동작"""
        game = _make_game()
        restored = BlackjackGame.from_dict(game.to_dict())
        before = len(restored.player_hand)
        restored.player_hit()
        assert len(restored.player_hand) == before + 1
        restored.dealer_play()
        assert calculate_hand_value(restored.dealer_hand) >= 17


class TestSessionStore:
    """session_store 저장/복원 테스트"""

    def _use_tmp_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_store, "SESSION_FILE", tmp_path / "sessions.json")

    def test_save_and_load(self, tmp_path, monkeypatch):
        """저장 후 복원하면 동일한 세션"""
        self._use_tmp_file(tmp_path, monkeypatch)
        game = _make_game(bet=50.0)
        session_store.save_sessions({12345: game})

        loaded = session_store.load_sessions()
        assert list(loaded.keys()) == [12345]
        assert loaded[12345].bets == [50.0]
        assert loaded[12345].hands == game.hands

    def test_empty_sessions_removes_file(self, tmp_path, monkeypatch):
        """세션이 비면 파일 삭제"""
        self._use_tmp_file(tmp_path, monkeypatch)
        session_store.save_sessions({12345: _make_game()})
        assert session_store.SESSION_FILE.exists()

        session_store.save_sessions({})
        assert not session_store.SESSION_FILE.exists()
        assert session_store.load_sessions() == {}

    def test_load_missing_file(self, tmp_path, monkeypatch):
        """파일이 없으면 빈 dict"""
        self._use_tmp_file(tmp_path, monkeypatch)
        assert session_store.load_sessions() == {}

    def test_load_corrupted_file(self, tmp_path, monkeypatch):
        """손상된 파일은 초기화하고 빈 dict 반환"""
        self._use_tmp_file(tmp_path, monkeypatch)
        session_store.SESSION_FILE.write_text("{corrupted json!!")

        assert session_store.load_sessions() == {}
        assert not session_store.SESSION_FILE.exists()
