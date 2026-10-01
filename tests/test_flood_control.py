"""
Flood control 대응 테스트
- RetryAfterLimiter: 429 시 대기 후 재시도, 한도 초과 시 포기
- 테이블: 메시지 전송이 실패해도 타이머가 예약되어 라운드가 멈추지 않음
"""

import asyncio
from datetime import timedelta

import pytest
from telegram.error import BadRequest, RetryAfter

from bot.handlers import table as table_handlers
from bot.middleware.rate_limit import RetryAfterLimiter
from bot.utils.table import BlackjackTable


class _Sleeps:
    def __init__(self):
        self.calls = []

    async def __call__(self, seconds):
        self.calls.append(seconds)


def _flaky(failures, retry_after=3):
    """처음 failures번은 RetryAfter, 이후 성공하는 콜백"""
    state = {"calls": 0}

    async def callback(*args, **kwargs):
        state["calls"] += 1
        if state["calls"] <= failures:
            raise RetryAfter(retry_after)
        return {"ok": True, "args": args, "kwargs": kwargs}

    return callback, state


def _process(limiter, callback):
    return asyncio.run(
        limiter.process_request(
            callback=callback,
            args=("sendPhoto", {"chat_id": -1}),
            kwargs={"read_timeout": 5},
            endpoint="sendPhoto",
            data={"chat_id": -1},
            rate_limit_args=None,
        )
    )


class TestRetryAfterLimiter:
    def test_passes_through_without_waiting(self):
        sleeps = _Sleeps()
        callback, state = _flaky(0)
        result = _process(RetryAfterLimiter(sleep=sleeps), callback)
        assert result["args"] == ("sendPhoto", {"chat_id": -1})
        assert result["kwargs"] == {"read_timeout": 5}
        assert state["calls"] == 1
        assert sleeps.calls == []

    def test_waits_and_retries_after_flood(self):
        sleeps = _Sleeps()
        callback, state = _flaky(2, retry_after=4)
        result = _process(RetryAfterLimiter(max_retries=2, sleep=sleeps), callback)
        assert result["ok"] is True
        assert state["calls"] == 3
        assert sleeps.calls == [4.5, 4.5]

    def test_gives_up_after_max_retries(self):
        sleeps = _Sleeps()
        callback, state = _flaky(5)
        with pytest.raises(RetryAfter):
            _process(RetryAfterLimiter(max_retries=2, sleep=sleeps), callback)
        assert state["calls"] == 3

    def test_does_not_wait_too_long(self):
        sleeps = _Sleeps()
        callback, state = _flaky(1, retry_after=120)
        with pytest.raises(RetryAfter):
            _process(RetryAfterLimiter(max_wait_seconds=30, sleep=sleeps), callback)
        assert state["calls"] == 1
        assert sleeps.calls == []

    def test_accepts_timedelta_retry_after(self):
        sleeps = _Sleeps()
        callback, _ = _flaky(1, retry_after=timedelta(seconds=2))
        _process(RetryAfterLimiter(sleep=sleeps), callback)
        assert sleeps.calls == [2.5]

    def test_other_errors_are_not_retried(self):
        sleeps = _Sleeps()
        calls = []

        async def callback(*args, **kwargs):
            calls.append(1)
            raise BadRequest("Message is not modified")

        with pytest.raises(BadRequest):
            _process(RetryAfterLimiter(sleep=sleeps), callback)
        assert len(calls) == 1
        assert sleeps.calls == []


def _seated_table(seat_count=7):
    table = BlackjackTable(chat_id=-100, host_id=1)
    for i in range(seat_count):
        table.join(user_id=i + 1, name=f"P{i + 1}", bet=10.0)
    return table


@pytest.fixture
def armed(monkeypatch):
    """타이머 예약 호출 기록 (실제 asyncio 태스크는 만들지 않음)"""
    calls = []
    monkeypatch.setattr(
        table_handlers, "_arm_turn_timer", lambda bot, table: calls.append("turn")
    )
    monkeypatch.setattr(
        table_handlers,
        "_arm_betting_timer",
        lambda bot, table: calls.append("betting"),
    )
    return calls


async def _flooded(*args, **kwargs):
    raise RetryAfter(60)


class TestTableKeepsRunning:
    def test_turn_timer_armed_even_if_turn_message_fails(self, monkeypatch, armed):
        table = _seated_table()
        table.deck.cards = ["5C", "6D"] * 20  # 블랙잭 없이 진행 중인 라운드
        table.deal()
        monkeypatch.setattr(table_handlers, "_show_turn", _flooded)

        with pytest.raises(RetryAfter):
            asyncio.run(table_handlers._advance(None, table, new_message=True))
        assert armed == ["turn"]

    def test_betting_timer_armed_even_if_table_message_fails(self, monkeypatch, armed):
        monkeypatch.setattr(table_handlers, "_show_betting", _flooded)
        monkeypatch.setattr(table_handlers, "_persist_tables", lambda: None)
        monkeypatch.setattr(table_handlers, "table_sessions", {})

        with pytest.raises(RetryAfter):
            asyncio.run(table_handlers._open_or_resume(None, -100, 1, "ko"))
        assert armed == ["betting"]

    def test_stale_callback_answer_is_ignored(self):
        class _ExpiredQuery:
            async def answer(self):
                raise BadRequest("Query is too old and response timeout expired")

        asyncio.run(table_handlers._answer_quietly(_ExpiredQuery()))
