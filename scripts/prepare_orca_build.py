#!/usr/bin/env python3
"""Use installed pybind11 for Python 3.11 instead of the vendored old headers."""
from pathlib import Path

def prepare(path):
    before = "add_subdirectory(pybind11)\nfind_package(pybind11 REQUIRED)"
    after = "# UCMP: Python 3.11 uses pinned external pybind11 2.13.6.\nfind_package(pybind11 CONFIG REQUIRED)"
    text = path.read_text()
    if before in text:
        path.write_text(text.replace(before, after, 1))
    elif after not in text:
        raise ValueError("Unknown upstream CMake content; inspect before changing it")


if __name__ == "__main__":
    import argparse
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[1]
    prepare(root / "third_party/metaurban/metaurban/orca_algo/CMakeLists.txt")
    print("ORCA_BUILD_CONFIG_PREPARED")
