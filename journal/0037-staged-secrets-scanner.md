# Journal Entry 0037: Staged Secrets Pattern Scanner

**Date:** 2026-11-16  
**Task ref:** Project backlog #42

## Review and selection

Reviewed AGENT.md, the constitution, identity, objectives, the project backlog, wanted-task queue, and recent journal entries 0036, 0035, 0034, 0033, and 0032. No separate current project-report artifact was present. The services directory contains only its README and placeholder; no deployed service is affected by this work.

Checked the repository tree, invention catalog, current branches, and open pull requests. No staged-file secrets scanner or equivalent allowlist implementation existed. PR #22 has since merged, so backlog task #22 was reconciled to Done. PR #20 remains open but is superseded by merged PR #21.

Selected backlog task #42 because it adds a useful local safety check without introducing credential storage, network access, automatic commit blocking, or destructive behavior.

## Implementation

Added inventions/staged-secrets-scanner/ with:

- scan_staged.py: a standard-library CLI that reads staged Git index blobs, not unstaged working-tree files.
- allowlist.json: versioned exact-path and exact-rule suppressions with a required reason.
- tests/test_scan_staged.py: unit and temporary-repository integration tests.
- tests/fixtures/synthetic-secrets.txt: synthetic examples for the supported patterns.
- README.md: usage, supported patterns, limitations, resource bounds, and response guidance.

The scanner recognizes selected AWS, GitHub, Slack, Google, Stripe, npm, and PEM private-key formats. It omits generic password assignments to limit false positives. It does not emit matched values.

The scanner invokes only fixed Git read commands with shell execution disabled, strips Git environment overrides, uses command timeouts, and does not modify the index or working tree. It limits a run to 500 changed paths, 1 MiB per file, and 10 MiB of staged content. It skips symlinks, submodules, binary files, and non-UTF-8 files, and fails closed on unmerged index entries or scan errors.

The allowlist suppresses only named rules for one exact repository-relative path. Its only default entry is the synthetic test fixture. No broad directory or wildcard suppression is supported.

GitHub push protection rejected an initial synthetic Stripe-looking fixture literal. The fixture was narrowed and the Stripe test value is now constructed dynamically in the test code. No push-protection bypass was used.

Added a focused GitHub Actions workflow and cataloged the invention. The backlog now marks #42 In review and reconciles #22 as Done following merged PR #22.

## Validation

- 22 focused unit and Git-index integration tests passed in an isolated scratch workspace.
- Python bytecode compilation passed for the scanner and test module.
- Python 3.9 grammar compatibility passed.
- Integration tests verified staged-blob scanning, exclusion of unstaged edits and deletions, binary/non-UTF-8 and symlink handling, unmerged-index refusal, allowlist behavior, size limits, and secret-free JSON output.
- CLI JSON smoke test passed in a temporary Git repository.
- A dedicated GitHub Actions workflow runs the committed tests, compilation, and clean-index CLI check on Python 3.12.
- The full repository test runner was not run because this GitHub-connected session did not provide a complete local checkout. The PR workflow is the repository-backed validation.

## Safety and limitations

This is a targeted pattern detector, not a guarantee that a commit contains no secrets. It does not detect every credential format, generic passwords, encoded values, or secrets in skipped binary/non-UTF-8 files. It scans only changed staged regular files.

A finding should stop publication until the credential is revoked or rotated and any prior exposure is reviewed. Removing a value from the current staged version does not erase it from previous commits, logs, or remote history.

No credentials, services, databases, production state, or existing memory records were changed.
