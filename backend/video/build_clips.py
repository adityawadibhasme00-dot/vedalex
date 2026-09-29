"""Render the demo deck: TTS narration, slide renders, and live page captures.

Outputs one clip per scene into video/out/ plus a timings manifest, so the
composer can assemble the final video with picture length derived from the real
measured audio duration.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FRONTEND = "http://localhost:3000"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

sys.path.insert(0, str(HERE.parent))
from video.script import SCENES, VOICE, VOICE_PITCH  # noqa: E402
from video.slides import render  # noqa: E402


# ---------------------------------------------------------------------------
# narration
# ---------------------------------------------------------------------------

async def synth(text: str, out_mp3: Path) -> None:
    import edge_tts

    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text, VOICE, pitch=VOICE_PITCH).save(str(out_mp3))
            if out_mp3.exists() and out_mp3.stat().st_size > 2000:
                return
            last = "empty output"
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"TTS failed after 4 attempts: {last}")


def measure(mp3: Path) -> float:
    wav = mp3.with_suffix(".measure.wav")
    subprocess.run(
        [FFMPEG, "-y", "-i", str(mp3), "-ac", "1", "-ar", "24000", str(wav)],
        check=True, capture_output=True,
    )
    with wave.open(str(wav), "rb") as w:
        dur = w.getnframes() / w.getframerate()
    wav.unlink(missing_ok=True)
    return dur


# ---------------------------------------------------------------------------
# visuals
# ---------------------------------------------------------------------------

async def render_slide(html: str, out_png: Path) -> None:
    from playwright.async_api import async_playwright

    tmp = OUT / "_slide.html"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(html, encoding="utf-8")

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--force-color-profile=srgb"])
        page = await browser.new_page(viewport={"width": 1920, "height": 1080},
                                      device_scale_factor=1)
        await page.goto(tmp.resolve().as_uri())
        await page.wait_for_timeout(320)
        await page.screenshot(path=str(out_png))
        await browser.close()
    tmp.unlink(missing_ok=True)


async def _login(page) -> bool:
    """Sign in with the demo account so protected routes render."""
    try:
        await page.goto(f"{FRONTEND}/login", wait_until="networkidle", timeout=45000)
    except Exception:
        await page.goto(f"{FRONTEND}/login", wait_until="load", timeout=45000)
    await page.wait_for_timeout(1500)

    btn = page.locator("text=Startup / MSME Founder").first
    if await btn.count() == 0:
        print("    WARN demo login button not found")
        return False
    await btn.click()
    await page.wait_for_timeout(700)
    await page.locator("button[type=submit]").first.click()
    await page.wait_for_timeout(4000)
    ok = "/login" not in page.url
    print(f"    demo login {'OK' if ok else 'FAILED (still on /login)'}")
    return ok


async def capture_pages(routes: dict, viewport: dict) -> None:
    """Full-viewport and magnified captures for each live route."""
    from playwright.async_api import async_playwright

    OUT.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--force-color-profile=srgb"])
        ctx = await browser.new_context(viewport=viewport, device_scale_factor=2)
        page = await ctx.new_page()

        await _login(page)

        for route, spec in routes.items():
            selector = spec.get("selector") if isinstance(spec, dict) else spec
            slug = route.strip("/").replace("/", "_") or "home"
            try:
                await page.goto(f"{FRONTEND}{route}", wait_until="networkidle", timeout=45000)
            except Exception:
                await page.goto(f"{FRONTEND}{route}", wait_until="load", timeout=45000)
            await page.wait_for_timeout(2800)

            full = OUT / f"page_{slug}.png"
            await page.screenshot(path=str(full), full_page=False)
            print(f"  page  {route}")

            if not selector:
                continue

            el = None
            try:
                el = await page.query_selector(selector)
            except Exception:
                el = None
            if el is None:
                print(f"    WARN selector {selector!r} not found on {route}; falling back to full frame")
                await page.screenshot(path=str(OUT / f"zoom_{slug}.png"), full_page=False)
                continue

            # Magnify: scroll the target to the top of the viewport, then capture a
            # tight crop around it and upscale to full frame.
            await el.evaluate("e => e.scrollIntoView({block:'start'})")
            await page.wait_for_timeout(900)
            box = await el.bounding_box()
            if not box:
                await page.screenshot(path=str(OUT / f"zoom_{slug}.png"), full_page=False)
                continue
            vw, vh = viewport["width"], viewport["height"]
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + min(box["height"], vh) / 2
            half_w, half_h = vw * 0.34, vh * 0.36
            clip = {
                "x": max(0, min(cx - half_w, vw - vw * 0.68)),
                "y": max(0, min(cy - half_h, vh - vh * 0.72)),
                "width": vw * 0.68,
                "height": vh * 0.72,
            }
            await page.screenshot(path=str(OUT / f"zoom_{slug}.png"), clip=clip)
            print(f"  zoom  {route}  ({selector})  target {box['width']:.0f}x{box['height']:.0f}")

        await browser.close()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

async def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    total = len(SCENES)

    print(f"synthesising {total} narration clips with {VOICE} ...")
    clips: list[dict] = []
    for i, scene in enumerate(SCENES, 1):
        mp3 = OUT / f"{scene['id']}.mp3"
        t0 = time.time()
        await synth(scene["text"], mp3)
        dur = measure(mp3)
        print(f"  [{i:>2}/{total}] {scene['id']:<26} {dur:6.2f}s  ({time.time()-t0:.1f}s)")
        clips.append({"id": scene["id"], "mp3": str(mp3), "duration": dur})

    print("rendering slides ...")
    for i, scene in enumerate(SCENES, 1):
        if scene["visual"]["kind"] != "slide":
            continue
        png = OUT / f"slide_{scene['id']}.png"
        await render_slide(render(scene["visual"]["template"], i, total), png)
        print(f"  [{i:>2}/{total}] {scene['id']}")

    print("capturing live pages ...")
    routes: dict[str, dict] = {}
    for scene in SCENES:
        v = scene["visual"]
        if v["kind"] == "page":
            routes.setdefault(v["route"], {"selector": None})
        elif v["kind"] == "zoom":
            routes[v["route"]] = {"selector": v.get("selector")}
    await capture_pages(routes, {"width": 1920, "height": 1080})

    manifest = {
        "voice": VOICE,
        "pitch": VOICE_PITCH,
        "scene_count": total,
        "clips": clips,
        "total_narration_s": round(sum(c["duration"] for c in clips), 2),
        "slides": [s["id"] for s in SCENES if s["visual"]["kind"] == "slide"],
        "pages": [s["id"] for s in SCENES if s["visual"]["kind"] == "page"],
        "zooms": [s["id"] for s in SCENES if s["visual"]["kind"] == "zoom"],
        "routes": sorted(routes),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\ntotal narration: {manifest['total_narration_s']:.1f}s")
    print(f"manifest: {OUT / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
