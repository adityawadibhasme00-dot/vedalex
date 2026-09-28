import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from gtts import gTTS
from moviepy import *

OUTPUT_DIR = Path(r"C:\Users\adity\OneDrive\Pictures\Desktop\SIH Final\xyz")
TEMP_DIR = Path(r"C:\Users\adity\AppData\Local\Temp\opencode\video_demo")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

WEBSITE_URL = "http://localhost:3000"

HINDI_SCRIPT = [
    ("intro", "Namaste! Aaj main aapko dikhata hoon IP-SAKTI Sahayak — Ayurveda Intellectual Property aur Regulatory Decision Engine. Ye ek AI-powered platform hai jo Ayurveda researchers, startups, MSMEs aur patent professionals ko Idea se Innovation Passport, Patent Analysis, Compliance aur Commercialization tak guide karta hai."),
    ("problem", "Problem Statement: Indian MSMEs sirf 16% patents file karte hain, jabki 61% trademarks register karte hain. Main reasons hain procedural complexity, high legal fees, aur cross-border regulatory clarity ki kami. Generic LLMs legal queries par 69-88% hallucinate karte hain."),
    ("solution", "Solution: IP-SAKTI ek citation-grounded decision-support system hai jo hallucinations prevent karta hai legal logic ko language models se decouple karke. LLM kabhi law classify nahi karta — deterministic rule packs karte hain. Har statement statutory passage se anchored hota hai."),
    ("homepage", "Ye hai hamara homepage. Yahan se aap dashboard, innovation lab, aur saare features access kar sakte hain. Interface multilingual hai — 10 Indic languages supported hain."),
    ("login", "Pehle login page. Yahan aap sign up ya login kar sakte hain. JWT-based authentication use hota hai with DPDP Act 2023 compliance."),
    ("dashboard", "Ye hai dashboard. Yahan overview cards dikhte hain — Passport status, Patent Readiness score, Evidence gaps, aur Next Action items. Sab kuch ek nazar mein."),
    ("passport", "Innovation Passport — 4-step form hai: basic info, multilingual formulation input, process description, aur claims. Botanical canonicalization automatically hoti hai — jaise Haridra ko Curcuma longa mein map kiya jata hai."),
    ("formulation", "Multilingual formulation input — aap Hindi, Marathi, Tamil, Telugu, Kannada, Bengali, Gujarati, Malayalam, Sanskrit ya English mein ingredients enter kar sakte hain. System automatically canonical botanical names mein convert karta hai."),
    ("upload", "Document upload feature — PDF, DOCX, TXT ya images upload karein. Sandboxed extraction with prompt-injection defense se text safely extract hota hai."),
    ("copilot", "AI Copilot — RAG-grounded answers with citations. Har answer ke saath sources aur confidence score dikhta hai. Unsupported Claim Rate 5% se kam rakha jata hai."),
    ("analysis", "Patent Analysis — Novelty, Inventive Step, aur Overall readiness scores. 4-band confidence system: High, Medium, Low, aur Insufficient Evidence."),
    ("roadmap", "Regulatory Roadmap — 6-phase timeline for compliance. India ASU Drug, Ayurveda Aahara, US FDA DSHEA, aur Canada NHP pathways supported hain."),
    ("firewall", "Claim Firewall — label copy analyze karein compliance risks ke liye. Section 3(p) Traditional Knowledge vulnerabilities identify hoti hain."),
    ("export", "Dossier Export — HTML report with QR code, Patent Score, aur Evidence matrix. Sab kuch ek click mein download ho jata hai."),
    ("closing", "IP-SAKTI Sahayak — Ayurveda innovation ko empower karte hue, citation-grounded AI ke saath. Dhanyavaad!"),
]

