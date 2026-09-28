"""Slide templates for the Vedalex demo deck.

Rendered as HTML at 1920x1080 and captured with Playwright, so the typography and
layout are the browser's, not a drawing library's.
"""

from __future__ import annotations

W, H = 1920, 1080

BASE_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:1920px; height:1080px; overflow:hidden; }
body {
  font-family: "Segoe UI", Inter, system-ui, -apple-system, sans-serif;
  background:
    radial-gradient(1200px 700px at 78% -10%, #12325c 0%, transparent 60%),
    linear-gradient(160deg, #071324 0%, #0a1c33 55%, #0d2742 100%);
  color:#e8eef7;
  -webkit-font-smoothing:antialiased;
}
.wrap { width:1920px; height:1080px; padding:96px 120px; display:flex; flex-direction:column; }
.eyebrow { font-size:22px; letter-spacing:.24em; text-transform:uppercase; color:#7fb0e8; font-weight:600; }
h1 { font-size:82px; line-height:1.08; font-weight:700; letter-spacing:-.02em; margin-top:22px; }
h2 { font-size:60px; line-height:1.14; font-weight:700; letter-spacing:-.015em; margin-top:20px; }
p.lede { font-size:33px; line-height:1.5; color:#b9cbe2; margin-top:28px; max-width:1500px; }
.rule { width:150px; height:5px; background:linear-gradient(90deg,#3b82f6,#22d3ee); border-radius:3px; margin-top:34px; }
.foot { position:absolute; left:120px; bottom:64px; font-size:20px; color:#61789a; letter-spacing:.06em; }
.pagenum { position:absolute; right:120px; bottom:64px; font-size:20px; color:#61789a; font-variant-numeric:tabular-nums; }
.grid { display:grid; gap:26px; margin-top:52px; }
.card { background:linear-gradient(180deg, rgba(255,255,255,.075), rgba(255,255,255,.028));
  border:1px solid rgba(120,170,225,.24); border-radius:18px; padding:32px 34px; }
.card h3 { font-size:30px; font-weight:650; margin-bottom:12px; color:#eaf2fb; }
.card p { font-size:23px; line-height:1.48; color:#a8bfd8; }
.bad { border-color:rgba(244,113,113,.36); }
.bad h3 { color:#fca5a5; }
.good { border-color:rgba(52,211,153,.38); }
.good h3 { color:#6ee7b7; }
.warn { border-color:rgba(251,191,36,.4); }
.warn h3 { color:#fcd34d; }
.stack { display:flex; flex-direction:column; gap:20px; margin-top:44px; }
.layer { display:flex; align-items:center; gap:28px; padding:26px 32px; border-radius:16px;
  border:1px solid rgba(120,170,225,.22); background:rgba(255,255,255,.04); }
.layer .tag { flex:0 0 210px; font-size:21px; letter-spacing:.14em; text-transform:uppercase;
  color:#7fb0e8; font-weight:700; }
.layer .body { font-size:25px; line-height:1.45; color:#cfdcec; }
.arrowdown { text-align:center; font-size:30px; color:#4b7fb0; margin:-8px 0 -8px 100px; }
.pillrow { display:flex; flex-wrap:wrap; gap:12px; margin-top:34px; }
.pill { font-size:21px; padding:11px 20px; border-radius:999px; border:1px solid rgba(120,170,225,.3);
  background:rgba(59,130,246,.12); color:#cfe2f7; }
code, .mono { font-family: "Cascadia Mono", Consolas, monospace; }
.kbd { font-family:"Cascadia Mono",Consolas,monospace; font-size:23px; color:#7dd3fc;
  background:rgba(125,211,252,.1); padding:3px 10px; border-radius:6px; }
"""


def _shell(body: str, *, eyebrow: str, page: int, total: int) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>{BASE_CSS}</style></head><body>
<div class="wrap">
  <div class="eyebrow">{eyebrow}</div>
  {body}
</div>
<div class="foot">VEDALEX &middot; Traditional Knowledge IP &amp; Compliance</div>
<div class="pagenum">{page} / {total}</div>
</body></html>"""


def render(template: str, page: int, total: int) -> str:
    t = template

    if t == "title":
        body = f"""
        <h1 style="font-size:104px;max-width:1560px">Vedalex</h1>
        <div class="rule"></div>
        <p class="lede" style="font-size:37px;max-width:1420px;margin-top:34px">
          A research and compliance workspace for Indian traditional knowledge.
          Deterministic statutory rules, grounded retrieval, and a verifiable
          citation for every claim.</p>
        <div class="pillrow" style="margin-top:56px">
          <span class="pill">39 specialist agents</span>
          <span class="pill">Deterministic rule engine</span>
          <span class="pill">Hybrid RAG retrieval</span>
          <span class="pill">Zero-hallucination guard</span>
        </div>"""
        return _shell(body, eyebrow="Smart India Hackathon &middot; Problem statement and product walkthrough", page=page, total=total)

    if t == "problem_headline":
        body = """
        <h2>The knowledge is real.<br>The paper trail is not.</h2>
        <div class="rule"></div>
        <p class="lede">A formulation scientist can tell you it works. What they
        cannot usually tell you is whether it is novel, whether it is patentable,
        or whether somebody already owns it.</p>"""
        return _shell(body, eyebrow="The problem", page=page, total=total)

    if t == "problem_diagram":
        body = """
        <h2 style="font-size:52px">Four failures, at the same time</h2>
        <div class="grid" style="grid-template-columns:1fr 1fr;width:1620px">
          <div class="card bad"><h3>1 &middot; Oral knowledge</h3>
            <p>Traditional knowledge is transmitted, not written down. Undocumented
            knowledge cannot be searched, and is treated as publicly available in law.</p></div>
          <div class="card bad"><h3>2 &middot; Paywalled prior art</h3>
            <p>Commercial prior art sits inside subscription patent databases that
            a formulation team rarely has access to or time for.</p></div>
          <div class="card bad"><h3>3 &middot; Scattered legal tests</h3>
            <p>Patents Act, Biodiversity Act, TKDL guidelines, FSSAI, Schedule T,
            plus US and Canadian regimes. Each test lives in a different instrument.</p></div>
          <div class="card bad"><h3>4 &middot; Manual search fails</h3>
            <p>Human search is slow, costly and quietly incomplete, because nobody
            reads every relevant document before filing.</p></div>
        </div>
        <div class="arrowdown" style="margin-top:34px">&#9660;</div>
        <h3 style="font-size:31px;color:#fca5a5;margin-top:8px">Result: good work gets
        blocked &mdash; or gets patented by somebody else first.</h3>"""
        return _shell(body, eyebrow="The problem", page=page, total=total)

    if t == "problem_tkdl":
        body = """
        <h2 style="font-size:52px">This has already cost India</h2>
        <div class="grid" style="grid-template-columns:1fr 1fr;width:1620px">
          <div class="card warn"><h3>Defensive publications cited abroad</h3>
            <p>India's Traditional Knowledge Digital Library publishes prior art to
            defeat bad patents. Those publications have been cited against Indian
            companies in overseas patent offices.</p></div>
          <div class="card warn"><h3>Section 3, Patents Act 1970</h3>
            <p>No patent may be granted on matter in the public domain, including
            plant matter, unless disclosed to the public. Miss this and the filing,
            the cost and the priority date are all lost.</p></div>
        </div>
        <p class="lede" style="margin-top:40px;font-size:29px">The failure is not legal.
        It is informational &mdash; the answer exists, but not in one place, and not
        in a form a team can act on before the deadline.</p>"""
        return _shell(body, eyebrow="Why this matters", page=page, total=total)

    if t == "problem_llm":
        body = """
        <h2 style="font-size:52px">The obvious fix is the dangerous one</h2>
        <div class="grid" style="grid-template-columns:1fr 1fr 1fr;width:1680px">
          <div class="card bad"><h3>Invented citations</h3>
            <p>Confident references to papers that do not exist.</p></div>
          <div class="card bad"><h3>Misquoted statute</h3>
            <p>A real section quoted as if it said something it does not.</p></div>
          <div class="card bad"><h3>Fake identifiers</h3>
            <p>A patent number, C I D or gene id that resolves to nothing.</p></div>
        </div>
        <div class="card" style="margin-top:44px;border-color:rgba(244,113,113,.5)">
          <h3 style="color:#fca5a5">In a compliance context, a fluent wrong answer is
          more expensive than no answer at all.</h3>
          <p style="font-size:25px">A wrong novelty opinion filed with an authority
          can cost a patent. A wrong ingredient list can cost a product.</p>
        </div>"""
        return _shell(body, eyebrow="Why a general LLM is not the answer", page=page, total=total)

    if t == "solution_headline":
        body = """
        <h2 style="max-width:1500px">Never assert what you cannot trace to a source.</h2>
        <div class="rule"></div>
        <p class="lede">Three layers. The language model is only the top one, and it
        is not permitted to reach a conclusion on its own.</p>"""
        return _shell(body, eyebrow="The solution", page=page, total=total)

    if t == "solution_diagram":
        body = """
        <h2 style="font-size:50px;margin-bottom:6px">Deterministic core, generative surface</h2>
        <div class="stack" style="width:1660px">
          <div class="layer"><div class="tag">Layer 3 &middot; Explain</div>
            <div class="body"><b>Language model.</b> Renders the finding in plain
            language. Cannot introduce a fact. Suppressed when nothing is grounded.</div></div>
          <div class="arrowdown">&#9660;</div>
          <div class="layer"><div class="tag">Layer 2 &middot; Retrieve</div>
            <div class="body"><b>Hybrid RAG.</b> Hybrid semantic and keyword search over
            a curated corpus of statutes, guidance, pharmacopoeia text and official
            datasets.</div></div>
          <div class="arrowdown">&#9660;</div>
          <div class="layer" style="border-color:rgba(52,211,153,.4)">
            <div class="tag">Layer 1 &middot; Decide</div>
            <div class="body"><b>Deterministic rule engine.</b> Reviewable rule packs:
            Patents Act s.3 and s.5, Biodiversity Act 2002, TKDL examination
            guidelines, FSSAI aahara regulations, Schedule T, US DSHEA, Canada NHPR.
            Same input, same verdict, every time.</div></div>
        </div>"""
        return _shell(body, eyebrow="The solution &middot; architecture", page=page, total=total)

    if t == "solution_guard":
        body = """
        <h2 style="font-size:50px">Every finding carries a resolvable identifier</h2>
        <div class="grid" style="grid-template-columns:1fr 1fr;width:1640px">
          <div class="card good"><h3>Plant taxonomy</h3>
            <p class="mono" style="color:#7dd3fc">GBIF usage key</p>
            <p>Accepted name, family, taxonomic status and synonyms from the GBIF
            backbone.</p></div>
          <div class="card good"><h3>Compounds</h3>
            <p class="mono" style="color:#7dd3fc">PubChem CID + InChIKey</p>
            <p>Formula, weight, SMILES and preferred IUPAC name for every marker.</p></div>
          <div class="card good"><h3>Proteins</h3>
            <p class="mono" style="color:#7dd3fc">UniProtKB accession</p>
            <p>Reviewed Swiss-Prot entries with the official function annotation.</p></div>
          <div class="card good"><h3>Genes</h3>
            <p class="mono" style="color:#7dd3fc">NCBI Gene ID</p>
            <p>Official symbol, description, summary and map location.</p></div>
        </div>
        <p class="lede" style="font-size:28px;margin-top:40px">If an identifier cannot be
        resolved, the statement is not displayed. &ldquo;I do not know&rdquo; is a valid
        output.</p>"""
        return _shell(body, eyebrow="The zero-hallucination guard", page=page, total=total)

    if t == "solution_agents":
        body = """
        <h2 style="font-size:50px">Thirty nine specialists, one task each</h2>
        <p class="lede" style="font-size:27px;margin-top:16px">Each returns cited
        findings, not prose.</p>
        <div class="pillrow" style="width:1680px;margin-top:30px">
          <span class="pill">novelty_search</span>
          <span class="pill">fto_search</span>
          <span class="pill">prior_art_mapping</span>
          <span class="pill">patent_drafting</span>
          <span class="pill">office_action_response</span>
          <span class="pill">inventive_step</span>
          <span class="pill">essentiality_claim_chart</span>
          <span class="pill">invention_disclosure</span>
          <span class="pill">markush_drafting</span>
          <span class="pill">lca_small_molecule</span>
          <span class="pill">lca_biotherapeutic</span>
          <span class="pill">sar_data_extraction</span>
          <span class="pill">formulation</span>
          <span class="pill">labeling_check</span>
          <span class="pill">regulatory_map</span>
          <span class="pill">approval_gate</span>
          <span class="pill">claim_scope</span>
          <span class="pill">white_space</span>
          <span class="pill">evidence_quality</span>
          <span class="pill">proof_auditor</span>
          <span class="pill">risk_guard</span>
          <span class="pill">export_pathfinder</span>
          <span class="pill">compliance_officer</span>
        </div>
        <div class="card good" style="margin-top:44px;width:1680px">
          <h3>Deterministic by construction</h3>
          <p style="font-size:25px">The language model explains the outcome. It does
          not decide it. That is why the same passport produces the same verdict on
          every run and every machine.</p>
        </div>"""
        return _shell(body, eyebrow="The solution &middot; agent layer", page=page, total=total)

    if t == "closing":
        body = f"""
        <h2 style="font-size:66px;max-width:1560px">It is not that a model can talk
        about Ayurveda.</h2>
        <div class="rule"></div>
        <p class="lede" style="font-size:33px;max-width:1500px">It is that when it
        does, every sentence can be checked.</p>
        <div class="grid" style="grid-template-columns:1fr 1fr 1fr 1fr;width:1680px">
          <div class="card good"><h3>Rules for the law</h3><p>Reviewable, versioned,
            deterministic statutory tests.</p></div>
          <div class="card good"><h3>Retrieval for the facts</h3><p>Grounded in a
            curated corpus and official datasets.</p></div>
          <div class="card good"><h3>Identifiers for the citations</h3><p>Resolvable,
            never plausible.</p></div>
          <div class="card good"><h3>Honesty when it is unknown</h3><p>Silence is a
            valid, expected result.</p></div>
        </div>
        <p class="lede" style="margin-top:48px;font-size:30px">Thank you.</p>"""
        return _shell(body, eyebrow="In summary", page=page, total=total)

    raise ValueError(f"unknown slide template: {template}")
