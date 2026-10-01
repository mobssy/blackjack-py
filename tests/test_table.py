"""
JackPy - 멀티플레이 테이블 테스트
BlackjackTable 규칙/턴 진행/직렬화, 테이블 영속화, 캡션 포맷 테스트
"""

import pytest

from bot.utils import session_store
from bot.utils.blackjack_game import BlackjackGame
from bot.utils.deck import Deck, calculate_hand_value
from bot.utils.table import (
    BETTING_SECONDS,
    MAX_SEATS,
    BlackjackTable,
    TableAction,
    TableError,
    TablePhase,
)
from bot.utils.table_view import betting_caption, result_text, turn_caption
from models.round import GameOutcome

# 덱이 소진되지 않도록 앞쪽(마지막에 뽑히는 쪽)에 채워 두는 카드
_FILLER = ["2C"] * 60


def _stack(deck: Deck, draw_order):
    """draw_order 순서대로 뽑히도록 덱 구성 (draw는 리스트 끝에서 pop)"""
    deck.cards = _FILLER + list(reversed(draw_order))


def _table_with(seat_count: int, draw_order, bet: float = 100.0) -> BlackjackTable:
    """
    seat_count명이 착석하고 draw_order로 딜된 테이블

    딜 순서: 좌석1..N → 딜러 → 좌석1..N → 딜러
    """
    table = BlackjackTable(chat_id=-100, host_id=1)
    for i in range(seat_count):
        table.join(user_id=i + 1, name=f"P{i + 1}", bet=bet)
    _stack(table.deck, draw_order)
    table.deal()
    return table


class TestSeating:
    """착석/퇴장 규칙"""

    def test_join_and_seat_of(self):
        table = BlackjackTable(chat_id=-100, host_id=1)
        seat = table.join(user_id=1, name="A", bet=50.0)
        assert table.seat_of(1) is seat
        assert seat.game.total_bet == 50.0
        assert table.seat_of(2) is None

    def test_join_twice_rejected(self):
        table = BlackjackTable(chat_id=-100, host_id=1)
        table.join(user_id=1, name="A", bet=50.0)
        with pytest.raises(TableError) as e:
            table.join(user_id=1, name="A", bet=50.0)
        assert e.value.key == "table_already_seated"

    def test_table_full(self):
        table = BlackjackTable(chat_id=-100, host_id=1)
        for uid in range(1, MAX_SEATS + 1):
            table.join(user_id=uid, name=str(uid), bet=10.0)
        with pytest.raises(TableError) as e:
            table.check_can_join(999)
        assert e.value.key == "table_full"
        assert e.value.kwargs == {"max": MAX_SEATS}

    def test_join_after_deal_rejected(self):
        table = _table_with(1, ["9S", "9D", "8S", "7D"])
        with pytest.raises(TableError) as e:
            table.check_can_join(99)
        assert e.value.key == "table_not_betting"

    def test_leave_during_betting(self):
        table = BlackjackTable(chat_id=-100, host_id=1)
        table.join(user_id=1, name="A", bet=50.0)
        seat = table.leave(1)
        assert seat.game.total_bet == 50.0
        assert table.seats == []

    def test_leave_during_play_rejected(self):
        table = _table_with(1, ["9S", "9D", "8S", "7D"])
        with pytest.raises(TableError) as e:
            table.leave(1)
        assert e.value.key == "table_leave_playing"

    def test_deal_empty_table_rejected(self):
        table = BlackjackTable(chat_id=-100, host_id=1)
        with pytest.raises(TableError) as e:
            table.deal()
        assert e.value.key == "table_empty"


class TestDeal:
    """딜 순서와 공유 상태"""

    def test_deal_order_and_shared_dealer(self):
        # P1, P2, 딜러, P1, P2, 딜러
        table = _table_with(2, ["9S", "5H", "KD", "8S", "6H", "7C"])
        p1, p2 = table.seats
        assert p1.game.hands[0] == ["9S", "8S"]
        assert p2.game.hands[0] == ["5H", "6H"]
        assert table.dealer_hand == ["KD", "7C"]
        # 좌석 게임들은 테이블의 딜러 핸드/덱을 공유
        assert p1.game.dealer_hand is table.dealer_hand
        assert p2.game.deck is table.deck
        assert table.phase is TablePhase.PLAYING
        assert table.current_seat is p1

    def test_natural_blackjack_skips_turn(self):
        # P1 블랙잭(A+K) → 바로 P2 차례
        table = _table_with(2, ["AS", "5H", "9D", "KS", "6H", "7C"])
        p1, p2 = table.seats
        assert p1.done is True
        assert table.current_seat is p2

    def test_all_naturals_round_over_immediately(self):
        table = _table_with(1, ["AS", "9D", "KS", "7C"])
        assert table.is_round_over


