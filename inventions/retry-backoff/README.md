# Retry and Backoff Pattern

A tiny, dependency-free helper for retrying explicitly selected transient failures.

## Usage

~~~python
from retry import run_with_retry
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
~~~

## Behavior

- Makes at most attempts calls, including the first call.
- Retries only exception types listed in retry_on.
- Re-raises the final matching exception unchanged when exhausted.
- Doubles deterministic delays and caps them at max_delay.
- Does not sleep after the final attempt.
- Uses only the Python standard library. Inject a custom sleep callable in tests.

## Safety and limitations

- Choose transient exceptions narrowly. Do not retry validation, authentication, or other permanent failures.
- Retrying a write or side effect is safe only when the operation is idempotent or has a deduplication key. A timeout does not prove the remote operation failed.
- Keep attempts and delays small. Retries consume time and can amplify load during an outage.
- No jitter, cancellation, deadlines, or logging are included.

## Tests

From the repository root:

~~~bash
python -m unittest discover -s inventions/retry-backoff -p 'test_*.py' -v
~~~
