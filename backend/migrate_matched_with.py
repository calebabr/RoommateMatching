#!/usr/bin/env python3
"""
Migration (P3D.1): normalize `users.matchedWith` to a canonical list-of-ints.

`matchedWith` has been stored in three shapes over the life of the app — `None`,
a bare `int`, and a `List[int]` — which forced three services to each carry a
private `_normalize_matched_with()` workaround. This migration rewrites every
user document to the canonical shape so those workarounds can be deleted.

Canonical rules (identical to the service-layer helpers being retired):
    None            -> []
    5               -> [5]
    [1, None, 2]    -> [1, 2]        (nulls dropped)
    ["3", 4.0]      -> [3, 4]        (coerced to int)
    anything else   -> []

Additionally reconciles the two fields that are always written alongside it and
can therefore drift out of sync:
    matchCount -> len(matchedWith)
    matched    -> matchCount > 0

Also DEDUPLICATES `matchedWith` (first occurrence wins): being matched with the
same user twice is not representable, and a duplicate would make the reconciled
`matchCount` wrong.

Safe to re-run — a second pass reports 0 documents to change. Read-only by
default; pass --apply to write.

Usage:
    cd backend
    python migrate_matched_with.py            # dry run, prints what would change
    python migrate_matched_with.py --apply    # perform the migration
"""
import os
import sys
from collections import Counter

from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient, UpdateOne

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME   = os.environ.get("MONGO_DB_NAME", "roommatch")


def _coerce_id(value):
    """Coerce a single matchedWith entry to an int, or return None to drop it."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            return None
    return None


def normalize_matched_with(raw):
    """Return the canonical list-of-ints for any historical `matchedWith` value."""
    if raw is None or isinstance(raw, bool):
        return []
    if isinstance(raw, int):
        return [raw]
    if isinstance(raw, list):
        out = []
        for entry in raw:
            coerced = _coerce_id(entry)
            if coerced is not None and coerced not in out:
                out.append(coerced)
        return out
    coerced = _coerce_id(raw)
    return [coerced] if coerced is not None else []


def _is_canonical(raw, desired):
    """True when `raw` is already stored in the exact canonical shape.

    Value equality is not enough: [1.0, 2.0] == [1, 2] in Python, but the stored
    floats still need rewriting. Element types are checked explicitly.
    """
    if not isinstance(raw, list):
        return False
    if len(raw) != len(desired):
        return False
    return all(type(a) is int and a == b for a, b in zip(raw, desired))


def _classify(raw):
    """Bucket the stored shape, for the dry-run breakdown."""
    if raw is None:
        return "None"
    if isinstance(raw, bool):
        return "bool (garbage)"
    if isinstance(raw, int):
        return "bare int"
    if isinstance(raw, list):
        if not raw:
            return "empty list"
        if all(type(x) is int for x in raw):
            return "list[int]"
        return "list (mixed/dirty)"
    return f"other ({type(raw).__name__})"


def analyze(users):
    """Read-only pass. Returns (plan, stats) without touching the database."""
    plan = []
    stats = {
        "total": 0,
        "shapes": Counter(),
        "matchedWith_rewrites": 0,
        "matchCount_fixes": 0,
        "matched_fixes": 0,
        "nulls_dropped": 0,
        "duplicates_dropped": 0,
        "self_references": [],
        "dangling_ids": [],
    }

    all_ids = {doc["id"] for doc in users.find({}, {"id": 1})}

    for doc in users.find({}, {"id": 1, "matchedWith": 1, "matchCount": 1, "matched": 1}):
        stats["total"] += 1
        user_id = doc.get("id")
        raw = doc.get("matchedWith")
        stats["shapes"][_classify(raw)] += 1

        desired = normalize_matched_with(raw)

        if isinstance(raw, list):
            stats["nulls_dropped"] += sum(1 for x in raw if x is None)
            coerced = [c for c in (_coerce_id(x) for x in raw) if c is not None]
            stats["duplicates_dropped"] += len(coerced) - len(set(coerced))

        if user_id in desired:
            stats["self_references"].append(user_id)
        for partner in desired:
            if partner not in all_ids:
                stats["dangling_ids"].append((user_id, partner))

        changes = {}
        if not _is_canonical(raw, desired):
            changes["matchedWith"] = desired
            stats["matchedWith_rewrites"] += 1

        desired_count = len(desired)
        if doc.get("matchCount") != desired_count:
            changes["matchCount"] = desired_count
            stats["matchCount_fixes"] += 1

        desired_matched = desired_count > 0
        if doc.get("matched") is not desired_matched:
            changes["matched"] = desired_matched
            stats["matched_fixes"] += 1

        if changes:
            plan.append(UpdateOne({"id": user_id}, {"$set": changes}))

    return plan, stats


def _report(stats, plan):
    print(f"\nScanned {stats['total']} user document(s).")

    print("\nStored `matchedWith` shapes:")
    for shape, count in sorted(stats["shapes"].items(), key=lambda kv: -kv[1]):
        print(f"  {shape:<22} {count}")

    print("\nDocuments needing each fix:")
    print(f"  matchedWith rewritten   {stats['matchedWith_rewrites']}")
    print(f"  matchCount reconciled   {stats['matchCount_fixes']}")
    print(f"  matched reconciled      {stats['matched_fixes']}")
    print(f"  -> total documents to update: {len(plan)}")

    if stats["nulls_dropped"] or stats["duplicates_dropped"]:
        print("\nEntries removed from arrays:")
        print(f"  null entries dropped    {stats['nulls_dropped']}")
        print(f"  duplicates dropped      {stats['duplicates_dropped']}")

    if stats["self_references"]:
        print(f"\n  [warn] {len(stats['self_references'])} user(s) list themselves in matchedWith: "
              f"{stats['self_references'][:10]}")
        print("         Not auto-removed - this is a service-layer bug, report it.")

    if stats["dangling_ids"]:
        print(f"\n  [warn] {len(stats['dangling_ids'])} matchedWith entrie(s) reference a user id "
              f"that no longer exists: {stats['dangling_ids'][:10]}")
        print("         Not auto-removed - deleting them would silently drop real matches.")
        print("         Investigate as a separate data-integrity task.")


def migrate(apply_changes=False, db_name=None):
    if apply_changes and "localhost" not in MONGO_URL and "127.0.0.1" not in MONGO_URL:
        print(f"[abort] --apply refused: MONGO_URL is not localhost ({MONGO_URL}).")
        print("        Run this against production only as part of the deploy checklist.")
        return 1

    client = MongoClient(MONGO_URL)
    db = client[db_name or DB_NAME]

    print(f"Database: {db.name} @ {MONGO_URL}")
    print("Mode: APPLY" if apply_changes else "Mode: DRY RUN (no writes - pass --apply to commit)")

    plan, stats = analyze(db.users)
    _report(stats, plan)

    if not plan:
        print("\n  [skip] Nothing to do - every document is already canonical.")
        client.close()
        return 0

    if not apply_changes:
        print("\n  [skip] Dry run - no changes written.")
        client.close()
        return 0

    result = db.users.bulk_write(plan, ordered=False)
    print(f"\n  [ok] Updated {result.modified_count} document(s).")

    _, after = analyze(db.users)
    remaining = after["matchedWith_rewrites"] + after["matchCount_fixes"] + after["matched_fixes"]
    if remaining == 0:
        print("  [ok] Verified - all documents are canonical, re-running is a no-op.")
    else:
        print(f"  [warn] {remaining} document(s) still non-canonical after migration.")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(migrate(apply_changes="--apply" in sys.argv))
