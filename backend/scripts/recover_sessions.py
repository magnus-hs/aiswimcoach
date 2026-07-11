#!/usr/bin/env python3
"""
Recovery script for swim sessions lost to session_date key collisions.

Background:
  The Sessions table originally used (user_id, session_date) as its primary
  key. Swims sharing a session_date (e.g. from devices with unset clocks)
  overwrote each other on upload, so only one survived per duplicate date.
  The raw FIT files, however, were all stored in S3 under uploads/{uuid}.fit
  BEFORE the colliding DynamoDB write — so the data is recoverable.

  With the composite-key fix (session_date = "{date}#{session_id}"), every
  session is now unique. This script re-processes orphaned S3 files (those
  not represented in DynamoDB) and writes them as distinct sessions.

Usage:
  python3 recover_sessions.py --user-id <UUID> [--dry-run] [--limit N]

Environment:
  SESSIONS_TABLE, S3_BUCKET must be set (or pass --bucket / --table).
"""
from __future__ import annotations

import argparse
import os
import sys

# Make backend modules importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from fit_parser import parse_fit, extract_session_info, ParseError, MetricsMissingError
from session_history import save_session
from models import Metrics


def get_existing_s3_keys(table_name: str, user_id: str) -> set[str]:
    """Collect all s3_keys already represented in DynamoDB for this user."""
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    existing: set[str] = set()

    query_params = {"KeyConditionExpression": Key("user_id").eq(user_id),
                    "ProjectionExpression": "s3_key"}
    while True:
        resp = table.query(**query_params)
        for item in resp.get("Items", []):
            k = item.get("s3_key")
            if k:
                existing.add(k)
        if "LastEvaluatedKey" not in resp:
            break
        query_params["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    return existing


def list_all_s3_keys(bucket: str, prefix: str = "uploads/") -> list[str]:
    """List every FIT file key under the uploads/ prefix."""
    s3 = boto3.client("s3")
    keys: list[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.lower().endswith(".fit"):
                keys.append(key)
    return keys


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover orphaned swim sessions from S3.")
    parser.add_argument("--user-id", required=True, help="Target user_id to attribute recovered swims to")
    parser.add_argument("--bucket", default=os.environ.get("S3_BUCKET"), help="S3 bucket name")
    parser.add_argument("--table", default=os.environ.get("SESSIONS_TABLE", "ai-swim-coach-sessions"))
    parser.add_argument("--dry-run", action="store_true", help="Count recoverable swims without writing")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N orphan files")
    args = parser.parse_args()

    if not args.bucket:
        print("ERROR: --bucket or S3_BUCKET env var required")
        sys.exit(1)

    os.environ["SESSIONS_TABLE"] = args.table

    print(f"User: {args.user_id}")
    print(f"Bucket: {args.bucket}")
    print(f"Table: {args.table}")
    print(f"Dry run: {args.dry_run}")
    print("-" * 60)

    print("Loading existing s3_keys from DynamoDB...")
    existing = get_existing_s3_keys(args.table, args.user_id)
    print(f"  {len(existing)} sessions already in DynamoDB")

    print("Listing all S3 FIT files...")
    all_keys = list_all_s3_keys(args.bucket)
    print(f"  {len(all_keys)} FIT files in S3")

    orphans = [k for k in all_keys if k not in existing]
    print(f"  {len(orphans)} orphan files to examine")
    if args.limit:
        orphans = orphans[: args.limit]
        print(f"  limited to {len(orphans)}")
    print("-" * 60)

    s3 = boto3.client("s3")
    recovered = 0
    skipped_nonswim = 0
    errors = 0
    processed = 0

    from concurrent.futures import ThreadPoolExecutor
    import dataclasses

    def download_and_parse(key: str):
        """Download + parse a single file (runs in worker threads)."""
        try:
            obj = s3.get_object(Bucket=args.bucket, Key=key)
            fit_bytes = obj["Body"].read()
        except ClientError:
            return (key, "error", None)
        try:
            metrics = parse_fit(fit_bytes)
            session_info, splits = extract_session_info(fit_bytes)
            return (key, "swim", (metrics, session_info, splits))
        except (ParseError, MetricsMissingError):
            return (key, "nonswim", None)
        except Exception:
            return (key, "error", None)

    # Download + parse in parallel (I/O bound); save serially (safe).
    with ThreadPoolExecutor(max_workers=20) as pool:
        for key, kind, payload in pool.map(download_and_parse, orphans):
            processed += 1
            if processed % 500 == 0:
                print(f"[{processed}/{len(orphans)}] recovered={recovered} nonswim={skipped_nonswim} errors={errors}")

            if kind == "nonswim":
                skipped_nonswim += 1
                continue
            if kind == "error":
                errors += 1
                continue

            if args.dry_run:
                recovered += 1
                continue

            metrics, session_info, splits = payload
            try:
                save_session(
                    user_id=args.user_id,
                    session_info=session_info,
                    metrics=metrics,
                    s3_key=key,
                    splits=[dataclasses.asdict(s) for s in splits] if splits else None,
                )
                recovered += 1
            except Exception as exc:
                print(f"  save failed for {key}: {exc}")
                errors += 1

    print("-" * 60)
    print(f"DONE. recoverable/recovered={recovered}, non-swim skipped={skipped_nonswim}, errors={errors}")
    if args.dry_run:
        print("(dry run — nothing written)")


if __name__ == "__main__":
    main()
