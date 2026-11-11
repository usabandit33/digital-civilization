"""Bounded, dependency-free retry helper with exponential backoff."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def run_with_retry(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    initial_delay: float = 0.25,
    max_delay: float = 2.0,
    retry_on: tuple[type[Exception], ...] = (TimeoutError,),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run an operation until it succeeds or its bounded retry budget is spent.

    attempts is the total number of calls, including the first call.
    Only exceptions matching retry_on are retried. The final matching
    exception is re-raised unchanged. Delays double and are capped at max_delay.
    """
    if not callable(operation):
        raise ValueError("operation must be callable")
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise ValueError("attempts must be a positive integer")

    for name, value in (("initial_delay", initial_delay), ("max_delay", max_delay)):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"{name} must be a finite, non-negative number")

    if not isinstance(retry_on, tuple) or not retry_on or not all(
        isinstance(error_type, type) and issubclass(error_type, Exception)
        for error_type in retry_on
    ):
        raise ValueError("retry_on must be a non-empty tuple of Exception classes")
    if not callable(sleep):
        raise ValueError("sleep must be callable")

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