class TestTurns:
    """턴 진행과 액션"""

    def test_only_current_player_can_act(self):
        table = _table_with(2, ["9S", "5H", "KD", "8S", "6H", "7C"])
        with pytest.raises(TableError) as e:
            table.apply(2, TableAction.HIT)
        assert e.value.key == "table_not_your_turn"

    def test_stand_moves_to_next_seat(self):
        table = _table_with(2, ["9S", "5H", "KD", "8S", "6H", "7C"])
        p1, p2 = table.seats
        table.apply(1, TableAction.STAND)
        assert p1.done is True
        assert table.current_seat is p2

    def test_hit_bust_finishes_seat(self):
        # P1 16에서 K 히트 → 버스트
        table = _table_with(2, ["9S", "5H", "KD", "7S", "6H", "7C", "KH"])
        p1, p2 = table.seats
        table.apply(1, TableAction.HIT)
        assert calculate_hand_value(p1.game.hands[0]) > 21
        assert p1.done is True
        assert table.current_seat is p2

    def test_hit_without_bust_keeps_turn(self):
        table = _table_with(1, ["5S", "KD", "6S", "7C", "2H"])
        p1 = table.seats[0]
        table.apply(1, TableAction.HIT)
        assert p1.done is False
        assert table.current_seat is p1

    def test_double_costs_bet_and_finishes(self):
        table = _table_with(1, ["5S", "KD", "6S", "7C", "9H"], bet=100.0)
        p1 = table.seats[0]
        assert table.action_cost(1, TableAction.DOUBLE) == 100.0
        table.apply(1, TableAction.DOUBLE)
        assert p1.game.total_bet == 200.0
        assert len(p1.game.hands[0]) == 3
        assert table.is_round_over

    def test_double_after_hit_rejected(self):
        table = _table_with(1, ["5S", "KD", "6S", "7C", "2H"])
        table.apply(1, TableAction.HIT)
        with pytest.raises(TableError) as e:
            table.action_cost(1, TableAction.DOUBLE)
        assert e.value.key == "double_only_first"

    def test_surrender_result(self):
        table = _table_with(1, ["9S", "KD", "7S", "7C"], bet=100.0)
        table.apply(1, TableAction.SURRENDER)
        table.play_dealer()
        [(seat, results)] = table.results()
        assert seat.surrendered is True
        assert results == [(GameOutcome.SURRENDER, -50.0)]

    def test_split_keeps_turn_and_costs_bet(self):
        # 8 페어 스플릿 → 각 핸드 카드 1장씩 추가, 같은 좌석 계속
        table = _table_with(1, ["8S", "KD", "8H", "7C", "3D", "2C"], bet=100.0)
        p1 = table.seats[0]
        assert table.action_cost(1, TableAction.SPLIT) == 100.0
        table.apply(1, TableAction.SPLIT)
        assert p1.game.hand_count == 2
        assert p1.game.bets == [100.0, 100.0]
        assert table.current_seat is p1
        # 첫 핸드 스탠드 → 두 번째 핸드, 다시 스탠드 → 좌석 완료
        table.apply(1, TableAction.STAND)
        assert p1.game.hand_number == 2
        table.apply(1, TableAction.STAND)
        assert table.is_round_over

    def test_split_aces_finishes_seat(self):
        table = _table_with(1, ["AS", "KD", "AH", "7C", "3D", "2C"])
        table.apply(1, TableAction.SPLIT)
        assert table.seats[0].done is True
        assert table.is_round_over

    def test_split_not_pair_rejected(self):
        table = _table_with(1, ["8S", "KD", "9H", "7C"])
        with pytest.raises(TableError) as e:
            table.action_cost(1, TableAction.SPLIT)
        assert e.value.key == "split_not_allowed"

    def test_insurance_when_dealer_shows_ace(self):
        # 딜러 업카드(두 번째 카드) A
        table = _table_with(1, ["9S", "KD", "7S", "AC"], bet=100.0)
        assert table.action_cost(1, TableAction.INSURANCE) == 50.0
        table.apply(1, TableAction.INSURANCE)
        seat = table.seats[0]
        assert seat.game.insurance_bet == 50.0
        # 보험은 턴을 넘기지 않음, 재가입 불가
        assert table.current_seat is seat
        with pytest.raises(TableError):
            table.action_cost(1, TableAction.INSURANCE)

    def test_timeout_stand_finishes_all_hands(self):
        table = _table_with(2, ["8S", "5H", "KD", "8H", "6H", "7C", "3D", "2C"])
        p1, p2 = table.seats
        table.apply(1, TableAction.SPLIT)
        version = table.version
        seat = table.timeout_stand()
        assert seat is p1
        assert p1.done is True
        assert table.current_seat is p2
        assert table.version > version

    def test_version_increments_on_action(self):
        table = _table_with(1, ["5S", "KD", "6S", "7C", "2H"])
        version = table.version
        table.apply(1, TableAction.HIT)
        assert table.version == version + 1


