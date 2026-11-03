"""Bounded, dependency-free retry helper with exponential backoff."""
from __future__ import annotations
import math
import time
from collections.abc import Callable
from typing import TypeVar
T = TypeVar("T")
def run_with_retry(operation: Callable[[], T], *, attempts: int = 3, initial_delay: float = 0.25, max_delay: float = 2.0, retry_on: tuple[type[Exception], ...] = (Exception,), sleep: Callable[[float], None] = time.sleep) -> T:
    """Run operation until success or the bounded retry budget is exhausted."""
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise ValueError("attempts must be a positive integer")
    if not math.isfinite(initial_delay) or initial_delay < 0:
        raise ValueError("initial_delay must be finite and non-negative")
    if not math.isfinite(max_delay) or max_delay < 0:
        raise ValueError("max_delay must be finite and non-negative")
    if not isinstance(retry_on, tuple) or not retry_on or not all(isinstance(e, type) and issubclass(e, Exception) for e in retry_on):
        raise ValueError("retry_on must be a non-empty tuple of Exception classes")
    delay = initial_delay
    for attempt in range(attempts):
        try:
            return operation()
        except retry_on:
            if attempt == attempts - 1:
                raise
            sleep(min(delay, max_delay))
            delay = min(delay * 2, max_delay)
    raise RuntimeError("unreachable retry state")
