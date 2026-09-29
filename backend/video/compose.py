"""Compose the final demo video: picture length follows the real audio duration.

For each scene the still is held for the measured narration length plus a short
breathing tail, given a slow Ken Burns push so the frame never looks frozen, faded
at the edges, and matched with an equal length of silence. Video and audio are
then concatenated, so narration and picture cannot drift apart.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SEG = OUT / "segments"
FINAL = HERE.parent.parent / "vedalex_demo.mp4"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1920, 1080, 30
TAIL = 0.55          # seconds of breathing room after each line
FADE = 0.30          # fade in/out on every scene

sys.path.insert(0, str(HERE.parent))
from video.script import SCENES  # noqa: E402


def run(args: list[str]) -> None:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        tail = "\n".join(r.stderr.strip().splitlines()[-14:])
        raise RuntimeError(f"ffmpeg failed:\n{tail}")


def visual_for(scene: dict, index: int) -> Path:
    v = scene["visual"]
    if v["kind"] == "slide":
        return OUT / f"slide_{scene['id']}.png"
    route = v["route"]
    slug = route.strip("/").replace("/", "_") or "home"
    return OUT / (f"page_{slug}.png" if v["kind"] == "page" else f"zoom_{slug}.png")


def zoom_expr(index: int, frames: int) -> str:
    """A slow push-in or pull-out, so a held still never looks frozen.

    d=1 makes zoompan emit one output frame per input frame, so `on` is the
    output frame index and the ramp is linear across the clip.
    """
    total = max(frames - 1, 1)
    if index % 2 == 0:
        return f"1+0.09*on/{total}"
    return f"1.09-0.09*on/{total}"


def build_scene(scene: dict, index: int, duration: float) -> tuple[Path, Path]:
    SEG.mkdir(parents=True, exist_ok=True)
    src = visual_for(scene, index)
    if not src.exists():
        raise FileNotFoundError(f"missing visual for {scene['id']}: {src}")

    vout = SEG / f"{index:02d}_{scene['id']}_v.mp4"
    aout = SEG / f"{index:02d}_{scene['id']}_a.m4a"
    frames = int(round(duration * FPS))

    run([FFMPEG, "-y", "-loop", "1", "-i", str(src),
         "-t", f"{duration:.3f}",
         "-vf",
         f"scale={W*2}:{H*2}:flags=lanczos,"
         f"zoompan=z='{zoom_expr(index, frames)}':d=1:"
         f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
         f"fade=t=in:st=0:d={FADE},fade=t=out:st={duration-FADE:.3f}:d={FADE},"
         f"format=yuv420p",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-an", str(vout)])

    run([FFMPEG, "-y", "-i", str(OUT / f"{scene['id']}.mp3"),
         "-af", f"apad=pad_dur={TAIL}", "-t", f"{duration:.3f}",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", str(aout)])

    return vout, aout


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--mux-only", action="store_true",
                    help="rebuild the final file from existing segments")
    args = ap.parse_args()

    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    durations = {c["id"]: c["duration"] for c in manifest["clips"]}

    if args.mux_only:
        vlist = SEG / "video.txt"
        alist = SEG / "audio.txt"
        if not (vlist.exists() and alist.exists()):
            print("no segments to re-mux; run without --mux-only first")
            return 1
        print("re-muxing only ...")
    else:
        if SEG.exists():
            shutil.rmtree(SEG)
        vparts: list[Path] = []
        aparts: list[Path] = []
        for i, scene in enumerate(SCENES, 1):
            dur = durations[scene["id"]] + TAIL
            v, a = build_scene(scene, i, dur)
            vparts.append(v)
            aparts.append(a)
            print(f"  [{i:>2}/{len(SCENES)}] {scene['id']:<30} {dur:6.2f}s")

        vlist = SEG / "video.txt"
        alist = SEG / "audio.txt"
        vlist.write_text("".join(f"file '{p.name}'\n" for p in vparts), encoding="utf-8")
        alist.write_text("".join(f"file '{p.name}'\n" for p in aparts), encoding="utf-8")

    print("\nconcatenating ...")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(vlist),
         "-c", "copy", str(SEG / "video_all.mp4")])
    # loudnorm brings the TTS narration to a broadcast-consistent level; raw edge
    # TTS sits around -24 dB, which is quiet on laptop speakers.
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(alist),
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
         str(SEG / "audio_all.m4a")])

    print(f"muxing -> {FINAL.name} ...")
    run([FFMPEG, "-y", "-i", str(SEG / "video_all.mp4"), "-i", str(SEG / "audio_all.m4a"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
         "-shortest", str(FINAL)])

    probe = subprocess.run(
        [FFMPEG, "-i", str(FINAL), "-hide_banner"],
        capture_output=True, text=True,
    )
    for line in probe.stderr.splitlines():
        if "Duration" in line or "Stream #" in line:
            print("  " + line.strip())
    size = FINAL.stat().st_size / (1024 * 1024)
    print(f"\nfinal: {FINAL}  ({size:.1f} MiB)")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