ENGLISH_SCRIPT = [
    ("intro", "Hello! Today I will show you IP-SAKTI Sahayak — an Ayurveda Intellectual Property and Regulatory Decision Engine. It is an AI-powered platform that guides Ayurveda researchers, startups, MSMEs, and patent professionals from Idea to Innovation Passport, Patent Analysis, Compliance, and Commercialization."),
    ("problem", "Problem Statement: Indian MSMEs file only 16% of patents despite 61% trademark registration. The main reasons are procedural complexity, high legal fees, and lack of cross-border regulatory clarity. Generic LLMs hallucinate 69 to 88 percent on legal queries."),
    ("solution", "Solution: IP-SAKTI is a citation-grounded decision-support system that prevents hallucinations by decoupling legal logic from language models. The LLM never classifies law — deterministic rule packs do. Every statement is anchored to a statutory passage."),
    ("homepage", "This is our homepage. From here you can access the dashboard, innovation lab, and all features. The interface is multilingual — 10 Indic languages are supported."),
    ("login", "First, the login page. Here you can sign up or log in. JWT-based authentication is used with DPDP Act 2023 compliance."),
    ("dashboard", "This is the dashboard. Overview cards show Passport status, Patent Readiness score, Evidence gaps, and Next Action items. Everything at a glance."),
    ("passport", "Innovation Passport — a 4-step form: basic info, multilingual formulation input, process description, and claims. Botanical canonicalization happens automatically — for example, Haridra is mapped to Curcuma longa."),
    ("formulation", "Multilingual formulation input — you can enter ingredients in Hindi, Marathi, Tamil, Telugu, Kannada, Bengali, Gujarati, Malayalam, Sanskrit, or English. The system automatically converts to canonical botanical names."),
    ("upload", "Document upload feature — upload PDF, DOCX, TXT, or images. Sandboxed extraction with prompt-injection defense safely extracts text."),
    ("copilot", "AI Copilot — RAG-grounded answers with citations. Every answer shows sources and a confidence score. Unsupported Claim Rate is kept below 5 percent."),
    ("analysis", "Patent Analysis — Novelty, Inventive Step, and Overall readiness scores. 4-band confidence system: High, Medium, Low, and Insufficient Evidence."),
    ("roadmap", "Regulatory Roadmap — 6-phase timeline for compliance. India ASU Drug, Ayurveda Aahara, US FDA DSHEA, and Canada NHP pathways are supported."),
    ("firewall", "Claim Firewall — analyze label copy for compliance risks. Section 3(p) Traditional Knowledge vulnerabilities are identified."),
    ("export", "Dossier Export — HTML report with QR code, Patent Score, and Evidence matrix. Everything downloads in one click."),
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

def generate_voiceover(script, lang, output_name):
    audio_dir = TEMP_DIR / "audio"
    audio_dir.mkdir(exist_ok=True)
    segments = []
    for key, text in script:
        tts = gTTS(text, lang=lang, slow=False)
        path = audio_dir / f"{output_name}_{key}.mp3"
        tts.save(str(path))
        segments.append((key, str(path)))
    return segments

async def record_website():
    video_dir = TEMP_DIR / "website_video"
    video_dir.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            record_video_dir=str(video_dir),
            record_video_size={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        pages_config = [
            ("homepage", WEBSITE_URL, 4),
            ("login", f"{WEBSITE_URL}/login", 3),
            ("dashboard", f"{WEBSITE_URL}/dashboard", 5),
            ("passport", f"{WEBSITE_URL}/innovation-lab", 5),
        ]

        for name, url, wait_sec in pages_config:
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(wait_sec * 1000)

        await context.close()
        await browser.close()

    video_files = list(video_dir.glob("*.webm"))
    if video_files:
        return video_files[0]
    return None

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

    print("Recording website...")
    website_video = await record_website()

    for lang, script, output_name in [
        ('hi', HINDI_SCRIPT, 'hindi'),
        ('en', ENGLISH_SCRIPT, 'english')
    ]:
        print(f"Generating {lang} voiceover...")
        voiceover = generate_voiceover(script, lang, output_name)

        output_file = OUTPUT_DIR / f"IP_SAKTI_Demo_{lang}.mp4"
        print(f"Creating {lang} video...")
        create_video(intro_img, website_video, voiceover, output_file)

    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
