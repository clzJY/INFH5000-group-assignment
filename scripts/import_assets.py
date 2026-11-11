#!/usr/bin/env python3
"""Offline extraction into a new profile; no automatic overwrites or downloads."""
import argparse
import getpass
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_artifacts import verify
from verify_artifacts import digest


def extract(archive, destination, password=None):
    destination.mkdir()
    try:
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                target = (destination / item.filename).resolve()
                if not target.is_relative_to(destination.resolve()):
                    raise ValueError("Unsafe archive member")
            z.extractall(destination, pwd=password)
    except Exception:
        # Preserve partially imported evidence; never reuse this profile blindly.
        (destination / "IMPORT_FAILED.txt").write_text("Partial extraction; choose a fresh --name after investigating.\n")
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument("artifact_root", type=Path)
    p.add_argument("--profile", choices=["tiny", "full"], required=True)
    p.add_argument("--name", help="Fresh local profile directory name")
    args = p.parse_args()
    root = args.artifact_root.resolve()
    verify(root)
    name = args.name or args.profile
    if Path(name).name != name or name in (".", ".."):
        p.error("--name must be one safe directory component")
    dest = ROOT / "assets" / name
    dest.parent.mkdir(exist_ok=True)
    dest.mkdir(exist_ok=False)
    if args.profile == "tiny":
        extract(root / "downloads/assets_tiny.zip", dest / "scene")
        candidates = {"assets": dest / "scene/assets"}
    else:
        password = getpass.getpass("Official registration password (not logged): ").encode()
        extract(root / "downloads/assets_full.zip", dest / "scene", password)
        extract(root / "downloads/assets_pedestrain.zip", dest / "people")
        candidates = {"assets": dest / "scene/assets", "assets_pedestrain": dest / "people/assets_pedestrain"}
    for key, target in candidates.items():
        if not target.is_dir():
            raise RuntimeError(f"Unexpected upstream archive layout: {target}")
        link = ROOT / "third_party/metaurban/metaurban" / key
        if link.exists() or link.is_symlink():
            raise FileExistsError(f"Existing asset link/directory preserved: {link}")
    for key, target in candidates.items():
        (ROOT / "third_party/metaurban/metaurban" / key).symlink_to(target, target_is_directory=True)
    names = ["assets_tiny.zip"] if args.profile == "tiny" else ["assets_full.zip", "assets_pedestrain.zip"]
    (dest / "import_receipt.json").write_text(json.dumps({"profile": args.profile,
        "archives": {name: digest(root / "downloads" / name) for name in names}}, indent=2) + "\n")
    print("ASSETS_IMPORTED_OFFLINE", args.profile)


if __name__ == "__main__":
    main()
