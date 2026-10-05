"""
JackPy - 멀티 테이블 이미지 테스트
TableLayout 좌표 계산, TableImageRenderer 출력, seat_views 상태 변환 테스트
"""

import io

from PIL import Image

from bot.utils.table import BlackjackTable, TableAction
from bot.utils.table_renderer import (
    SeatView,
    TableLayout,
    get_table_renderer,
)
from bot.utils.table_view import (
    COLOR_BLACKJACK,
    COLOR_LOSS,
    COLOR_NEUTRAL,
    COLOR_TURN,
    COLOR_WIN,
    seat_views,
)

_FILLER = ["2C"] * 60


def _table_with(seat_count, draw_order, bet=100.0):
    """딜 순서: 좌석1..N → 딜러 → 좌석1..N → 딜러"""
    table = BlackjackTable(chat_id=-100, host_id=1)
    for i in range(seat_count):
        table.join(user_id=i + 1, name=f"P{i + 1}", bet=bet)
    table.deck.cards = _FILLER + list(reversed(draw_order))
    table.deal()
    return table


def _photo_size(photo: bytes):
    with Image.open(io.BytesIO(photo)) as image:
        return image.format, image.size


class TestTableLayout:
    """좌석 그리드 좌표"""

    def test_rows(self):
        layout = TableLayout()
        assert layout.rows(1) == 1
        assert layout.rows(4) == 1
        assert layout.rows(5) == 2
        assert layout.rows(7) == 2

    def test_height_grows_with_rows(self):
        layout = TableLayout()
        one_row = layout.height(4)
        two_rows = layout.height(5)
        assert two_rows - one_row == layout.seat_height + layout.gap

    def test_seat_origin_wraps_to_next_row(self):
        layout = TableLayout()
        x0, y0 = layout.seat_origin(0, 8)
        x1, y1 = layout.seat_origin(1, 8)
        x4, y4 = layout.seat_origin(4, 8)
        assert y1 == y0 and x1 == x0 + layout.seat_width + layout.gap
        assert x4 == x0 and y4 == y0 + layout.seat_height + layout.gap

    def test_grid_fits_inside_width(self):
        layout = TableLayout()
        seat_count = layout.columns
        x_last, _ = layout.seat_origin(layout.columns - 1, seat_count)
        x_first, _ = layout.seat_origin(0, seat_count)
        assert x_first >= 0
        assert x_last + layout.seat_width <= layout.width

    def test_partial_row_is_centered(self):
        layout = TableLayout()
        for seat_count in (1, 2, 3):
            x_first, _ = layout.seat_origin(0, seat_count)
            x_last, _ = layout.seat_origin(seat_count - 1, seat_count)
            right_gap = layout.width - (x_last + layout.seat_width)
            assert abs(x_first - right_gap) <= 1, seat_count

    def test_partial_second_row_is_centered_under_full_row(self):
        layout = TableLayout()
        # 7석: 첫 줄 4석은 그대로, 둘째 줄 3석은 가운데
        x0, _ = layout.seat_origin(0, 7)
        x4, y4 = layout.seat_origin(4, 7)
        x6, y6 = layout.seat_origin(6, 7)
        assert x4 == x0 + (layout.seat_width + layout.gap) // 2
        assert y6 == y4
        assert abs(x4 - (layout.width - (x6 + layout.seat_width))) <= 1


class TestTableImageRenderer:
    """이미지 출력"""

    def _render(self, seats, caption="", hide=True, felt_lines=()):
        return get_table_renderer().render(
            dealer_hand=["KD", "7C"],
            seats=seats,
            hide_dealer_first=hide,
            dealer_label="Dealer",
            caption=caption,
            felt_lines=felt_lines,
        )

    def test_renders_jpeg_with_layout_size(self):
        seats = [SeatView(name=f"P{i}", hands=[["9S", "8S"]], bet=10) for i in range(7)]
        photo = self._render(seats, caption="Round results", hide=False)
        layout = TableLayout()
        assert _photo_size(photo) == ("JPEG", (layout.width, layout.height(7)))

    def test_play_mode_with_felt_rule_lines(self):
        seats = [SeatView(name="P1", hands=[["9S", "8S"]], bet=10, active=True)]
        felt = ("BLACKJACK PAYS 6 TO 5", "DEALER MUST HIT SOFT 17")
        photo = self._render(seats, felt_lines=felt)
        assert _photo_size(photo) == ("JPEG", (1600, TableLayout().height(1)))

    def test_split_hands_and_long_name(self):
        seats = [
            SeatView(
                name="A" * 60,
                hands=[["8S", "3D", "4H", "2C"], ["8H", "2C"]],
                bet=200,
                active=True,
                status="▶ Turn",
            )
        ]
        photo = self._render(seats)
        assert _photo_size(photo)[0] == "JPEG"

    def test_revealed_dealer(self):
        seats = [SeatView(name="P1", hands=[["9S", "8S"]], bet=10)]
        assert _photo_size(self._render(seats, hide=False))[0] == "JPEG"

    def test_renderer_cached_per_theme(self):
        assert get_table_renderer() is get_table_renderer()


class TestSeatViews:
    """테이블 상태 → 이미지 좌석 정보"""

    def test_playing_statuses(self):
        # P1 블랙잭(완료), P2 차례, P3 대기
        table = _table_with(3, ["AS", "9H", "5D", "KD", "KS", "8H", "6D", "7C"])
        views = seat_views(table)
        assert [v.name for v in views] == ["P1", "P2", "P3"]
        assert views[0].status_color == COLOR_BLACKJACK and not views[0].active
        assert views[1].active and views[1].status_color == COLOR_TURN
        assert views[2].status_color == COLOR_NEUTRAL and not views[2].active

    def test_bust_status(self):
        table = _table_with(2, ["9S", "5H", "KD", "7S", "6H", "7C", "KH"])
        table.apply(1, TableAction.HIT)  # 26 버스트
        views = seat_views(table)
        assert views[0].status_color == COLOR_LOSS
        assert views[1].active

    def test_views_copy_hands(self):
        table = _table_with(1, ["9S", "KD", "7S", "7C"])
        views = seat_views(table)
        views[0].hands[0].append("XX")
        assert table.seats[0].game.hands[0] == ["9S", "7S"]

    def test_result_mode_colors_and_no_highlight(self):
        # P1 19 승, P2 15 패, P3 18 무 (딜러 18)
        table = _table_with(3, ["KS", "9H", "KC", "KD", "9S", "6H", "8C", "8H"])
        for uid in (1, 2, 3):
            table.apply(uid, TableAction.STAND)
        table.play_dealer()
        views = seat_views(table, table.results())
        assert [v.status_color for v in views] == [
            COLOR_WIN,
            COLOR_LOSS,
            COLOR_NEUTRAL,
        ]
        assert "+$100.00" in views[0].status
        assert "-$100.00" in views[1].status
        assert not any(v.active for v in views)
