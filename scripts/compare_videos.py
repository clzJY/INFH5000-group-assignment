#!/usr/bin/env python3
"""Join real same-condition videos; label held frames after an episode ends."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("episodes", nargs=3, type=Path, help="baseline, distance, predictive episode directories")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("Output already exists")
    summaries = [json.loads((d / "summary.json").read_text()) for d in args.episodes]
    if [r["method"] for r in summaries] != ["baseline", "distance", "predictive"]:
        p.error("Expected baseline, distance, predictive in that order")
    for key in ("seed", "config_sha256", "initial_scene_fingerprint", "checkpoint_sha256", "dt_s"):
        if len({r[key] for r in summaries}) != 1:
            p.error(f"Videos are not matched: {key}")
    import cv2
    import imageio.v2 as imageio
    import numpy as np
    readers = [imageio.get_reader(str(d / "rollout.mp4")) for d in args.episodes]
    writer = None
    try:
        previous = [None] * 3
        ended = [False] * 3
        while True:
            panels = []
            advanced = False
            for i, reader in enumerate(readers):
                if not ended[i]:
                    try:
                        previous[i] = reader.get_next_data()
                        advanced = True
                    except (IndexError, StopIteration):
                        ended[i] = True
                if previous[i] is None:
                    raise ValueError("Video has no frames")
                frame = previous[i].copy()
                if ended[i]:
                    cv2.putText(frame, "EPISODE ENDED - HELD FRAME", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                panels.append(frame)
            if not advanced:
                break
            combined = np.concatenate(panels, axis=1)
            if writer is None:
                writer = imageio.get_writer(str(args.output), fps=1 / summaries[0]["dt_s"], codec="libx264", macro_block_size=1)
            writer.append_data(combined)
    finally:
        if writer:
            writer.close()
        for reader in readers:
            reader.close()
    print("MATCHED_VIDEO_COMPARISON_WRITTEN", args.output)


if __name__ == "__main__":
    main()
