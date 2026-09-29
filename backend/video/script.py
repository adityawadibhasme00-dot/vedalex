"""Demo video script: full English narration, scene by scene.

Each scene carries the narration text plus the visual it is spoken over. The
build pipeline renders the slide, synthesises the audio, measures the real audio
duration, then sets the clip length from that measurement - so narration and
visuals cannot drift apart.

Voice: en-GB-RyanNeural, male, measured 128 Hz against the 133 Hz reference
recording supplied in xyz/.
"""

from __future__ import annotations

# Visual kinds the builder understands:
#   slide    -> rendered from HTML by the deck builder
#   page     -> live Playwright capture of a real frontend route
#   zoom     -> magnified crop of the previous page capture
# en-GB-RyanNeural measured 128 Hz against the 133 Hz reference in xyz/, the
# closest of the sampled male English voices.
VOICE = "en-GB-RyanNeural"
VOICE_PITCH = "+4Hz"

SCENES: list[dict] = [
    # ----------------------------------------------------------------- intro
    {
        "id": "01_title",
        "visual": {"kind": "slide", "template": "title"},
        "text": (
            "Vedalex. A research and compliance workspace for Indian traditional "
            "knowledge. This video covers the problem it solves, the architecture "
            "behind it, and a walkthrough of the live product."
        ),
    },
    # --------------------------------------------------------------- problem
    {
        "id": "02_problem_headline",
        "visual": {"kind": "slide", "template": "problem_headline"},
        "text": (
            "Let us start with the problem. A formulation scientist in India can "
            "often tell you that a formulation works, because it has been handed "
            "down for generations. What that person usually cannot tell you is "
            "whether the same idea has already been claimed by somebody else."
        ),
    },
    {
        "id": "03_problem_diagram",
        "visual": {"kind": "slide", "template": "problem_diagram"},
        "text": (
            "Four failures happen at the same time. Traditional knowledge is "
            "oral, so it is undocumented and therefore hard to search. Commercial "
            "prior art lives inside paywalled patent databases. The legal tests "
            "that decide whether you can even patent something are spread across "
            "many separate statutes. And manual search is slow, expensive, and "
            "quietly incomplete, because nobody reads every relevant document. "
            "The result is that good work gets blocked, or worse, gets "
            "accidentally patented by somebody else."
        ),
    },
    {
        "id": "04_problem_tkdl",
        "visual": {"kind": "slide", "template": "problem_tkdl"},
        "text": (
            "This is not theoretical. Defensive publications by India in the "
            "Traditional Knowledge Digital Library have been cited against Indian "
            "companies in patent offices abroad. And under Section Three of the "
            "Patents Act, a patent cannot be granted on matter that is already in "
            "the public domain, including plant matter, unless disclosed to the "
            "public. Get that wrong, and you lose the filing, the money, and the "
            "date."
        ),
    },
    {
        "id": "05_problem_llm",
        "visual": {"kind": "slide", "template": "problem_llm"},
        "text": (
            "The obvious answer, a general purpose language model, makes it worse. "
            "Ask one whether an Ayurvedic formulation is novel and it will "
            "confidently invent a citation, quote a statute that does not say what "
            "was claimed, and give you a patent number that does not exist. In a "
            "compliance context, a fluent wrong answer is more expensive than no "
            "answer at all."
        ),
    },
    # --------------------------------------------------------------- solution
    {
        "id": "06_solution_headline",
        "visual": {"kind": "slide", "template": "solution_headline"},
        "text": (
            "Vedalex is built around one rule: never assert anything that cannot be "
            "traced to a source. The system is three layers, and the language "
            "model is only the top one."
        ),
    },
    {
        "id": "07_solution_diagram",
        "visual": {"kind": "slide", "template": "solution_diagram"},
        "text": (
            "The bottom layer is the law. Deterministic rule packs encode the actual "
            "tests, starting with Section Three of the Patents Act, Section Five on "
            "inventive step, the Biodiversity Act, the Traditional Knowledge "
            "Digital Library examination guidelines, the Food Safety Standards "
            "regulations, Schedule T of the Drugs and Cosmetics Rules, and the "
            "United States and Canadian natural health frameworks. These are "
            "reviewable code, so the same input always produces the same verdict. "
            "The middle layer is retrieval, grounded in a curated corpus and hybrid "
            "semantic and keyword search. The top layer explains the result in "
            "plain language. If the bottom layer has no answer, the top layer is "
            "told to say so."
        ),
    },
    {
        "id": "08_solution_guard",
        "visual": {"kind": "slide", "template": "solution_guard"},
        "text": (
            "Every finding carries a resolvable identifier, never a plausible "
            "guess. A taxon is a Global Biodiversity Information Facility usage "
            "key. A compound is a PubChem compound identifier with its InChIKey. A "
            "protein is a reviewed UniProt accession. A gene is an N C B I gene "
            "identifier. A statute is its actual section. The guard checks these "
            "identifiers, and an ungrounded statement is suppressed instead of "
            "being shown."
        ),
    },
    {
        "id": "09_solution_agents",
        "visual": {"kind": "slide", "template": "solution_agents"},
        "text": (
            "On top of that sit thirty nine specialist agents, each doing one real "
            "task rather than pretending to do everything. There are agents for "
            "novelty search, freedom to operate, prior art mapping, patent "
            "drafting, office action responses, essentiality claim charts, life "
            "cycle assessment for small molecules and biologics, structure and "
            "activity relationship extraction, formulation review, markush "
            "drafting, regulatory mapping, labelling checks, and white space "
            "analysis. Each returns cited findings, not prose."
        ),
    },
    # ------------------------------------------------------------ live demo
    {
        "id": "10_demo_home",
        "visual": {"kind": "page", "route": "/"},
        "text": (
            "This is the live product. The landing page is a research portal, and "
            "it is deliberately clear that this is an independent research project "
            "and not a Government of India website."
        ),
    },
    {
        "id": "11_demo_home_zoom",
        "visual": {
            "kind": "zoom",
            "route": "/",
            "selector": "#services",
            "label": "Services and platform modules",
        },
        "text": (
            "The services block is the whole surface area in one view: the patent "
            "and prior art modules, the regulatory base, evidence and compliance, "
            "and the market modules. Every one of them is backed by a curated corpus "
            "rather than a prompt."
        ),
    },
    {
        "id": "12_demo_lab",
        "visual": {"kind": "page", "route": "/innovation-lab"},
        "text": (
            "The Innovation Lab is the working surface. Agents are grouped by domain "
            "rather than listed alphabetically, so a formulation scientist and a "
            "patent examiner each see the tools that are relevant to them."
        ),
    },
    {
        "id": "13_demo_lab_zoom",
        "visual": {
            "kind": "zoom",
            "route": "/innovation-lab",
            "selector": "main",
            "label": "Agent library",
        },
        "text": (
            "Thirty nine agents are registered across engineering, intellectual "
            "property, life sciences and materials, and each one is a real workflow "
            "with its own inputs and its own decision, not a chat prompt."
        ),
    },
    {
        "id": "14_demo_agent",
        "visual": {"kind": "page", "route": "/innovation-lab/agents/novelty_search"},
        "text": (
            "Opening a single agent shows the inputs it needs and the workflow it "
            "will run. This is the novelty search agent."
        ),
    },
    {
        "id": "15_demo_agent_zoom",
        "visual": {
            "kind": "zoom",
            "route": "/innovation-lab/agents/novelty_search",
            "selector": "main",
            "label": "Novelty analysis",
        },
        "text": (
            "The result is always structured. Section Three exposure, inventive "
            "step, evidence strength, and a list of citations that can be opened and "
            "checked. Every field traces back to either a statute or a retrievable "
            "document, and if the evidence is not there, the field says so."
        ),
    },
    {
        "id": "16_demo_dashboard",
        "visual": {"kind": "page", "route": "/dashboard"},
        "text": (
            "Passports tie the work together. One passport is the subject, and every "
            "agent, analysis and document attaches to it, so the assessment is "
            "reproducible later instead of living in somebody's inbox."
        ),
    },
    {
        "id": "17_demo_dashboard_zoom",
        "visual": {
            "kind": "zoom",
            "route": "/dashboard",
            "selector": "main",
            "label": "Passport workspace",
        },
        "text": (
            "From the same passport you can reach the regulatory roadmap, the "
            "freedom to operate map, the claim firewall, and the disclosure "
            "sentinel. One subject, one evidence base, every module."
        ),
    },
    # -------------------------------------------------------------- closing
    {
        "id": "19_closing",
        "visual": {"kind": "slide", "template": "closing"},
        "text": (
            "The point is not that a model can talk about Ayurveda. The point is "
            "that when it does, every sentence can be checked. Deterministic rules "
            "for the law, grounded retrieval for the facts, verifiable identifiers "
            "for every citation, and a system that says I do not know when it "
            "genuinely does not know. Thank you."
        ),
    },
]

# Scene types that capture the live application rather than a rendered slide.
LIVE_SCENES = [s for s in SCENES if s["visual"]["kind"] in ("page", "zoom")]
SLIDE_SCENES = [s for s in SCENES if s["visual"]["kind"] == "slide"]
