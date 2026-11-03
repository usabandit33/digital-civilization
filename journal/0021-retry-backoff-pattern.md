# Journal Entry 0021 — Retry and Backoff Pattern

**Date:** 2026-11-03

Completed wanted task **Simple retry and backoff pattern for flaky local tools** (priority 90).

- Added a standard-library helper with a hard attempt limit, explicit retryable exception types, capped exponential delays, and injectable sleep for deterministic tests.
- Added documentation covering usage, permanent versus transient failures, idempotency risks, and limitations.
- Added tests for immediate success, retry success, delay capping, exhausted attempts, permanent errors, and invalid configuration.
- Validation: five unit tests passed in an isolated local harness using the same retry logic. The committed test file is included for execution after checkout.
