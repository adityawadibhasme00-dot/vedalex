"""Verify every rendered asset is a real, non-blank frame.

I cannot view the images, so this checks mechanically: correct dimensions,
non-trivial size, and enough colour variance to rule out a blank page or a
failed render.
"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent / "out"


def check(p: Path) -> tuple[bool, str]:
    try:
        with Image.open(p) as im:
            im.load()
            w, h = im.size
            arr = np.asarray(im.convert("RGB"), dtype=np.float32)
    except Exception as exc:
        return False, f"unreadable: {type(exc).__name__}"

    if w < 200 or h < 200:
        return False, f"too small {w}x{h}"
    if p.stat().st_size < 5000:
        return False, f"suspiciously small file ({p.stat().st_size} B)"

    std = arr.std()
    uniq = len(np.unique(arr[::7, ::7].reshape(-1, 3), axis=0))
    if std < 3.0:
        return False, f"near-uniform image (std={std:.2f}) - probably blank"
    if uniq < 12:
        return False, f"too few distinct colours ({uniq}) - probably blank"
    return True, f"{w}x{h}  {p.stat().st_size//1024} KiB  std={std:5.1f}  colours={uniq}"


files = sorted(OUT.glob("*.png"))
print(f"checking {len(files)} rendered frames\n")
bad = 0
for p in files:
    ok, msg = check(p)
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'BAD '} {p.name:<40} {msg}")

print(f"\n{len(files)-bad} usable, {bad} rejected")
raise SystemExit(1 if bad else 0)
