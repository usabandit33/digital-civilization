# Staged Secrets Pattern Scanner

A read-only, standard-library scanner for common credential patterns in staged Git text files. It inspects Git index blobs, not the working tree, so it checks the exact content that would enter the next commit.

## Quick start

From the repository root, stage the files you intend to commit, then run:

~~~bash
python inventions/staged-secrets-scanner/scan_staged.py
python inventions/staged-secrets-scanner/scan_staged.py --json
~~~

The scanner does not install a Git hook, block commits automatically, change the index, edit files, or contact a network service. Run it as a manual pre-commit check.

To scan another checkout or use a reviewed custom allowlist:

~~~bash
python inventions/staged-secrets-scanner/scan_staged.py --repo /path/to/repository
python inventions/staged-secrets-scanner/scan_staged.py --allowlist /path/to/allowlist.json --json
~~~

## Detected patterns

The initial rule set covers common high-confidence formats:

- AWS access key IDs
- GitHub classic and fine-grained personal access tokens
- Slack tokens
- Google API keys
- Stripe live secret and restricted keys
- npm access tokens
- PEM private-key headers

Generic assignments such as PASSWORD=value are intentionally not flagged because they produce many false positives. This is a pattern detector, not an exhaustive secret scanner.

## Staged-file and resource boundaries

- Scans staged added, modified, and renamed regular files reported by Git.
- Reads blob content from the index with fixed Git subcommands, no shell, and a 10-second timeout per command.
- Ignores deleted paths, symlinks, submodules, binary files, and non-UTF-8 files.
- Fails closed for unmerged index entries, unavailable Git data, invalid allowlists, and size-limit violations.
- Limits a run to 500 changed paths, 1 MiB per file, and 10 MiB of staged blob content.
- Does not recurse through the filesystem or read unstaged working-tree changes.
- Does not print matched credential values. Findings contain only repository-relative path, line, column, and rule name.

A clean result means no configured pattern was found in the scanned UTF-8 staged files. Skipped binary or non-UTF-8 files are counted in the report and are not inspected.

## Allowlisted test fixtures

The allowlist is versioned JSON. Each entry must contain:

- An exact repository-relative path. Wildcards, absolute paths, and parent traversal are rejected.
- One or more known rule identifiers to suppress for that path only.
- A non-empty reason explaining why the fixture is safe.

The default allowlist contains one exact test-fixture path with synthetic examples. It does not allowlist a directory, file extension, or general pattern. Keep additions narrow and review them like code.

## Output and exit codes

The JSON report uses schema version 1.0 and includes file counts, findings, allowlisted matches, and scan errors. It never includes the matched text.

| Exit code | Meaning |
|---|---|
| 0 | No configured patterns found in scanned text files |
| 1 | One or more possible credential patterns found |
| 2 | Scan could not complete safely |

If a real credential is found, do not merely delete the line and assume the credential is safe. Stop publication, revoke or rotate the credential, and review whether it entered earlier commits or logs.

## Tests

Requires Python 3.9+ and Git for the staged-index integration tests.

~~~bash
cd inventions/staged-secrets-scanner
python -m unittest discover -s tests -p 'test_*.py' -v
python -m py_compile scan_staged.py tests/test_scan_staged.py
~~~

Task reference: project backlog #42.
