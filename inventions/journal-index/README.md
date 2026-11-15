# Journal Index Generator

A small, standard-library-only utility that creates a Markdown index of the repository journal, grouped chronologically and by topic.

## Usage

Run from the repository root:

```sh
python inventions/journal-index/journal_index.py
```

The generator writes Markdown to standard output and never writes to the filesystem. To save or refresh an index, redirect the output into the journal directory:

```sh
python inventions/journal-index/journal_index.py > journal/INDEX.md
```

The generated links are relative to the journal directory, so keep the output file there.

## Index rules

- Scans only direct child files named `NNNN-topic-slug.md`; it does not recurse.
- Ignores directories, symlinks, and unnumbered Markdown files such as `INDEX.md`.
- Uses the first level-one heading as the entry title, falling back to the filename slug.
- Reads an ISO `YYYY-MM-DD` date from a `Date` metadata line. Bold labels with the colon inside or outside the bold markup are accepted.
- Reads optional `Topic` or `Topics` metadata. Separate multiple topics with commas, semicolons, or vertical bars. If absent, the filename slug becomes the topic.
- Sorts dated entries newest first and places undated or invalid-date entries afterward.
- Escapes Markdown punctuation in titles and topic labels before rendering links and headings.

## Validation

Run the focused tests:

```sh
cd inventions/journal-index
python -m unittest discover -s tests -p 'test_*.py' -v
```

The implementation uses only the Python standard library. It does not access the network, execute journal content, recurse through the repository, or modify files. The output is deterministic for unchanged inputs.

## Limitations

This is a navigation aid, not a metadata migration. Entries without an ISO date are shown as undated, and topics are inferred from filenames unless explicit topic metadata is present. Review the generated Markdown before publishing it.
