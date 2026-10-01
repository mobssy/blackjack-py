"""
JackPy - 텔레그램 Flood control 대응
RetryAfter(429)를 받으면 지시된 시간만큼 기다렸다가 같은 요청을 다시 보낸다.
평소에는 요청을 지연시키지 않는 반응형 리미터 (소규모 봇이라 사전 스로틀링 불필요)
"""

import asyncio
import logging
from datetime import timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from telegram.error import RetryAfter
from telegram.ext import BaseRateLimiter

logger = logging.getLogger(__name__)

# 7명 테이블은 한 판에 메시지 전송/수정이 수십 번이라 그룹 한도에 걸릴 수 있다
DEFAULT_MAX_RETRIES = 2
# 이보다 오래 기다리라고 하면 포기 (업데이트 처리가 순차라 봇 전체가 멈추지 않도록)
DEFAULT_MAX_WAIT_SECONDS = 30.0

_Result = Union[bool, Dict[str, Any], List[Dict[str, Any]]]


def _seconds(retry_after: Union[int, float, timedelta]) -> float:
    """RetryAfter.retry_after (PTB 버전에 따라 int 또는 timedelta)를 초로 변환"""
    if isinstance(retry_after, timedelta):
        return retry_after.total_seconds()
    return float(retry_after)


class RetryAfterLimiter(BaseRateLimiter[None]):
    """RetryAfter 발생 시에만 대기 후 재시도하는 레이트 리미터"""

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_wait_seconds: float = DEFAULT_MAX_WAIT_SECONDS,
        sleep: Callable[[float], Coroutine[Any, Any, None]] = asyncio.sleep,
    ):
        self.max_retries = max_retries
        self.max_wait_seconds = max_wait_seconds
        self._sleep = sleep

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def process_request(
        self,
        callback: Callable[..., Coroutine[Any, Any, _Result]],
        args: Any,
        kwargs: Dict[str, Any],
        endpoint: str,
        data: Dict[str, Any],
        rate_limit_args: Optional[None],
    ) -> _Result:
        attempt = 0
        while True:
            try:
                return await callback(*args, **kwargs)
            except RetryAfter as e:
                wait = _seconds(e.retry_after)
                if attempt >= self.max_retries or wait > self.max_wait_seconds:
                    raise
                attempt += 1
                logger.warning(
                    f"Flood control: {endpoint} {wait:.0f}초 후 재시도 "
                    f"({attempt}/{self.max_retries})"
                )
                # 텔레그램 권고보다 살짝 늦게 보내 연속 429를 피한다
                await self._sleep(wait + 0.5)