class TestDealerAndResults:
    """딜러 플레이와 결과"""

    def test_dealer_skips_when_everyone_busts(self):
        table = _table_with(1, ["9S", "KD", "7S", "5C", "KH"])
        table.apply(1, TableAction.HIT)  # 26 버스트
        table.play_dealer()
        assert table.dealer_hand == ["KD", "5C"]
        [(_, results)] = table.results()
        assert results[0][0] == GameOutcome.BUST

    def test_dealer_draws_to_17(self):
        table = _table_with(1, ["KS", "5D", "9S", "6C", "3H", "9H"])
        table.apply(1, TableAction.STAND)
        table.play_dealer()
        assert calculate_hand_value(table.dealer_hand) >= 17

    def test_mixed_results(self):
        # P1 19, P2 15, 딜러 18 (드로우 없음)
        table = _table_with(2, ["KS", "9H", "KD", "9S", "6H", "8C"], bet=100.0)
        table.apply(1, TableAction.STAND)
        table.apply(2, TableAction.STAND)
        table.play_dealer()
        outcomes = {seat.name: results[0] for seat, results in table.results()}
        assert outcomes["P1"] == (GameOutcome.WIN, 100.0)
        assert outcomes["P2"] == (GameOutcome.LOSS, -100.0)

    def test_natural_blackjack_pays_3_to_2(self):
        table = _table_with(1, ["AS", "9D", "KS", "8C"], bet=100.0)
        table.play_dealer()
        [(_, results)] = table.results()
        assert results == [(GameOutcome.BLACKJACK, 150.0)]


class TestSerialization:
    """테이블 직렬화"""

    def test_roundtrip_mid_round_keeps_shared_state(self):
        table = _table_with(2, ["8S", "5H", "KD", "8H", "6H", "7C", "3D", "2C"])
        table.apply(1, TableAction.SPLIT)
        table.message_id = 42

        restored = BlackjackTable.from_dict(table.to_dict())
        assert restored.phase is TablePhase.PLAYING
        assert restored.turn_index == table.turn_index
        assert restored.message_id == 42
        assert restored.dealer_hand == table.dealer_hand
        assert restored.deck.cards == table.deck.cards
        assert [s.game.hands for s in restored.seats] == [
            s.game.hands for s in table.seats
        ]
        # 복원 후에도 좌석들이 같은 딜러 핸드/덱 객체를 공유해야 한다
        for seat in restored.seats:
            assert seat.game.dealer_hand is restored.dealer_hand
            assert seat.game.deck is restored.deck

    def test_restored_table_playable(self):
        table = _table_with(1, ["5S", "KD", "6S", "7C", "2H"])
        restored = BlackjackTable.from_dict(table.to_dict())
        restored.apply(1, TableAction.HIT)
        assert restored.seats[0].game.hands[0] == ["5S", "6S", "2H"]

    def test_betting_table_roundtrip(self):
        table = BlackjackTable(chat_id=-100, host_id=7, lang="en")
        table.join(user_id=7, name="Host", bet=30.0)
        restored = BlackjackTable.from_dict(table.to_dict())
        assert restored.phase is TablePhase.BETTING
        assert restored.host_id == 7
        assert restored.lang == "en"
        assert restored.seats[0].game.total_bet == 30.0


