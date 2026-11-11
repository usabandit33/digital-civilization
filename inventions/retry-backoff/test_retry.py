import unittest

from retry import run_with_retry


class RetryTests(unittest.TestCase):
    def test_returns_first_success_without_sleep(self):
        sleeps = []
        self.assertEqual(run_with_retry(lambda: "ok", sleep=sleeps.append), "ok")
        self.assertEqual(sleeps, [])

    def test_retries_then_returns_success_with_capped_backoff(self):
        calls, sleeps = [], []

        def flaky():
            calls.append(True)
            if len(calls) < 4:
                raise TimeoutError("temporary")
            return "ready"

        result = run_with_retry(
            flaky, attempts=4, initial_delay=0.5, max_delay=0.75, sleep=sleeps.append
        )
        self.assertEqual(result, "ready")
        self.assertEqual(len(calls), 4)
        self.assertEqual(sleeps, [0.5, 0.75, 0.75])

    def test_exhaustion_reraises_last_exception_without_final_sleep(self):
        calls, sleeps = [], []

        def always_fails():
            calls.append(True)
            raise TimeoutError("still down")

        with self.assertRaisesRegex(TimeoutError, "still down"):
            run_with_retry(always_fails, attempts=3, initial_delay=0.1, sleep=sleeps.append)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [0.1, 0.2])

    def test_non_retryable_exception_is_not_retried(self):
        calls, sleeps = [], []

        def invalid():
            calls.append(True)
            raise ValueError("bad input")

        with self.assertRaisesRegex(ValueError, "bad input"):
            run_with_retry(invalid, retry_on=(TimeoutError,), sleep=sleeps.append)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sleeps, [])

    def test_default_policy_does_not_retry_value_error(self):
        calls = []

        def invalid():
            calls.append(True)
            raise ValueError("programming or input error")

        with self.assertRaises(ValueError):
            run_with_retry(invalid, sleep=lambda _: self.fail("should not sleep"))
        self.assertEqual(len(calls), 1)

    def test_zero_max_delay_disables_waiting(self):
        sleeps = []
        calls = []

        def flaky():
            calls.append(True)
            if len(calls) == 1:
                raise TimeoutError("temporary")
            return "ok"

        self.assertEqual(
            run_with_retry(flaky, attempts=2, initial_delay=1, max_delay=0, sleep=sleeps.append),
            "ok",
        )
        self.assertEqual(sleeps, [0])

    def test_invalid_attempt_counts_are_rejected(self):
        for value in (0, -1, True, 1.5, "3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_with_retry(lambda: None, attempts=value)

    def test_invalid_delays_are_rejected(self):
        for value in (-0.1, float("inf"), float("nan"), True, "0.2", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_with_retry(lambda: None, initial_delay=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_with_retry(lambda: None, max_delay=value)

    def test_invalid_retry_exception_configuration_is_rejected(self):
        for value in ((), (ValueError, KeyboardInterrupt), (42,), Exception):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_with_retry(lambda: None, retry_on=value)

    def test_non_callable_operation_and_sleep_are_rejected(self):
        with self.assertRaises(ValueError):
            run_with_retry(None)
        with self.assertRaises(ValueError):
            run_with_retry(lambda: None, sleep=None)


if __name__ == "__main__":
    unittest.main()
