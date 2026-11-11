# Retry and Backoff Pattern

A small, dependency-free helper for retrying explicitly selected transient failures.

## Usage

    from inventions.retry_backoff.retry import run_with_retry
    import urllib.error
    import urllib.request

    def fetch_status():
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3) as response:
            return response.status

    status = run_with_retry(
        fetch_status,
        attempts=4,
        initial_delay=0.2,
        max_delay=1.0,
        retry_on=(TimeoutError, urllib.error.URLError),
    )

## Behavior

- attempts is the total call count, including the initial call.
- The default retry policy catches only TimeoutError.
- Only exception classes explicitly listed in retry_on are retried.
- The final matching exception is re-raised unchanged when attempts are exhausted.
- Delays double after each failure and are capped at max_delay.
- No sleep occurs after the final attempt.
- sleep is injectable so tests can verify delays without waiting.
- Uses only the Python standard library.

## Safety and limitations

- Keep the retry exception list narrow. Do not retry validation, authentication,
  or other permanent failures.
- Retrying a write or other side effect is safe only when the operation is
  idempotent or uses a deduplication key. A timeout does not prove that a
  remote operation failed.
- Keep attempt counts and delays small. Retries consume time and can amplify
  load during an outage.
- This helper does not provide jitter, cancellation, an overall deadline,
  asynchronous support, or logging.

## Tests

From the repository root:

    python -m unittest discover -s inventions/retry-backoff -p 'test_*.py' -v
