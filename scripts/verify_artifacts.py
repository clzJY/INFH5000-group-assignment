#!/usr/bin/env python3
"""Verify transferred Mac receipts; missing receipt coverage is a hard error."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for b in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def verify(root):
    rows = []
    for receipt in sorted(root.glob("receipt_*.json")):
        rows += json.loads(receipt.read_text())["entries"]
    expected = {}
    for row in rows:
        old = Path(row["path"])
        category = "wheelhouse" if old.suffix == ".whl" else "downloads"
        relative = Path(category) / old.name
        previous = expected.get(relative)
        if previous and previous != row["sha256"]:
            raise ValueError(f"Conflicting historical receipts: {relative}")
        expected[relative] = row["sha256"]
    count = 0
    for category in ("downloads", "wheelhouse"):
        for path in sorted((root / category).glob("*")):
            if not path.is_file() or path.name.endswith(".part"):
                continue
            relative = Path(category) / path.name
            if expected.get(relative) != digest(path):
                raise ValueError(f"Missing receipt or SHA256 mismatch: {relative}")
            count += 1
    if not count:
        raise ValueError("No verified artifacts found")
    return count


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    args = p.parse_args()
    print(f"ARTIFACTS_VERIFIED {verify(args.root.resolve())}")
