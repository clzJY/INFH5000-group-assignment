#!/usr/bin/env python3
"""Public acquisition on macOS; Linux CPython/wheels, never macOS packages."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

COMMIT = "6b8ff9aa48dd27d5c57fa1c712db520732f11fa9"
ARTIFACTS = {
    "source": {
        "filename": "metaurban-6b8ff9aa.tar.gz", "bytes": 201209533,
        "url": f"https://codeload.github.com/metadriverse/metaurban/tar.gz/{COMMIT}",
        "sha256": "4933b8ba8614c3a701db1b4ce0ede87dd5cae407fd2ff24842814879e31aaa5a"},
    "python": {
        "filename": "cpython-3.11.14-linux-x86_64.tar.gz", "bytes": 47042299,
        "url": "https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-3.11.14%2B20251014-x86_64-unknown-linux-gnu-install_only.tar.gz",
        "sha256": "d0623c777fb89b904b56cd5aba51af29cbb34b1f9d45f0672f90f6dce30fa93e"},
    "tiny": {"filename": "assets_tiny.zip", "bytes": 479067250, "sha256": None,
        "url": "https://drive.usercontent.google.com/download?id=10bAr4-WnMHCSNCuz7qG41MDt_GStxkI9&export=download&confirm=t"},
    "full-static": {"filename": "assets_full.zip", "bytes": 2437771429, "sha256": None,
        "url": "https://drive.usercontent.google.com/download?id=17pUIjPZrtac60YVHUL3YHMSaQ6J_Pmgc&export=download&confirm=t"},
    "pedestrians": {"filename": "assets_pedestrain.zip", "bytes": 1588857017, "sha256": None,
        "url": "https://drive.usercontent.google.com/download?id=1XUGfG57Cof43dX2pkMYBhsFVirJ4DQ1o&export=download&confirm=t"},
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch(name, folder):
    item = ARTIFACTS[name]
    dest = folder / item["filename"]
    if dest.exists():
        digest = sha256(dest)
        if item["sha256"] and digest != item["sha256"]:
            raise RuntimeError(f"Existing file checksum mismatch: {dest}")
        if item["bytes"] and dest.stat().st_size != item["bytes"]:
            raise RuntimeError(f"Existing file size mismatch: {dest}")
        print(f"EXISTS {name}: {dest}", flush=True)
    else:
        part = dest.with_suffix(dest.suffix + ".part")
        subprocess.run(["curl", "--fail", "--location", "--retry", "2", "--connect-timeout", "15",
                        "--continue-at", "-", "--output", str(part), item["url"]], check=True)
        with part.open("rb") as stream:
            head = stream.read(256).lstrip().lower()
        if head.startswith((b"<!doctype html", b"<html")):
            raise RuntimeError(f"HTML instead of {name}; use the official browser download, retain .part for inspection")
        digest = sha256(part)
        if item["sha256"] and digest != item["sha256"]:
            raise RuntimeError(f"Downloaded checksum mismatch: {part}")
        if item["bytes"] and part.stat().st_size != item["bytes"]:
            raise RuntimeError(f"Downloaded size mismatch: {part}; recheck official asset version")
        part.rename(dest)
    return dict(name=name, path=str(dest), url=item["url"], bytes=dest.stat().st_size,
                sha256=sha256(dest), upstream_sha256=item["sha256"])


def wheels(root, project):
    # This venv runs on the Mac solely as a cross-platform acquisition tool.
    tool = root / "tools/download-venv"
    if not (tool / "bin/python").is_file():
        subprocess.run([sys.executable, "-m", "venv", str(tool)], check=True)
    python = str(tool / "bin/python")
    subprocess.run([python, "-m", "pip", "install", "pip==24.3.1", "setuptools==75.6.0", "wheel==0.45.1"], check=True)
    wheelhouse = root / "wheelhouse"
    wheelhouse.mkdir(exist_ok=True)
    # Upstream progressbar is source-only. Its pure-Python wheel is portable.
    subprocess.run([python, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheelhouse), "progressbar==2.5"], check=True)
    if not list(wheelhouse.glob("progressbar-2.5-*-none-any.whl")):
        raise RuntimeError("progressbar build did not produce a portable wheel")
    cmd = [python, "-m", "pip", "download", "--dest", str(wheelhouse),
           "--find-links", str(wheelhouse), "--only-binary=:all:",
           "--python-version", "3.11.14", "--implementation", "cp", "--abi", "cp311"]
    for target in ("manylinux_2_28_x86_64", "manylinux_2_17_x86_64", "manylinux2014_x86_64", "linux_x86_64"):
        cmd += ["--platform", target]
    cmd += ["--extra-index-url", "https://download.pytorch.org/whl/cpu",
            "--requirement", str(project / "requirements/runtime-linux-py311.txt")]
    subprocess.run(cmd, check=True)
    entries = []
    for path in sorted(wheelhouse.glob("*.whl")):
        if any(tag in path.name.lower() for tag in ("macosx", "win32", "win_amd64", "aarch64", "arm64")):
            raise RuntimeError(f"Wrong target wheel: {path.name}")
        entries.append(dict(name="wheel", path=str(path), bytes=path.stat().st_size, sha256=sha256(path)))
    return entries


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=["list", "runtime", "python", "wheels", "tiny", "full", "source"], default="list")
    p.add_argument("--root", type=Path, default=Path.home() / "xingliu-transfer/ucmp-week3")
    p.add_argument("--registration-complete", action="store_true")
    args = p.parse_args()
    if args.stage == "list":
        print(json.dumps(ARTIFACTS, indent=2))
        return
    if platform.system() != "Darwin":
        p.error("This public acquisition entry point runs on the Mac only")
    if args.stage == "full" and not args.registration_complete:
        p.error("Complete official asset registration first; then pass --registration-complete")
    root = args.root.expanduser().resolve()
    folder = root / "downloads"
    folder.mkdir(parents=True, exist_ok=True)
    project = Path(__file__).resolve().parents[1]
    # A fresh receipt per invocation preserves historical acquisition evidence.
    rows = []
    if args.stage in ("runtime", "python"):
        rows.append(fetch("python", folder))
    if args.stage in ("runtime", "wheels"):
        rows.extend(wheels(root, project))
    if args.stage in ("tiny", "source"):
        rows.append(fetch(args.stage, folder))
    if args.stage == "full":
        for name in ("full-static", "pedestrians"):
            rows.append(fetch(name, folder))
    receipt = root / ("receipt_" + datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S-%f") + ".json")
    receipt.write_text(json.dumps(dict(stage=args.stage, entries=rows), indent=2) + "\n")
    print(f"MAC_DOWNLOAD_STAGE_COMPLETE {args.stage}\nRECEIPT {receipt}")


if __name__ == "__main__":
    main()
