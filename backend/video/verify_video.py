"""Verify the composed video: picture is never black, audio is never silent.

I cannot watch the file, so this samples frames and audio across the whole
timeline and fails loudly if any stretch is black or silent.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO = Path(__file__).resolve().parents[2] / "vedalex_demo.mp4"


def duration_s(path: Path) -> float:
    out = subprocess.run(
        [FFMPEG, "-i", str(path), "-hide_banner"], capture_output=True, text=True
    ).stderr
    for line in out.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def main() -> int:
    if not VIDEO.exists():
        print("video missing")
        return 1

    dur = duration_s(VIDEO)
    print(f"file   : {VIDEO.name}")
    print(f"size   : {VIDEO.stat().st_size/1024/1024:.1f} MiB")
    print(f"length : {dur:.2f}s\n")

    tmp = Path(tempfile.mkdtemp())
    n = 24
    print("sampling frames ...")
    dark = []
    for i in range(n):
        t = dur * (i + 0.5) / n
        frame = tmp / f"f{i:02d}.png"
        subprocess.run(
            [FFMPEG, "-y", "-ss", f"{t:.2f}", "-i", str(VIDEO), "-frames:v", "1",
             "-vf", "scale=480:-1", str(frame)],
            check=True, capture_output=True,
        )
        with Image.open(frame) as im:
            arr = np.asarray(im.convert("L"), dtype=np.float32)
        mean, std = float(arr.mean()), float(arr.std())
        flag = "DARK" if std < 4.0 else "ok"
        if flag == "DARK":
            dark.append(t)
        print(f"  t={t:6.1f}s  mean={mean:6.1f}  std={std:6.1f}  {flag}")

    print("\nmeasuring audio ...")
    # mean volume per 10s window
    silent = []
    step = 10
    for start in range(0, int(dur), step):
        length = min(step, dur - start)
        r = subprocess.run(
            [FFMPEG, "-ss", str(start), "-t", f"{length}", "-i", str(VIDEO),
             "-af", "volumedetect", "-f", "null", "NUL"],
            capture_output=True, text=True,
        )
        mv = "n/a"
        for line in r.stderr.splitlines():
            if "mean_volume" in line:
                mv = line.split("mean_volume:")[1].split("dB")[0].strip()
        try:
            loud = float(mv) > -50.0
        except ValueError:
            loud = False
        if not loud:
            silent.append(start)
        print(f"  {start:4d}-{start+length:4.0f}s  mean={mv:>7} dB  {'SILENT' if not loud else 'ok'}")

    print()
    if dark:
        print(f"FAIL: {len(dark)} black frame(s) at {['%.1f' % t for t in dark]}")
    if silent:
        print(f"FAIL: {len(silent)} silent window(s) starting at {silent}")
    if not dark and not silent:
        print("PASS: picture never black, audio never silent")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
