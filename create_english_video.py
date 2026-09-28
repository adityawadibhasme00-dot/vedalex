import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from gtts import gTTS
from moviepy import *

OUTPUT_DIR = Path(r"C:\Users\adity\OneDrive\Pictures\Desktop\SIH Final\xyz")
TEMP_DIR = Path(r"C:\Users\adity\AppData\Local\Temp\opencode\full_demo")

ENGLISH_SEGMENTS = [
    ("intro", "Hello! Today I will show you all features of IP-SAKTI Sahayak. It is a complete AI-powered platform for Ayurveda intellectual property and regulatory compliance."),
    ("landing", "Landing page — hero section, 94% Section 3(p) accuracy, 3 jurisdictions, 0% hallucination, 9 languages. Below are features, knowledge sources, and compliance sections."),
    ("login", "Login page — sign in or create account. Demo credentials available. JWT-based authentication with DPDP Act 2023 compliance."),
    ("dashboard_overview", "Dashboard Overview — welcome section, stats cards, quick actions, recent activity, and 16 feature cards including Patent Disclosure Sentinel, FTO Map, Claim Firewall, Regulatory Roadmap, and What-If Simulator."),
    ("ai_copilot", "AI Copilot — RAG-grounded answers with citations. Decision trace, confidence score, source citations, and escalation recommendation."),
    ("innovation_lab", "Innovation Lab — 19 AI agents grouped by Engineering, IP, Life Sciences, and Materials. Orchestrator for multi-agent workflow."),
    ("passport", "Innovation Passport — IP Route Advisor, passport view, and multi-step form. Botanical canonicalization happens automatically."),
    ("ip_regulatory", "IP & Regulatory Analysis — Patent readiness scoring, Jurisdiction Matrix, Regulatory Roadmap, and White Space Navigator."),
    ("evidence", "Evidence & Compliance — Evidence Matrix, Claim Safety Intelligence, Quality Intelligence, and Document OCR with threat detection."),
    ("bioresource", "Bio-Resource Intelligence — Provenance graph, Knowledge Graph, and per-plant botanical data with ABS/TK/IP considerations."),
    ("classifier", "Product Classifier — regulatory pathway prediction, pathway scoring, rule validation, and ABS assessment."),
    ("market", "Market Readiness — India, US, EU, Canada market comparison with gap analysis and readiness scores."),
    ("whatif", "What-If Simulator — live claim mutation, reactive compliance diff, risk analysis, and dependency DAG traversal."),
    ("dossier", "Dossier Export — PDF, DOCX, and CSV export. Filing-ready documents with QR code and evidence matrix."),
    ("settings", "Settings — 10 Indian languages, profile management, preferences, and Terminology Mapper for botanical name resolution."),
    ("agent_detail", "Agent Detail — guided questions, document upload, Eureka confirmation, review and run, results with citations, and Word export."),
    ("closing", "IP-SAKTI Sahayak — empowering Ayurveda innovation with citation-grounded AI. Thank you!"),
]

async def record_all_features():
    video_dir = TEMP_DIR / "recordings_en"
    video_dir.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        await page.goto("http://localhost:3000", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, 800)")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0, 1600)")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0, 2400)")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        await page.goto("http://localhost:3000/login", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        await page.fill("input[type='email']", "founder@ayurstartup.in")
        await page.fill("input[type='password']", "demo123")
        await page.click("button:has-text('Sign In')")
        await page.wait_for_timeout(3000)

        await page.goto("http://localhost:3000/dashboard", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        tabs = ["AI Assistant", "Innovation Lab", "Innovation Passport", "IP & Regulatory", "Evidence & Compliance", "Bio-Resource", "Product Classifier", "Market Readiness", "What-If", "Dossier", "Settings"]

        for tab in tabs:
            try:
                await page.click(f"text={tab}", timeout=5000)
                await page.wait_for_timeout(2000)
            except Exception:
                pass

        await page.goto("http://localhost:3000/innovation-lab/agents/triz", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        await context.close()
        await browser.close()

    video_files = list(video_dir.glob("*.webm"))
    return video_files[0] if video_files else None

async def main():
    print("Recording website...")
    website_video = await record_all_features()

    print("Generating voiceover...")
    audio_dir = TEMP_DIR / "audio_en"
    audio_dir.mkdir(exist_ok=True)
    audio_clips = []
    for key, text in ENGLISH_SEGMENTS:
        tts = gTTS(text, lang="en", slow=False)
        path = audio_dir / f"{key}.mp3"
        tts.save(str(path))
        audio_clips.append(AudioFileClip(str(path)))

    combined_audio = concatenate_audioclips(audio_clips)

    intro_img = TEMP_DIR / "intro_slide.png"
    intro_clip = ImageClip(str(intro_img), duration=8)

    if website_video and website_video.exists():
        web_clip = VideoFileClip(str(website_video))
        web_clip = web_clip.resized(height=800)
        final = concatenate_videoclips([intro_clip, web_clip], method="compose")
    else:
        final = intro_clip

    if combined_audio.duration > final.duration:
        final = final.with_audio(combined_audio.subclipped(0, final.duration))
    else:
        final = final.with_audio(combined_audio)

    output_file = OUTPUT_DIR / "IP_SAKTI_Full_Demo_EN.mp4"
    final.write_videofile(str(output_file), fps=24, codec="libx264", audio_codec="aac", threads=4, preset="fast", ffmpeg_params=["-movflags", "+faststart"])
    print(f"Video saved: {output_file}")

asyncio.run(main())
