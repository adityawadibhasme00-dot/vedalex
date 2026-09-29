import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from gtts import gTTS
from moviepy import *

OUTPUT_DIR = Path(r"C:\Users\adity\OneDrive\Pictures\Desktop\SIH Final\xyz")
TEMP_DIR = Path(r"C:\Users\adity\AppData\Local\Temp\opencode\full_demo")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

WEBSITE_URL = "http://localhost:3000"

HINDI_SEGMENTS = [
    ("intro", "Namaste! Aaj main aapko IP-SAKTI Sahayak ke saare features dikhata hoon. Ye ek complete AI-powered platform hai Ayurveda intellectual property aur regulatory compliance ke liye."),
    ("landing", "Landing page — hero section, 94% Section 3(p) accuracy, 3 jurisdictions, 0% hallucination, 9 languages. Neeche features, knowledge sources, aur compliance sections hain."),
    ("login", "Login page — sign in ya create account. Demo credentials available hain. JWT-based authentication with DPDP Act 2023 compliance."),
    ("dashboard_overview", "Dashboard Overview — welcome section, stats cards, quick actions, recent activity, aur 16 feature cards including Patent Disclosure Sentinel, FTO Map, Claim Firewall, Regulatory Roadmap, aur What-If Simulator."),
    ("ai_copilot", "AI Copilot — RAG-grounded answers with citations. Decision trace, confidence score, source citations, aur escalation recommendation dikhta hai."),
    ("innovation_lab", "Innovation Lab — 19 AI agents grouped by Engineering, IP, Life Sciences, aur Materials. Orchestrator se multi-agent workflow run kar sakte hain."),
    ("passport", "Innovation Passport — IP Route Advisor, passport view, aur multi-step form. Botanical canonicalization automatically hoti hai."),
    ("ip_regulatory", "IP & Regulatory Analysis — Patent readiness scoring, Jurisdiction Matrix, Regulatory Roadmap, aur White Space Navigator."),
    ("evidence", "Evidence & Compliance — Evidence Matrix, Claim Safety Intelligence, Quality Intelligence, aur Document OCR with threat detection."),
    ("bioresource", "Bio-Resource Intelligence — Provenance graph, Knowledge Graph, aur per-plant botanical data with ABS/TK/IP considerations."),
    ("classifier", "Product Classifier — regulatory pathway prediction, pathway scoring, rule validation, aur ABS assessment."),
    ("market", "Market Readiness — India, US, EU, Canada market comparison with gap analysis aur readiness scores."),
    ("whatif", "What-If Simulator — live claim mutation, reactive compliance diff, risk analysis, aur dependency DAG traversal."),
    ("dossier", "Dossier Export — PDF, DOCX, aur CSV export. Filing-ready documents with QR code aur evidence matrix."),
    ("settings", "Settings — 10 Indian languages, profile management, preferences, aur Terminology Mapper for botanical name resolution."),
    ("agent_detail", "Agent Detail — guided questions, document upload, Eureka confirmation, review & run, results with citations, aur Word export."),
    ("closing", "IP-SAKTI Sahayak — Ayurveda innovation ko empower karte hue, citation-grounded AI ke saath. Dhanyavaad!"),
]

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

