"""Demo video script: full English narration, scene by scene.

Pure website walkthrough - no title, problem or architecture slides. Every
scene captures the live product, and the interactive scenes record real motion
(opening an agent, switching dashboard tabs, typing into the copilot) instead
of a static shell.

Each scene carries the narration text plus the visual it is spoken over. The
build pipeline captures the visual, synthesises the audio, measures the real
audio duration, then sets the clip length from that measurement - so narration
and visuals cannot drift apart.

Visual kinds the builder understands:
  page     -> live Playwright screenshot of a real frontend route
  zoom     -> magnified crop of a page capture
  video    -> live Playwright screencast of real clicks and typing

All may carry optional "steps" that run before the capture.

Voice: en-GB-RyanNeural, male, measured 128 Hz against the 133 Hz reference
recording supplied in xyz/.
"""

from __future__ import annotations

VOICE = "en-GB-RyanNeural"
VOICE_PITCH = "+4Hz"

COPILOT_Q = (
    "Is an Ashwagandha and Brahmi composition for healthy sleep patentable? "
    "Cite the law."
)

SCENES: list[dict] = [
    {
        "id": "01_demo_home",
        "visual": {"kind": "page", "route": "/"},
        "text": (
            "This is the live website, starting with the public portal. It is "
            "a calm government style portal, in English and Hindi, built "
            "around the national colors. The portal is fast, clear and honest "
            "about what it does. Everything on the home page leads somewhere "
            "useful."
        ),
    },
    {
        "id": "02_demo_home_zoom",
        "visual": {"kind": "zoom", "route": "/", "selector": "#features"},
        "text": (
            "Scrolling through the portal, you see the complete feature map. "
            "The Innovation Lab for inventors, the IP shield for patents, the "
            "food safety register, the biodiversity register and the policy "
            "dashboard. Each module opens with one click, and every one of "
            "these opens the real tool, not a mockup, with live data behind "
            "it."
        ),
    },
    {
        "id": "03_demo_lab",
        "visual": {"kind": "page", "route": "/innovation-lab"},
        "text": (
            "Next, the Innovation Lab, the heart of the platform. Nine "
            "specialist agents are registered here, each built around Indian "
            "IP law and the traditional knowledge toolkit. Every agent does "
            "one clear job, and every result can be checked."
        ),
    },
    {
        "id": "04_demo_lab_zoom",
        "visual": {"kind": "zoom", "route": "/innovation-lab", "selector": "main"},
        "text": (
            "The agent library lists every specialist with its name, status "
            "and task. Each one is a real workflow with its own inputs and "
            "outputs, judged against official rules rather than free chat. You "
            "can launch any of them in one click, and even the small quick "
            "links jump straight into an agent."
        ),
    },
    {
        "id": "05_demo_open_agent",
        "visual": {
            "kind": "video",
            "route": "/innovation-lab",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": 'text="Novelty Search"'},
                {"action": "wait", "ms": 5000},
            ],
        },
        "text": (
            "Let me open one of these agents live, just like a founder would. "
            "I will click the novelty search card, and the agent's working "
            "surface opens, ready for a real filing. You can see the quick "
            "start buttons and the disclaimer that this is research support, "
            "not legal advice."
        ),
    },
    {
        "id": "06_demo_agent_zoom",
        "visual": {
            "kind": "zoom",
            "route": "/innovation-lab/agents/novelty_search",
            "selector": "main",
        },
        "text": (
            "This is the novelty search agent. It asks for the raw materials, "
            "the extraction method and the target countries, and then it runs "
            "a structured search with a citation behind every source."
        ),
    },
    {
        "id": "07_demo_dashboard",
        "visual": {"kind": "video", "route": "/dashboard",
                   "steps": [{"action": "wait", "ms": 9000}]},
        "text": (
            "This is the entrepreneur dashboard, the founder's working area "
            "after signing in. The system has already created an example "
            "product: Ashwagandha and Brahmi tablets, with a claim that they "
            "support healthy sleep. Everything here runs against the real rule "
            "engine."
        ),
    },
    {
        "id": "08_demo_dashboard_zoom",
        "visual": {"kind": "zoom", "route": "/dashboard", "selector": "main"},
        "text": (
            "This is the command center of the whole platform. In one glance "
            "you see the innovation passport status, the evidence matrix, the "
            "red flags, and quick action buttons for every module, from legal "
            "analysis to export planning."
        ),
    },
    {
        "id": "09_demo_passport",
        "visual": {
            "kind": "video",
            "route": "/dashboard",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "aside button:has-text('Innovation Passport')"},
                {"action": "wait", "ms": 6000},
            ],
        },
        "text": (
            "Let me open the innovation passport by clicking it in the menu. "
            "It captures the complete product story: the raw materials, the "
            "extraction method and the manufacturing process, accepted in "
            "several Indian languages."
        ),
    },
    {
        "id": "10_demo_ipreg",
        "visual": {
            "kind": "video",
            "route": "/dashboard",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "aside button:has-text('IP & Regulatory Base')"},
                {"action": "wait", "ms": 6000},
            ],
        },
        "text": (
            "Now the IP and regulatory base. It checks every protection "
            "route: patentability, novelty, prior art, inventive step and "
            "freedom to operate, and it produces a clear go or no go filing "
            "roadmap for India and abroad. The roadmap tells you the order, "
            "the cost and the risk of each step, so nothing is filed blind."
        ),
    },
    {
        "id": "11_demo_evidence",
        "visual": {
            "kind": "video",
            "route": "/dashboard",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "aside button:has-text('Evidence & Compliance')"},
                {"action": "wait", "ms": 6000},
            ],
        },
        "text": (
            "Next, evidence and compliance. The matrix maps every claim to "
            "its supporting research. A claim without evidence is flagged in "
            "red, with the exact gap and source shown, so you know what to "
            "strengthen. The file you submit is never weaker than the evidence "
            "behind it."
        ),
    },
    {
        "id": "12_demo_biores",
        "visual": {
            "kind": "video",
            "route": "/dashboard",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "aside button:has-text('Bio-Resource Intelligence')"},
                {"action": "wait", "ms": 6000},
            ],
        },
        "text": (
            "The bio resource intelligence view tracks the raw materials "
            "against the Biological Diversity Act. Each plant is matched to "
            "its scientific name, its access obligations and its benefit "
            "sharing position."
        ),
    },
    {
        "id": "13_demo_classify",
        "visual": {
            "kind": "video",
            "route": "/dashboard",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "aside button:has-text('Product Classifier')"},
                {"action": "wait", "ms": 6000},
            ],
        },
        "text": (
            "The product classifier reads the claim on the label and splits "
            "it into compliance parts. Health claims, disease claims and "
            "therapeutic claims each take a separate legal route."
        ),
    },
    {
        "id": "14_demo_market",
        "visual": {
            "kind": "video",
            "route": "/dashboard",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "aside button:has-text('Market Readiness')"},
                {"action": "wait", "ms": 6000},
            ],
        },
        "text": (
            "The market readiness module tests the product country by country, "
            "India, the United States or Canada. It compares the labeling and "
            "regulation differences before you spend money on an export."
        ),
    },
    {
        "id": "15_demo_copilot",
        "visual": {
            "kind": "video",
            "route": "/dashboard",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "aside button:has-text('AI Assistant')"},
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "input[placeholder*='Type or speak']"},
                {"action": "type", "locator": "input[placeholder*='Type or speak']",
                 "value": COPILOT_Q, "delay": 30},
                {"action": "press", "locator": "input[placeholder*='Type or speak']", "key": "Enter"},
                {"action": "wait", "ms": 12000},
            ],
        },
        "text": (
            "Now the most asked about feature, the AI copilot. Watch me ask it "
            "a real question. I will type: is this Ashwagandha and Brahmi "
            "composition patentable, and cite the law. And here is the live "
            "answer, because the search is real."
        ),
    },
    {
        "id": "16_demo_copilot_zoom",
        "visual": {
            "kind": "zoom",
            "route": "/dashboard#copilot",
            "selector": "main",
            "steps": [
                {"action": "wait", "ms": 3000},
                {"action": "eval", "script": (
                    "window.dispatchEvent(new CustomEvent('ipsakti:copilot-question',"
                    "{detail:'Is an Ashwagandha and Brahmi composition for healthy "
                    "sleep patentable? Cite the law.'}))"
                )},
                {"action": "wait", "ms": 15000},
            ],
        },
        "text": (
            "Notice everything the copilot shows. First the answer text, then "
            "a confidence score, the retrieval engines used, and a sources "
            "panel with every document behind the answer. No invented "
            "citations, every claim traceable. This is exactly what a founder "
            "needs before making any decision."
        ),
    },
    {
        "id": "17_demo_whatif",
        "visual": {
            "kind": "video",
            "route": "/dashboard",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "aside button:has-text('What-If Simulator')"},
                {"action": "wait", "ms": 6000},
            ],
        },
        "text": (
            "The what if simulator shows what happens if you change a raw "
            "material, a dosage or a claim. The same rule engine recalculates "
            "the whole verdict on the spot, so an idea can be tested without "
            "touching a lawyer or spending money."
        ),
    },
    {
        "id": "18_demo_dossier",
        "visual": {
            "kind": "video",
            "route": "/dashboard",
            "steps": [
                {"action": "wait", "ms": 2500},
                {"action": "click", "locator": "aside button:has-text('Dossier Export')"},
                {"action": "wait", "ms": 6000},
            ],
        },
        "text": (
            "Finally the dossier. The system assembles everything into one "
            "clean report: claims, evidence, citations and a legal summary, "
            "ready to hand to an attorney or an investor."
        ),
    },
    {
        "id": "19_demo_settings",
        "visual": {"kind": "page", "route": "/dashboard#settings"},
        "text": (
            "And in settings you control the terminology and the language of "
            "the whole platform, keeping external communication in English and "
            "Hindi as needed, and everything stays consistent in one workspace. "
            "That is the complete walkthrough. Thank you for watching."
        ),
    },
]

# Scene types that capture the live application rather than a rendered slide.
LIVE_SCENES = [s for s in SCENES if s["visual"]["kind"] in ("page", "zoom", "video")]
SLIDE_SCENES = [s for s in SCENES if s["visual"]["kind"] == "slide"]