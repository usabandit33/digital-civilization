#!/usr/bin/env python3
"""Human CLI to list and approve pending contributions.

Usage:
  python -m core.approve list
  python -m core.approve approve <contribution_id> [--points 10]
"""

from __future__ import annotations

import argparse
import sys

from core.db import init_db, list_pending_contributions, approve_contribution


def cmd_list() -> None:
    rows = list_pending_contributions()
    if not rows:
        print("No pending contributions.")
        return
    for r in rows:
        print(
            f"#{r['id']}  agent={r['agent_id']}  kind={r['kind']}\n"
            f"  title: {r['title']}\n"
            f"  created: {r['created_at']}\n"
        )


def cmd_approve(contribution_id: int, points: int) -> None:
    ok = approve_contribution(contribution_id, points=points)
    if ok:
        print(f"Approved contribution #{contribution_id} (+{points} reputation, approved=1).")
    else:
        print(f"Contribution #{contribution_id} not found or not pending.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Approve external agent contributions")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List pending contributions")

    p_approve = sub.add_parser("approve", help="Approve a contribution and grant access")
    p_approve.add_argument("contribution_id", type=int)
    p_approve.add_argument("--points", type=int, default=10)

    args = parser.parse_args()
    init_db()

    if args.cmd == "list":
        cmd_list()
    elif args.cmd == "approve":
        cmd_approve(args.contribution_id, args.points)


if __name__ == "__main__":
    main()