async def generate_intro_slide():
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body { margin:0; padding:40px; background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); font-family: 'Segoe UI', sans-serif; color: white; }
.container { max-width: 900px; margin: 0 auto; }
h1 { color: #10B981; font-size: 36px; text-align: center; margin-bottom: 10px; }
h2 { color: #D97706; font-size: 18px; text-align: center; font-weight: normal; margin-bottom: 30px; }
.section { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
.section h3 { color: #10B981; margin-top: 0; font-size: 16px; }
.section p { color: #CBD5E1; font-size: 14px; line-height: 1.6; }
.flow { display: flex; align-items: center; justify-content: center; gap: 8px; margin: 15px 0; flex-wrap: wrap; }
.flow-box { background: #059669; padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: bold; }
.flow-arrow { color: #D97706; font-size: 18px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 15px; }
.card h4 { color: #D97706; margin: 0 0 8px 0; font-size: 13px; }
.card p { color: #94A3B8; font-size: 12px; margin: 0; }
</style></head><body>
<div class="container">
<h1>IP-SAKTI Sahayak</h1>
<h2>Ayurveda IP & Regulatory Decision Engine</h2>
<div class="section">
<h3>Problem Statement</h3>
<p>Indian MSMEs file only 16% patents despite 61% trademark registration. Generic LLMs hallucinate 69-88% on legal queries. No unified platform exists for Ayurveda-specific IP guidance with multilingual support.</p>
</div>
<div class="section">
<h3>Solution</h3>
<p>Citation-grounded AI system that prevents hallucinations by decoupling legal logic from language models. Deterministic rule packs classify law — LLM only explains results.</p>
<div class="flow">
<span class="flow-box">User Facts</span><span class="flow-arrow">→</span>
<span class="flow-box">Deterministic Rules</span><span class="flow-arrow">→</span>
<span class="flow-box">Hybrid RAG</span><span class="flow-arrow">→</span>
<span class="flow-box">LLM Explanation</span>
</div>
</div>
<div class="section">
<h3>Key Features</h3>
<div class="grid">
<div class="card"><h4>Multilingual</h4><p>10 Indic languages with botanical canonicalization</p></div>
<div class="card"><h4>Innovation Passport</h4><p>4-section form with QR code generation</p></div>
<div class="card"><h4>AI Copilot</h4><p>RAG-grounded answers with citations</p></div>
<div class="card"><h4>Patent Analysis</h4><p>Novelty, Inventive Step, Overall scores</p></div>
<div class="card"><h4>Regulatory Roadmap</h4><p>6-phase compliance timeline</p></div>
<div class="card"><h4>Dossier Export</h4><p>HTML report with evidence matrix</p></div>
</div>
</div>
</div>
</body></html>"""

    html_path = TEMP_DIR / "intro.html"
    html_path.write_text(html, encoding='utf-8')

    async def screenshot():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={'width': 1280, 'height': 800})
            await page.goto(f'file:///{html_path}')
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(TEMP_DIR / "intro_slide.png"), full_page=True)
            await browser.close()

    await screenshot()
    return TEMP_DIR / "intro_slide.png"

def generate_voiceover(segments, lang, output_name):
    audio_dir = TEMP_DIR / "audio"
    audio_dir.mkdir(exist_ok=True)
    result = []
    for key, text in segments:
        tts = gTTS(text, lang=lang, slow=False)
        path = audio_dir / f"{output_name}_{key}.mp3"
        tts.save(str(path))
        result.append((key, str(path)))
    return result

async def record_all_features():
    video_dir = TEMP_DIR / "recordings"
    video_dir.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            record_video_dir=str(video_dir),
            record_video_size={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        # 1. Landing page
        await page.goto(WEBSITE_URL, wait_until='networkidle')
        await page.wait_for_timeout(3000)
        await page.evaluate('window.scrollTo(0, 800)')
        await page.wait_for_timeout(1000)
        await page.evaluate('window.scrollTo(0, 1600)')
        await page.wait_for_timeout(1000)
        await page.evaluate('window.scrollTo(0, 2400)')
        await page.wait_for_timeout(1000)
        await page.evaluate('window.scrollTo(0, 0)')
        await page.wait_for_timeout(500)

        # 2. Login page
        await page.goto(f'{WEBSITE_URL}/login', wait_until='networkidle')
        await page.wait_for_timeout(2000)

        # 3. Login with demo credentials
        await page.fill('input[type="email"]', 'founder@ayurstartup.in')
        await page.fill('input[type="password"]', 'demo123')
        await page.click('button:has-text("Sign In")')
        await page.wait_for_timeout(3000)

        # 4. Dashboard - Overview
        await page.goto(f'{WEBSITE_URL}/dashboard', wait_until='networkidle')
        await page.wait_for_timeout(3000)

        # 5-14. Navigate through sidebar tabs
        tabs = [
            'AI Assistant',
            'Innovation Lab',
            'Innovation Passport',
            'IP & Regulatory',
            'Evidence & Compliance',
            'Bio-Resource',
            'Product Classifier',
            'Market Readiness',
            'What-If',
            'Dossier',
            'Settings',
        ]

        for tab in tabs:
            try:
                await page.click(f'text={tab}', timeout=5000)
                await page.wait_for_timeout(2000)
            except Exception:
                pass

        # 15. Agent detail
        await page.goto(f'{WEBSITE_URL}/innovation-lab/agents/triz', wait_until='networkidle')
        await page.wait_for_timeout(3000)

        await context.close()
        await browser.close()

    video_files = list(video_dir.glob("*.webm"))
    return video_files[0] if video_files else None

def create_video(intro_img, website_video, voiceover_segments, output_file):
    clips = []

    intro_clip = ImageClip(str(intro_img), duration=8)
    clips.append(intro_clip)

    if website_video and website_video.exists():
        web_clip = VideoFileClip(str(website_video))
        web_clip = web_clip.resized(height=800)
        clips.append(web_clip)

    final = concatenate_videoclips(clips, method="compose")

    audio_clips = []
    for key, audio_path in voiceover_segments:
        if Path(audio_path).exists():
            audio_clip = AudioFileClip(audio_path)
            audio_clips.append(audio_clip)

    if audio_clips:
        combined_audio = concatenate_audioclips(audio_clips)
        if combined_audio.duration > final.duration:
            final = final.with_audio(combined_audio.subclipped(0, final.duration))
        else:
            final = final.with_audio(combined_audio)

    final.write_videofile(str(output_file), fps=24, codec='libx264', audio_codec='aac', threads=4)
    print(f"Video saved: {output_file}")

async def main():
    print("Generating intro slide...")
    intro_img = await generate_intro_slide()

    print("Recording all features...")
    website_video = await record_all_features()

    for lang, segments, output_name in [
        ('hi', HINDI_SEGMENTS, 'hindi'),
        ('en', ENGLISH_SEGMENTS, 'english')
    ]:
        print(f"Generating {lang} voiceover...")
        voiceover = generate_voiceover(segments, lang, output_name)

        output_file = OUTPUT_DIR / f"IP_SAKTI_Full_Demo_{lang}.mp4"
        print(f"Creating {lang} video...")
        create_video(intro_img, website_video, voiceover, output_file)

    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
