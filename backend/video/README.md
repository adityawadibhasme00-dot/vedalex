# Video demo pipeline

Generates the English demo video for Vedalex: narrated problem/solution slides
followed by a live, authenticated website walkthrough.

## Output

`../vedalex_demo.mp4` — 1920x1080, 30 fps, H.264 + AAC 48 kHz stereo, ~5:55.

## Pipeline

| Step | Command | Produces |
| --- | --- | --- |
| 1. assets | `python -m video.build_clips` | `out/*.mp3`, `out/slide_*.png`, `out/page_*.png`, `out/zoom_*.png`, `out/manifest.json` |
| 2. frame QA | `python -m video.verify_frames` | per-asset dimensions/size/colour-variance report |
| 3. compose | `python -m video.compose` | scene segments + `../vedalex_demo.mp4` |
| 4. video QA | `python -m video.verify_video` | timeline frame-blackness and audio-silence report |

`python -m video.compose --mux-only` rebuilds the final file from existing
segments without re-encoding.

## Prerequisites

- Backend on `http://localhost:8000`, frontend on `http://localhost:3000`.
- Playwright Chromium: `python -m playwright install chromium`.
- Extra packages: `pip install edge-tts imageio-ffmpeg playwright pillow numpy`.

## Files

- `script.py` — the 18 scenes. Each has narration text plus a `visual` block of
  `slide`, `page`, or `zoom`. Zoom scenes name a CSS selector; the capture step
  magnifies that element and scales it back to frame.
- `slides.py` — HTML/CSS templates rendered to PNG.
- `build_clips.py` — TTS synthesis, slide rendering, Playwright capture, manifest.
- `compose.py` — ffmpeg segment build, Ken Burns, fades, loudnorm, mux.
- `verify_frames.py`, `verify_video.py` — mechanical QA, no human viewing needed.

## Notes

- Scene length follows the measured narration duration plus a short tail, so
  picture and voice cannot drift. Audio is padded to match exactly.
- The capture step signs in with the demo founder account
  (`founder@ayurstartup.in` / `demo123`) so protected Innovation Lab routes render
  instead of redirecting to the login page.
- Narration uses `en-GB-RyanNeural` at `+4Hz` pitch, chosen to match the median
  pitch of the supplied reference voice (`132.6 Hz`).
- Both verifiers exit non-zero on failure, so they can gate a build.
