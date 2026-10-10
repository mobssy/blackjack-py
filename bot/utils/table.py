"""
JackPy - 멀티플레이 블랙잭 테이블
그룹 채팅에서 여러 플레이어가 하나의 딜러/슈를 공유하는 테이블 상태와 규칙.
텔레그램/DB 의존성 없음 — 잔액 차감과 정산은 핸들러 책임.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from bot.utils.blackjack_game import BlackjackGame
from bot.utils.deck import Deck, dealer_should_hit, is_blackjack, is_bust
from models.round import GameOutcome

MAX_SEATS = 7
TURN_TIMEOUT_SECONDS = 30
# 베팅(착석) 마감 — 사람들이 모일 시간을 주도록 분 단위로 둔다 (안내 문구도 분 단위)
BETTING_SECONDS = 3 * 60


class TablePhase(str, Enum):
    """테이블 진행 단계"""

    BETTING = "BETTING"  # 착석/베팅 접수
    PLAYING = "PLAYING"  # 딜 완료, 좌석 순서대로 플레이


class TableAction(str, Enum):
    """플레이어 차례에 가능한 액션"""

    HIT = "hit"
    STAND = "stand"
    DOUBLE = "double"
    SURRENDER = "surrender"
    SPLIT = "split"
    INSURANCE = "insurance"


class TableError(Exception):
    """테이블 규칙 위반 — 사용자에게 보여줄 i18n 키와 포맷 인자를 담는다"""

    def __init__(self, key: str, **kwargs: Any):
        super().__init__(key)
        self.key = key
        self.kwargs = kwargs


@dataclass
class Seat:
    """
    테이블 좌석

    game은 테이블의 덱/딜러 핸드를 공유하는 BlackjackGame으로,
    기존 1인 게임의 핸드/스플릿/더블/보험 로직을 그대로 재사용한다.
    """

    user_id: int
    name: str
    game: BlackjackGame
    done: bool = False
    surrendered: bool = False

    @property
    def base_bet(self) -> float:
        """착석 시 베팅액 (더블/스플릿 추가분 제외) — 다음 판 "같은 금액으로 계속"에 사용"""
        return self.game.initial_bet

    @property
    def is_live(self) -> bool:
        """딜러와 승부할 핸드가 남아 있는지 (서렌더/전 핸드 버스트 제외)"""
        return not self.surrendered and self.game.any_hand_alive()

    def results(self) -> List[Tuple[GameOutcome, float]]:
        """좌석의 핸드별 (outcome, payout) — 딜러 플레이 이후 호출"""
        if self.surrendered:
            return [self.game.surrender_result()]
        return self.game.get_results()

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "done": self.done,
            "surrendered": self.surrendered,
            "game": self.game.to_dict(include_shared=False),
        }


# 좌석별 핸드 결과: [(좌석, [(outcome, payout), ...]), ...]
SeatResults = List[Tuple[Seat, List[Tuple[GameOutcome, float]]]]


class BlackjackTable:
    """
    멀티플레이 블랙잭 테이블 (채팅방당 1개)

    흐름: BETTING(착석/베팅) → deal() → PLAYING(좌석 순서대로 턴)
    → 모든 좌석 완료 시 play_dealer() → 핸들러가 정산 후 테이블 제거.

    version은 상태가 바뀔 때마다 증가하며, 턴 타임아웃 타이머가
    자신이 예약된 이후 상태 변화가 있었는지 판단하는 데 쓰인다.
    """

    def __init__(
        self,
        chat_id: int,
        host_id: int,
        lang: str = "ko",
        deck: Optional[Deck] = None,
    ):
        self.chat_id = chat_id
        self.host_id = host_id
        self.lang = lang
        self.deck = deck if deck is not None else Deck(num_decks=6)
        # 좌석 게임들과 공유되는 리스트 — 재할당 금지, 제자리 변경만
        self.dealer_hand: List[str] = []
        self.seats: List[Seat] = []
        self.phase = TablePhase.BETTING
        self.turn_index = 0
        self.message_id: Optional[int] = None
        self.version = 0

    # ── 좌석 관리 (BETTING) ─────────────────────────────────────

    def seat_of(self, user_id: int) -> Optional[Seat]:
        """사용자의 좌석 (없으면 None)"""
        return next((seat for seat in self.seats if seat.user_id == user_id), None)

    @property
    def is_full(self) -> bool:
        return len(self.seats) >= MAX_SEATS

    def check_can_join(self, user_id: int) -> None:
        """
        착석 가능 여부 검증 (잔액 차감 전에 호출)

        Raises:
            TableError: 베팅 단계가 아니거나, 이미 착석했거나, 만석인 경우
        """
        if self.phase is not TablePhase.BETTING:
            raise TableError("table_not_betting")
        if self.seat_of(user_id) is not None:
            raise TableError("table_already_seated")
        if self.is_full:
            raise TableError("table_full", max=MAX_SEATS)

    def join(self, user_id: int, name: str, bet: float) -> Seat:
        """착석 및 베팅 (잔액은 호출 전에 차감되어 있어야 함)"""
        self.check_can_join(user_id)
        game = BlackjackGame(user_id, bet, deck=self.deck, dealer_hand=self.dealer_hand)
        seat = Seat(user_id=user_id, name=name, game=game)
        self.seats.append(seat)
        self.version += 1
        return seat

    def base_bets(self) -> Dict[int, float]:
        """좌석별 착석 베팅액 (user_id → 금액)"""
        return {seat.user_id: seat.base_bet for seat in self.seats}

    def leave(self, user_id: int) -> Seat:
        """
        베팅 단계에서 퇴장 (반환된 좌석의 베팅은 호출자가 환불)

        Raises:
            TableError: 진행 중이거나 착석하지 않은 경우
        """
        if self.phase is not TablePhase.BETTING:
            raise TableError("table_leave_playing")
        seat = self.seat_of(user_id)
        if seat is None:
            raise TableError("table_not_seated")
        self.seats.remove(seat)
        self.version += 1
        return seat

    # ── 딜 ─────────────────────────────────────────────────────

    def deal(self) -> None:
        """
        카지노 순서대로 좌석 → 딜러 순으로 2바퀴 딜, 첫 차례 결정

        내추럴 블랙잭 좌석은 플레이할 필요가 없으므로 바로 완료 처리한다.
        딜러 업카드가 10점 카드이고 블랙잭이면(피크) 플레이 없이 라운드가 끝난다.
        업카드가 A면 각자 인슈어런스를 결정하도록 플레이를 진행하고,
        정산에서 처음 건 베팅액만 잃는다 (BlackjackGame.get_results).
        """
        if self.phase is not TablePhase.BETTING:
            raise TableError("table_not_betting")
        if not self.seats:
            raise TableError("table_empty")

        for _ in range(2):
            for seat in self.seats:
                seat.game.hands[0].append(self.deck.draw())
            self.dealer_hand.append(self.deck.draw())

        for seat in self.seats:
            # 내추럴 블랙잭, 또는 딜러 피크로 블랙잭이 확인된 경우(업카드 10점 카드)
            if is_blackjack(seat.game.hands[0]) or seat.game.must_reveal_blackjack():
                seat.done = True

        self.phase = TablePhase.PLAYING
        self.turn_index = -1
        self._advance_turn()
        self.version += 1

    # ── 턴 진행 (PLAYING) ──────────────────────────────────────

    @property
    def current_seat(self) -> Optional[Seat]:
        """현재 차례인 좌석 (플레이 단계가 아니거나 모두 끝났으면 None)"""
        if self.phase is not TablePhase.PLAYING:
            return None
        if 0 <= self.turn_index < len(self.seats):
            return self.seats[self.turn_index]
        return None

    @property
    def dealer_has_blackjack(self) -> bool:
        """딜러 블랙잭 여부"""
        return is_blackjack(self.dealer_hand)

    @property
    def is_round_over(self) -> bool:
        """모든 좌석의 플레이가 끝났는지"""
        return self.phase is TablePhase.PLAYING and self.current_seat is None

    def require_turn(self, user_id: int) -> Seat:
        """
        user_id의 차례인지 확인

        Raises:
            TableError: 차례가 아닌 경우
        """
        seat = self.current_seat
        if seat is None or seat.user_id != user_id:
            raise TableError("table_not_your_turn")
        return seat

    def action_cost(self, user_id: int, action: TableAction) -> float:
        """
        액션 가능 여부 검증 및 추가 베팅 비용 반환 (잔액 차감 전에 호출)

        Raises:
            TableError: 차례가 아니거나 액션 조건 미달
        """
        game = self.require_turn(user_id).game
        if action is TableAction.DOUBLE:
            if not game.is_first_turn:
                raise TableError("double_only_first")
            return game.bet
        if action is TableAction.SURRENDER:
            if not game.is_first_turn:
                raise TableError("surrender_only_first")
            return 0.0
        if action is TableAction.SPLIT:
            if not game.can_split:
                raise TableError("split_not_allowed")
            return game.bet
        if action is TableAction.INSURANCE:
            if not game.can_insure:
                raise TableError("insurance_not_allowed")
            return game.insurance_cost
        return 0.0

    def apply(self, user_id: int, action: TableAction) -> Seat:
        """
        차례인 플레이어의 액션 실행 (추가 비용은 호출 전에 차감되어 있어야 함)

        Returns:
            Seat: 액션을 실행한 좌석
        """
        self.action_cost(user_id, action)
        seat = self.require_turn(user_id)
        handlers: Dict[TableAction, Callable[[Seat], None]] = {
            TableAction.HIT: self._hit,
            TableAction.STAND: self._next_hand_or_finish,
            TableAction.DOUBLE: self._double,
            TableAction.SURRENDER: self._surrender,
            TableAction.SPLIT: self._split,
            TableAction.INSURANCE: self._insure,
        }
        handlers[action](seat)
        self.version += 1
        return seat

    def timeout_stand(self) -> Optional[Seat]:
        """
        차례 시간 초과 — 현재 좌석의 남은 핸드를 모두 스탠드 처리

        Returns:
            Optional[Seat]: 자동 스탠드된 좌석 (차례인 좌석이 없으면 None)
        """
        seat = self.current_seat
        if seat is None:
            return None
        self._finish_seat(seat)
        self.version += 1
        return seat

    def _hit(self, seat: Seat) -> None:
        seat.game.player_hit()
        if is_bust(seat.game.player_hand):
            self._next_hand_or_finish(seat)

    def _double(self, seat: Seat) -> None:
        seat.game.player_double()
        self._finish_seat(seat)

    def _surrender(self, seat: Seat) -> None:
        seat.surrendered = True
        self._finish_seat(seat)

    def _split(self, seat: Seat) -> None:
        seat.game.split()
        # 에이스 스플릿: 각 핸드 카드 1장씩만 받고 자동 스탠드
        if seat.game.split_rank == "A":
            self._finish_seat(seat)

    def _insure(self, seat: Seat) -> None:
        seat.game.take_insurance()

    def _next_hand_or_finish(self, seat: Seat) -> None:
        """스플릿 핸드가 남았으면 다음 핸드로, 아니면 좌석 완료"""
        if not seat.game.advance_hand():
            self._finish_seat(seat)

    def _finish_seat(self, seat: Seat) -> None:
        seat.done = True
        self._advance_turn()

    def _advance_turn(self) -> None:
        """완료되지 않은 다음 좌석으로 차례 이동"""
        index = self.turn_index + 1
        while index < len(self.seats) and self.seats[index].done:
            index += 1
        self.turn_index = index

    # ── 딜러 및 결과 ───────────────────────────────────────────

    def play_dealer(self) -> None:
        """승부할 좌석이 남아 있으면 딜러 규칙(17 미만·소프트 17 히트)대로 플레이"""
        if not any(seat.is_live for seat in self.seats):
            return
        while dealer_should_hit(self.dealer_hand):
            self.dealer_hand.append(self.deck.draw())

    def results(self) -> SeatResults:
        """좌석별 핸드 결과 (play_dealer 이후 호출)"""
        return [(seat, seat.results()) for seat in self.seats]

    # ── 직렬화 ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "host_id": self.host_id,
            "lang": self.lang,
            "phase": self.phase.value,
            "turn_index": self.turn_index,
            "message_id": self.message_id,
            "dealer_hand": self.dealer_hand,
            "deck_cards": self.deck.cards,
            "seats": [seat.to_dict() for seat in self.seats],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BlackjackTable":
        """to_dict()로 저장된 상태에서 테이블 복원 (좌석은 덱/딜러 핸드를 다시 공유)"""
        table = cls(
            chat_id=int(data["chat_id"]),
            host_id=int(data["host_id"]),
            lang=data.get("lang", "ko"),
        )
        table.deck.cards = list(data["deck_cards"])
        table.dealer_hand.extend(data["dealer_hand"])
        table.phase = TablePhase(data["phase"])
        table.turn_index = int(data["turn_index"])
        table.message_id = data.get("message_id")
        table.seats = [_seat_from_dict(seat_data, table) for seat_data in data["seats"]]
        return table


def _seat_from_dict(data: dict, table: BlackjackTable) -> Seat:
    """저장된 좌석 복원 (게임은 테이블의 덱/딜러 핸드를 공유)"""
    game_data = dict(data["game"])
    # 처음 건 베팅액이 게임에 저장되기 전의 세션은 좌석의 base_bet으로 대체
    if "initial_bet" not in game_data and "base_bet" in data:
        game_data["initial_bet"] = data["base_bet"]
    return Seat(
        user_id=int(data["user_id"]),
        name=data["name"],
        game=BlackjackGame.from_dict(
            game_data, deck=table.deck, dealer_hand=table.dealer_hand
        ),
        done=bool(data["done"]),
        surrendered=bool(data["surrendered"]),
    )