class TestSharedGameInjection:
    """BlackjackGame 공유 덱/딜러 핸드 주입"""

    def test_injected_objects_are_used(self):
        deck = Deck(num_decks=1)
        dealer_hand = []
        game = BlackjackGame(1, 10.0, deck=deck, dealer_hand=dealer_hand)
        assert game.deck is deck
        assert game.dealer_hand is dealer_hand

    def test_seat_dict_omits_shared_state(self):
        game = BlackjackGame(1, 10.0)
        game.deal_initial()
        data = game.to_dict(include_shared=False)
        assert "deck_cards" not in data
        assert "dealer_hand" not in data

    def test_deal_initial_keeps_dealer_reference(self):
        dealer_hand = []
        game = BlackjackGame(1, 10.0, dealer_hand=dealer_hand)
        game.deal_initial()
        assert game.dealer_hand is dealer_hand
        assert len(dealer_hand) == 2


class TestTableStore:
    """session_store 테이블 저장/복원"""

    def _use_tmp_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_store, "TABLE_FILE", tmp_path / "tables.json")

    def test_save_and_load(self, tmp_path, monkeypatch):
        self._use_tmp_file(tmp_path, monkeypatch)
        table = _table_with(2, ["9S", "5H", "KD", "8S", "6H", "7C"])
        session_store.save_tables({-100: table})

        loaded = session_store.load_tables()
        assert list(loaded.keys()) == [-100]
        assert [s.name for s in loaded[-100].seats] == ["P1", "P2"]

    def test_empty_removes_file(self, tmp_path, monkeypatch):
        self._use_tmp_file(tmp_path, monkeypatch)
        session_store.save_tables({-100: BlackjackTable(chat_id=-100, host_id=1)})
        assert session_store.TABLE_FILE.exists()
        session_store.save_tables({})
        assert not session_store.TABLE_FILE.exists()

    def test_load_corrupted_file(self, tmp_path, monkeypatch):
        self._use_tmp_file(tmp_path, monkeypatch)
        session_store.TABLE_FILE.write_text("{broken")
        assert session_store.load_tables() == {}
        assert not session_store.TABLE_FILE.exists()


class TestTableView:
    """캡션 포맷"""

    def test_betting_caption_escapes_names(self):
        table = BlackjackTable(chat_id=-100, host_id=1)
        table.join(user_id=1, name="<b>Evil</b>", bet=100.0)
        caption = betting_caption(table)
        assert "&lt;b&gt;Evil&lt;/b&gt;" in caption
        assert "<b>Evil" not in caption
        assert "$100.00" in caption
        assert "1/7" in caption

    def test_betting_caption_shows_deadline_in_minutes(self):
        assert BETTING_SECONDS == 180
        ko = betting_caption(BlackjackTable(chat_id=-100, host_id=1, lang="ko"))
        en = betting_caption(BlackjackTable(chat_id=-100, host_id=1, lang="en"))
        assert "3분 뒤 자동 딜" in ko
        assert "Auto-deal in 3 min" in en

    def test_turn_caption_is_notice_and_turn_only(self):
        table = _table_with(2, ["9S", "5H", "KD", "8S", "6H", "7C"])
        caption = turn_caption(table, notice="NOTICE")
        assert caption.startswith("NOTICE")
        assert 'href="tg://user?id=1"' in caption
        # 카드는 이미지에만 — 캡션에 카드/홀 카드 정보가 새지 않음
        assert "K♦️" not in caption
        assert "9♠️" not in caption
        assert caption.count("\n") == 2

    def test_result_text_lists_every_seat(self):
        table = _table_with(2, ["KS", "9H", "KD", "9S", "6H", "8C"])
        table.apply(1, TableAction.STAND)
        table.apply(2, TableAction.STAND)
        table.play_dealer()
        seat_results = table.results()
        settle_infos = {
            1: {"wallet": 1100.0, "streak": 1, "bonus": 0.0},
            2: {"wallet": 900.0, "streak": 0, "bonus": 0.0},
        }
        text = result_text(table, seat_results, settle_infos)
        assert "딜러 18" in text.splitlines()[0]
        assert len(text.splitlines()) == 4  # 제목, 빈 줄, 좌석당 한 줄
        assert "$1,100.00" in text
        assert "$900.00" in text
        assert "+$100.00" in text
        assert "-$100.00" in text
