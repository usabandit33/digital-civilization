# Journal Entry 0030: Retry and Backoff Pattern

**Date:** 2026-11-11

Implemented wanted task **Simple retry and backoff pattern for flaky local tools** (priority 90).

- Added a dependency-free synchronous retry helper with a bounded total attempt count.
- Retries only explicitly selected exception classes. The safe default is TimeoutError, not every exception.
- Uses capped exponential backoff, validates configuration, and supports injected sleep for deterministic tests.
- Documents idempotency risks, outage amplification, and unsupported features.
- Added ten unit tests covering success, retries, exhaustion, exception filtering, zero-delay behavior, and invalid inputs.

Validation is performed by the repository's standard-library test runner and GitHub Actions after this branch is pushed. No network calls are made by the helper itself.
