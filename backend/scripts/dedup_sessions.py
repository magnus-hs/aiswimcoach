#!/usr/bin/env python3
"""
De-duplicate swim sessions.

The bulk import + recovery process could create multiple DynamoDB rows for the
same physical swim — the same FIT file was uploaded more than once (different S3
UUIDs, identical content), so recovery treated each as distinct.

This script groups a user's sessions by (clean_date, distance, time, stroke) and,
for any group with more than one row, keeps a single representative and deletes
the rest.

Usage:
  python3 dedup_sessions.py --user-id <UUID> [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from boto3.dynamodb.conditions import Key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--table", default=os.environ.get("SESSIONS_TABLE", "ai-swim-coach-sessions"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(args.table)

    # Load all rows for the user
    rows = []
    qp = {"KeyConditionExpression": Key("user_id").eq(args.user_id),
          "ProjectionExpression": "session_date, total_distance_meters, total_time_seconds, stroke_type"}
    while True:
        resp = table.query(**qp)
        rows.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        qp["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    print(f"Total rows for user: {len(rows)}")

    # Group by dedup signature
    groups: dict[tuple, list] = defaultdict(list)
    for r in rows:
        sd = r.get("session_date", "")
        if sd.startswith("PLAN#") or sd.startswith("MPLAN#"):
            continue
        clean = sd.split("#")[0]
        sig = (
            clean,
            str(r.get("total_distance_meters", "")),
            str(r.get("total_time_seconds", "")),
            str(r.get("stroke_type", "")),
        )
        groups[sig].append(sd)  # store the full range-key value for deletion

    # Identify duplicates to delete (keep the first in each group)
    to_delete = []
    for sig, keys in groups.items():
        if len(keys) > 1:
            # Prefer to keep a legacy plain-date row (no "#") if present
            keys_sorted = sorted(keys, key=lambda k: (0 if "#" not in k else 1, k))
            keep = keys_sorted[0]
            to_delete.extend(keys_sorted[1:])

    print(f"Duplicate groups: {sum(1 for k in groups.values() if len(k) > 1)}")
    print(f"Rows to delete: {len(to_delete)}")

    if args.dry_run:
        print("(dry run — nothing deleted)")
        return

    deleted = 0
    with table.batch_writer() as batch:
        for range_key in to_delete:
            batch.delete_item(Key={"user_id": args.user_id, "session_date": range_key})
            deleted += 1
    print(f"Deleted {deleted} duplicate rows.")


if __name__ == "__main__":
    main()
