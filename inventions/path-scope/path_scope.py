#!/usr/bin/env python3
"""Resolve filesystem paths while keeping them inside an existing root."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Union

PathInput = Union[str, os.PathLike]


class PathScopeError(ValueError):
    """Raised when a path cannot be safely resolved inside its allowed root."""


def _coerce_path(value: PathInput, label: str) -> Path:
    try:
        raw = os.fspath(value)
    except TypeError:
        raise PathScopeError(f"{label} must be a string or path-like value") from None

    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise PathScopeError(f"{label} must be a non-empty text path")

    try:
        return Path(raw)
    except (TypeError, ValueError):
        raise PathScopeError(f"{label} is not a valid path") from None


def resolve_scoped_path(
    allowed_root: PathInput,
    candidate: PathInput,
    *,
    must_exist: bool = False,
) -> Path:
    """Return a canonical path only when it remains within ``allowed_root``.

    Relative candidates are interpreted beneath the root. Absolute candidates
    are accepted only if they resolve beneath it. Any explicit ``..`` path
    component is rejected, even if normalization would bring it back inside.
    Existing symlinks are resolved before the containment check, so a link
    that points outside the root is rejected.

    The root must already exist and be a directory. By default the final path
    may not exist yet, which is useful when validating a destination before a
    later write. Set ``must_exist=True`` when the target must already exist.

    This is a path-validation helper, not a race-free file-opening primitive.
    Another process could change a symlink after this function returns. Do not
    use check-then-open with attacker-writable directories; use descriptor-
    relative operations and platform-specific no-follow protections when that
    threat is in scope.
    """
    if not isinstance(must_exist, bool):
        raise PathScopeError("must_exist must be a boolean")

    root_path = _coerce_path(allowed_root, "allowed_root")
    candidate_path = _coerce_path(candidate, "candidate")

    if ".." in candidate_path.parts:
        raise PathScopeError("candidate contains a parent-directory traversal component")

    try:
        root = root_path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise PathScopeError("allowed_root must resolve to an existing directory") from None

    if not root.is_dir():
        raise PathScopeError("allowed_root must resolve to an existing directory")

    target = candidate_path if candidate_path.is_absolute() else root / candidate_path
    try:
        if must_exist:
            resolved = target.resolve(strict=True)
        else:
            # Resolve the nearest existing ancestor strictly, then append only
            # the missing suffix. lstat distinguishes a missing path from a
            # dangling symlink and exposes symlink loops in existing ancestors.
            probe = target
            missing_parts: list[str] = []
            while True:
                try:
                    probe.lstat()
                    break
                except FileNotFoundError:
                    parent = probe.parent
                    if parent == probe:
                        raise PathScopeError("candidate could not be resolved safely")
                    missing_parts.append(probe.name)
                    probe = parent
            resolved_base = probe.resolve(strict=True)
            resolved = resolved_base.joinpath(*reversed(missing_parts))
    except FileNotFoundError:
        raise PathScopeError("candidate does not exist") from None
    except PathScopeError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise PathScopeError("candidate could not be resolved safely") from None

    try:
        resolved.relative_to(root)
    except ValueError:
        raise PathScopeError("candidate resolves outside the allowed root") from None

    return resolved
