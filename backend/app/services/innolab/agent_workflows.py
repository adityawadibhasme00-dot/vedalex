"""IP-SAKTI Agent Hub — guided workflows (Eureka-exact Input → Process → Output).

Defines, for every registered Agent-Hub agent:

  * ``steps``    — the internal workflow the agent executes (exposed to the
                   user as a visible, controllable plan à la PatSnap Eureka)
  * ``questions``— the step-by-step intake questions the agent asks the user
                   one at a time before it runs.

Every agent below is calibrated to behave EXACTLY like the corresponding
PatSnap Eureka agent (researched from Eureka product pages, the Eureka blog
guides, the PatSnap Help Center and the PatSnap Open Platform API):

  * Engineering/TRIZ  : Frame → Analyze → Solve (3 phases, checkpointed),
                        contradiction matrix 39x39 / 40 principles.
  * Find Solutions    : task → recommend constraints → confirm → directions
                        → select → final technical-solution mind map.
  * Quick Research    : topic → auto-generated 8-module report outline →
                        confirm outline → generate modules w/ citations.
  * Novelty Search    : disclosure → confirm extracted features (F1..Fn) →
                        5-group hybrid search → feature-by-feature verdicts vs
                        single closest reference → SEPARATED metrics (semantic
                        similarity, feature coverage, search confidence, anticipation
                        risk) — never one combined 'novelty score'.
  * FTO ("Hiro")      : confirm product features → keyword expansion →
                        multi-strategy search → screen (legal status) →
                        element-wise claim charting (independent-first) →
                        High/Medium/Low risk report.
  * Design FTO        : image → patent-standard line drawings (auto views) →
                        image-database search → design-feature comparison →
                        risk + design-around report (similarity score,
                        registration number, legal status, jurisdiction).
  * Patent Drafting   : disclosure + jurisdiction → terms map → embedded
                        prior-art search → confirm essential features →
                        claims tree (ind then dep) → specification → figures →
                        compliance review → Word export.
  * Invention Disc.   : raw idea → generate → refine via 4 interpretation
                        dimensions (subject/application/mechanism/outcome).
  * Office Action      : parse action → rejection analysis table → jurisdiction
                        grounds (§101/102/103/112, Art 52-57/83-84, 26.2/26.3)
                        → ranked strategies → drafted response.
  * Essentiality Chart: claim text + standard/version → chart-type classification →
                        atomic limitations (dependent claims inherit) → version gate →
                        clause obligation classification → AICC rows (feature-match labels) →
                        ETSI essentiality test → evidence tiers → template-only export gate.
  * tDoc Novelty      : TDoc ingest → cleaning (headings/metadata separated) →
                        feature classification (14 categories) → confirm → relevant date →
                        multi-strategy search → reference normalisation → single-reference
                        matrix → separated metrics (no 'novelty score').
  * Document Analyzer : ingest → exec summary → tables/figures/entities →
                        export → table/figure tools → doc Q&A.
  * LCA Biotherapeutic: ingest (200MB+/1000pp) → OCSR → NER → normalize →
                        sequence comparison + epitope → claim scope/legal →
                        developability top-5 patents / 5-10 molecules.
  * LCA Small Molecule: ingest → OCSR → assay NER → Lipinski developability →
                        ranked leads + SMILES export.
  * SAR Extraction    : patent → structure+experiment records → SMILES
                        standardize → human validate (Value/Structure Source,
                        Structure Match) → export (CSV/Excel/SDF).
  * Antibody Predictor: sequence/target → curated R&D + BLAST → affinity
                        cross-check → prediction → ranked shortlist w/ scores.
  * Markush Drafting  : structures (MOL/CDX/SDF) → scaffold/R-groups →
                        coverable-vs-not → editable → file-ready claims.
  * Formulation       : classification gate → objective/constraints → identity/
                        function map → evidence-classified candidates (1 strategy
                        change) → concentration audit → precise process → 4-type
                        stability + ICH Q1A → compatibility/manufacturability →
                        regulatory/claims/IP → risk & weighted decision matrices →
                        controlled bench-testing plan (10 steps).
  * Materials FS      : material-problem intake (10 fields) → classification →
                        root-cause tree → characterization → CMA-CPP-CQA (ICH Q8)
                        → real MS-001/002 candidates → mind map →
                        compatibility/cost/regulatory/IP → risk per category →
                        MAT-EX validation + DOE (10 steps).

These definitions are shared by the step-by-step agent UI, the per-agent
executor (``agent_executors.py``) and the Orchestration Engine
(``orchestrator.py``), so a workflow is always consistent everywhere.
"""

from __future__ import annotations

from typing import Any


def _step(label: str, description: str = "") -> dict[str, str]:
    return {"label": label, "description": description}


def _q(
    key: str,
    label: str,
    question: str,
    *,
    kind: str = "text",
    required: bool = False,
    options: list[str] | None = None,
    placeholder: str = "",
    help_text: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "question": question,
        "kind": kind,
        "required": required,
        "options": options or [],
        "placeholder": placeholder,
        "help": help_text,
    }


AGENT_WORKFLOWS: dict[str, dict[str, Any]] = {
    # ---------------------------------------------------------------------- #
    # Engineering  (3)  — Eureka R&D agents
    # ---------------------------------------------------------------------- #
    "triz": {
        "steps": [
            _step("Frame the problem & system boundary", "Review your input, summarise the agent's understanding, and name the system being improved."),
            _step("Build root-cause hypotheses", "Generate falsifiable RCA hypotheses (thermal, oxidative, physical, mass-transfer, configuration) with a confirm test each."),
            _step("Isolate the technical contradiction", "State exactly which parameter you push and which one degrades in return."),
            _step("Map to the 39 TRIZ parameters", "Translate both sides of the contradiction onto the Altshuller 39-parameter scale."),
            _step("Look up the contradiction matrix cell", "Retrieve the inventive principles from the exact 39×39 matrix cell (canonical Altshuller data)."),
            _step("Convert principles into IP-SAKTI solutions", "Turn each principle into a domain-specific solution WITH a validation experiment — principles are directions, not answers."),
            _step("Rank, validate & recommend", "Rank principles (matrix frequency vs domain fit kept separate), define success metrics and evidence rules, give one final recommendation."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Technical problem", "What technical problem or performance target do you want to solve?", kind="textarea", required=True,
               placeholder="e.g. Increase extraction yield of the hydroalcoholic extract without degrading heat-sensitive ashwagandha markers"),
            _q("improve_aspect", "Parameter to improve", "Which parameter do you want to improve? (optional — we derive it if blank)", kind="text",
               required=False, placeholder="e.g. extraction yield, throughput, stability"),
            _q("tradeoff", "What worsens as you improve", "What degrades when you push that parameter? (optional — we derive it if blank)", kind="text",
               required=False, placeholder="e.g. potency retention, energy use, colour"),
        ],
    },
    "quick_research": {
        "steps": [
            _step("Parse the research topic", "Identify the core topic, provisional product classification and research scope."),
            _step("Generate the report outline", "Auto-build the 8-module evidence-backed report structure, then confirm & refine it with you."),
            _step("Module 1: technical background & objectives", "Describe the technology, background, research aims and provisional classification."),
            _step("Module 2: market & demand analysis", "Assess market definition, customer segments, demand indicators and evidence status — demand is never inferred from source count."),
            _step("Module 3: regulatory & compliance landscape", "Cover per-jurisdiction classification, authorities, rules and implications."),
            _step("Module 4: technology status & challenges", "Cover the status quo, maturity labels and current technical challenges."),
            _step("Module 5: technology evolution path", "Trace historical → current → emerging direction with trend caveats."),
            _step("Module 6: stakeholder & player analysis", "Separate regulators, research institutions and commercial players."),
            _step("Module 7: technical-scheme review", "Compare existing technical approaches, advantages, limitations and trade-offs."),
            _step("Module 8: patent & prior-art landscape", "Screen references with claim-level interpretation and explicit legal disclaimers."),
            _step("Innovation opportunities & research gaps", "Generate specific ideas and classify research gaps by type and priority."),
            _step("Cite every claim & assemble the report", "Annotate each module with source-traceable citations and assemble the exportable report."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Research topic", "What topic or technology area do you want researched?", kind="textarea", required=True,
               placeholder="e.g. Adaptogens for cognitive health: Ashwagandha vs Brahmi evidence base"),
            _q("target_markets", "Target markets", "Which jurisdictions should the regulatory and market analysis cover?", kind="multi", required=False,
               placeholder="India, United States, Canada"),
            _q("timeframe", "Time horizon", "What time horizon should the evolution-path analysis use?", kind="text", required=False,
               placeholder="5y / 10y / latest / all"),
        ],
    },
    "find_solutions": {
        "steps": [
            _step("Create the task", "Parse the technical problem into a structured task with baseline and system boundary."),
            _step("Build the failure-mode hypothesis tree", "Separate the observed symptom from possible root causes with a confirm test each."),
            _step("Recommend constraints to confirm", "Generate the constraints/conditions (cost, safety, compatibility) the solving must respect."),
            _step("Generate solution directions", "Confirm the constraints, then generate candidate solutions across intervention classes."),
            _step("Evaluate & rank the solutions", "Score across technical impact, root-cause relevance, cost, line compatibility, safety, regulatory simplicity, scale-up, validation speed and IP potential."),
            _step("Design the validation experiments", "Define control vs treatment, variables changed vs fixed, metrics and success criteria."),
            _step("Deliver the technical-solution mind map", "Present the ranked solution set with its core contradiction, cost/IP/regulatory notes and cited evidence."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Technical problem", "Describe the technical challenge you want solved.", kind="textarea", required=True,
               placeholder="e.g. Product clumps and settles during storage"),
            _q("process_desc", "Process / current practice", "Describe the current process (optional).", kind="text", required=False,
               placeholder="e.g. hydroalcoholic extraction, then concentration, filling and sealing"),
            _q("improve_aspect", "Success target", "What measurable outcome should the solution deliver? (optional)", kind="text", required=False,
               placeholder="e.g. extend shelf life to 12 months"),
            _q("constraint", "Constraints", "Any constraints to respect (cost ceiling, safety, existing line)? (optional)", kind="text", required=False,
               placeholder="e.g. cost increase ≤15%, no new allergens on label"),
        ],
    },
    # ---------------------------------------------------------------------- #
    # IP  (8)  — Eureka patent agents
    # ---------------------------------------------------------------------- #
    "novelty_search": {
        "steps": [
            _step("Submit the invention description", "Register your description (200–500 words) and target jurisdictions."),
            _step("Extract core technical features (atomic)", "Split the invention into atomic claim-comparable features (F1…Fn); confirm, edit or remove them and mark the ESSENTIAL set before searching."),
            _step("Run the multi-strategy prior-art search", "Semantic + keyword/synonym + feature-combination + parameter/range + classification + family/citation + non-patent strategies, examiner-style reasoning over domain data."),
            _step("Compare prior art to each feature", "Seven-level disclosure taxonomy per feature×reference; build the single-reference novelty matrix (one reference must disclose every essential feature to anticipate — references are never combined for lack of novelty)."),
            _step("Generate the structured comparison report", "Separated metrics: semantic similarity (not novelty), essential-feature coverage, missing/underdefined features, combination disclosure, preliminary anticipation risk, search confidence — plus separate inventive-step and FTO notes."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Invention", "Describe the invention in 200–500 words (problem, solution, advantages).", kind="textarea", required=True,
               placeholder="e.g. A hydroalcoholic Ashwagandha–Brahmi extract delivering ≥3% withanolides with 36-month stability, for restful sleep"),
        ],
    },
    "fto_search": {
        "steps": [
            _step("Describe your technical solution", "Decompose the product into claim-relevant elements (composition, solvent, excipients, device, process, use); choose the target authorities/markets."),
            _step("Confirm extracted technical features", "Review the decomposition — every element is labelled Confirmed / Missing; missing elements must be supplied before a final FTO conclusion."),
            _step("Launch the FTO search", "Click 'Confirm features & start search' — semantic + classification + keyword rounds across each target market and each commercial activity (manufacture/use/sale/offer for sale/import/export)."),
            _step("Screening & search-strategy trace", "Screen candidates by source category: patents → include for claim review (status uncertain); regulations/monographs/technical papers → background only (not patent rights)."),
            _step("Chart the active claims element-wise", "Map every claim element vs product evidence (Identified / Not identified / Uncertain + rationale + reviewer question) — mapping is driven by confirmed product data."),
            _step("Create the FTO report", "Risk classification with basis and movers — capped at Medium until legal status is verified on official national registers; regulatory context is reported separately from patent risk."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Technical solution", "Describe the product you plan to make, use or commercialise.", kind="textarea", required=True,
               placeholder="e.g. Hydroalcoholic Ashwagandha–Brahmi liquid supplement, 500 mg dose, amber dropper bottle"),
        ],
    },
    "design_fto": {
        "steps": [
            _step("Identify the design article & separate visual from functional features", "State the article (bottle/container/cap/label/packaging) and the commercial activities per target market; functional features (pump, dosing, tamper, grip geometry) are set aside from the start."),
            _step("Extract atomic visual features (V1…Vn) and confirm", "Split the design into atomic visual units — silhouette, configuration, surface treatment, ornamentation, colour, marks/labels — each classified Functional / Ornamental / Mixed; confirm, edit and mark each feature as essential/functional/optional."),
            _step("Search the official design registers per jurisdiction", "Image-to-register and classification search on official design-register routes only (IP India Design Search + e-register, USPTO design patents, Canadian industrial-design register, Hague where applicable); registration numbers, views and dates are recorded."),
            _step("Screen candidates & verify registration / legal status", "Screen by record type: utility patents, regulations and technical papers are background/excluded — not design-right evidence; legal status is verified with a date (registered & active / pending / expired / lapsed / refused / not found)."),
            _step("Compare the overall visual impression & report separated IP risks", "Compare the proposed design dimension-by-dimension with verified representations against the design-right standard; design, trademark/trade-dress, copyright, passing-off and utility-patent risks are reported in separate lines."),
            _step("Provide function-preserving design-arounds", "Suggest appearance changes that preserve the required product function, each re-validated by re-comparing the overall visual impression."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Design", "Describe the visual design of your product.", kind="textarea", required=True,
               placeholder="e.g. Amber glass dropper bottle, hexagonal cap, leaf-marked label"),
        ],
    },
    "patent_drafting": {
        "steps": [
            _step("Ingest the invention description", "Ingest the disclosure — notes, sketches, screenshots, prototype or pasted text."),
            _step("Extract technical elements & build the terms map", "Analyse the disclosure and build the editable terms map with broader/narrower expansions."),
            _step("Detect corrupted / vague / undefined terms (drafting gate)", "Block drafting on 'cognitive support' or similar benefits used as components, corrupted text (e.g. 'wellnessHowever'), undefined 'effective amounts', unsupported 'synergistic' proportions, vague 'controlled conditions', unnamed 'solvent', and 'supporting stress' — these require inventor confirmation before any claim is drafted."),
            _step("Split ingredients from benefits & confirm essential features", "Separate actual ingredients from benefit/effect terms; ask the inventor to confirm each ingredient, and agree the essential technical features and claim architecture."),
            _step("Run the embedded prior-art / TK review", "Check family documents, citations, legal events and traditional-knowledge context inside the workflow."),
            _step("Draft claim versions (A broad / B supported / C fallback)", "Draft independent claims (product/method/use) then dependents, layered from the confirmed features only; every missing datum appears as an explicit [TO BE CONFIRMED] marker — never silently filled."),
            _step("Draft the specification", "Build title, technical field, background, summary, detailed description and examples from supported content only."),
            _step("Generate figures only where technically meaningful", "Plan figures with automatic reference numerals only when a concrete dosage form/device structure or an explicit process flow exists."),
            _step("Run the compliance review (blocking)", "Mandatory dual-track review — deterministic (numbering, dependencies, coverage, abstract limits) + semantic (antecedent basis, placeholders, undefined quantities, synergy, benefit-as-component, vague process); the draft is NOT filing-ready while any fail remains."),
            _step("Export the preliminary draft / clarification checklist", "Export the preliminary drafting package with jurisdiction notes and the inventor-confirmation checklist for attorney review."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Invention description", "Describe the invention you want to protect (technical background + technical means + new effects).", kind="textarea", required=True,
               placeholder="e.g. A stable hydroalcoholic Ashwagandha–Brahmi composition with 36-month stability"),
        ],
    },
    "invention_disclosure": {
        "steps": [
            _step("Capture raw notes & inventors", "Record the raw lab-book notes and full inventor / ownership details — nothing is invented."),
            _step("Build the source-of-truth record", "Split confirmed vs unconfirmed items; every missing datum becomes an explicit [TO BE CONFIRMED] / [NOT PROVIDED] / [EXPERIMENTAL DATA REQUIRED] marker."),
            _step("Map problem → means → mechanism → effect", "Derive the technical problem, objectives, core solution, mechanism, embodiments and best mode (Sec. 10 note) with an essential-feature matrix."),
            _step("Run knowledge & disclosure reviews", "Traditional-knowledge / biological-material review, evidence table and public-disclosure & confidentiality timeline."),
            _step("Gate the handoff", "Patent-drafting handoff stays BLOCKED until inventor confirmation and experimental evidence are attached; then sign the record."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Raw idea / lab notes", "Paste your raw notes or lab-book text (background + what you did).", kind="textarea", required=True,
               placeholder="e.g. Mixed 3 parts ashwagandha root with 1 part brahmi, 40% alcohol, 70°C..."),
            _q("inventors", "Inventor(s)", "Full names of all inventors (optional here; required to confirm the record).", kind="text",
               placeholder="e.g. Dr Aditi Sharma, Prof. R. Verma"),
        ],
    },
    "office_action_response": {
        "steps": [
            _step("Triage the office action", "Label the action (formal vs substantive; full action or partial text); if incomplete, flag PRELIMINARY REJECTION TRIAGE."),
            _step("Segment & classify every objection", "Individual O-001… segments with the exact examiner wording, ground classification, claims, statutory basis and jurisdiction."),
            _step("Verify references & map claim elements", "Separate patent vs non-patent citations with dates/status, then map each claim element to its disclosure basis."),
            _step("Audit novelty & inventive step separately", "Single-reference novelty test and a separate obviousness analysis; never conflate the grounds (India Sec. 59 / no new matter)."),
            _step("Rank strategies & draft, or stay blocked", "Objection-specific amendment options with original-basis support and new-matter risk; formal drafting only when the full action, claims and specification are available."),
        ],
        "auto_run": True,
        "questions": [
            _q("office_action_text", "Office action", "Paste the office action / rejection text.", kind="textarea", required=True,
               placeholder="e.g. Claims 1-10 rejected under 35 U.S.C. § 103 as obvious over ..."),
            _q("proposed_claims", "Claim text (optional)", "Current claim text if available — enables claim-element mapping and amendment support.", kind="textarea",
               placeholder="e.g. 1. A composition comprising Bacopa monnieri extract and a hydroalcoholic solvent..."),
        ],
    },
    "essentiality_claim_chart": {
        "steps": [
            _step("Classify the chart type", "Determine whether the chart is standard-essentiality, patent-to-product, patent-to-prior-art, licensing/pool or litigation — never assumed."),
            _step("Extract claims & atomic limitations", "Split each claim into atomic limitations; dependent claims inherit every limitation of the parent claim. Record a preliminary claim-construction note."),
            _step("Identify the standard & open the version gate", "Confirm the standard body, number, version/release and effective date; classify retrieved clauses (mandatory / conditional / optional / recommended / informative / example / deprecated / profile-specific / implementation-dependent / unclear)."),
            _step("Map limits clause-by-clause (AICC rows)", "Match each limitation to its standard clause with evidence-based feature-match labels (direct / partial / optional / not-found / unclear) — regulatory & patent-office sources never act as clause evidence."),
            _step("Essentiality test, evidence tiers & export gate", "Apply the ETSI-style essentiality questions, tier the sources (Tier 1–5), manage chart/standard versions, and hold export at 'template only' until claims, standard, version and evidence are complete."),
        ],
        "auto_run": True,
        "questions": [
            _q("proposed_claims", "Claim text", "Paste the claims to chart (independent and dependent).", kind="textarea", required=True,
               placeholder="e.g. 1. A composition comprising Ashwagandha root extract and Brahmi extract..."),
            _q("standard_name", "Standard", "Standard body, name and number (e.g. ETSI TS 138 300 V16.x, ISO 8601:2019).", required=True,
               placeholder="e.g. ETSI TS 138 300 V16.0.0"),
            _q("standard_version", "Standard version & date", "Version/release and effective date required for the version gate.", placeholder="e.g. V16.0.0, effective 2019-07"),
            _q("chart_intent", "Chart purpose", "Standard-essentiality, patent-to-product, patent-to-prior-art, licensing/pool or litigation.", kind="select",
               options=["standard-essentiality", "patent-to-product", "patent-to-prior-art", "licensing", "litigation"]),
            _q("patent_number", "Patent number (optional)", "Patent/application number for the subject patent.", placeholder="e.g. US10,123,456"),
            _q("product_desc", "Product description (optional)", "For patent-to-product charts: describe the implemented product so claims map to components.", kind="textarea",
               placeholder="e.g. Tablets of 500 mg Ashwagandha + 300 mg Brahmi hydroalcoholic extract..."),
            _q("product_versions", "Product versions (optional)", "Comma-separated hw/sw/fw versions the chart is claimed against.", placeholder="e.g. v1.0, v1.2"),
        ],
    },
    "tdoc_novelty_search": {
        "steps": [
            _step("Ingest & clean the TDoc", "Separate headings, metadata and administrative labels (project title, manufacturer/regulatory documentation, quality checkpoints) from technical content; detect corrupted text."),
            _step("Extract & classify technical features", "Split the disclosure into atomic, claim-comparable features across 14 categories with essentiality and measurability, then confirm them with the inventor."),
            _step("Fix the relevant date & prior-art cutoff", "Confirm the priority/filing date; only pre-cutoff documents can be cited for anticipation."),
            _step("Run the multi-strategy prior-art search", "Semantic, keyword, feature-combination, parameter/range, classification, family & citation, NPL, plus TDoc-specific re-read and contribution-number searches."),
            _step("Normalise references & assess novelty", "References become real documents with publication numbers; build the feature×reference disclosure, single-reference novelty matrix and SEPARATED metrics (semantic similarity, feature coverage, search confidence, anticipation risk), with regulatory/TK/admin context held out of the closest-art contest."),
        ],
        "auto_run": True,
        "questions": [
            _q("disclosure_text", "TDoc / disclosure", "Paste the technical disclosure or TDoc text.", kind="textarea", required=True,
               placeholder="e.g. Project Title ... We disclose a two-stage hydroalcoholic extraction achieving >90% withanolide recovery..."),
            _q("relevant_date", "Relevant date", "Priority or filing date — sets the prior-art cutoff.", placeholder="e.g. 2024-03-15"),
            _q("prior_art_cutoff", "Prior-art cutoff (optional)", "Earliest applicable prior-art date if different from the relevant date.", placeholder="e.g. 2024-01-30"),
        ],
    },
    # ---------------------------------------------------------------------- #
    # Life Sciences  (6)  — Eureka LS (Synapse/Lead Compound) agents
    # ---------------------------------------------------------------------- #
    "document_analyzer": {
        "steps": [
            _step("Ingest the document", "Accept the text layer; strip OCR artefacts (e.g. \"# OCR Output (Demo)\"), headers, footers, page numbers and watermark labels before anything else."),
            _step("Capture intake & metadata", "Record title, type, version, date, publisher, pages and provenance — the title is NEVER taken from an OCR artefact."),
            _step("Grade OCR quality", "Issue a deterministic High / Medium / Low / Unusable band and flag mis-encoded characters; per-page confidence appears once the scanned PDF is attached; flag that original-image verification is required for filing-grade use."),
            _step("Build the section hierarchy", "Detect numbered/headings/chapters and produce a parent-child tree; admin lines are excluded."),
            _step("Categorise entities", "Organisations, people, products, processes, regulatory instruments, measurements, documents — generic nouns (batch, cleaning, control, documentation) are NOT biomedical entities."),
            _step("Extract numeric measures", "Record value, unit, normalised unit, comparator, context, page and confidence; distinguish 'no numbers present' from 'OCR may have missed numbers in tables/superscripts'."),
            _step("Inventory tables & figures", "Emit T-001 / FIG-001 records with independent addresses; never read a figure whose image was lost in OCR."),
            _step("Extract obligations", "Classify shall/must (mandatory), should (recommended), may (permission) and prohibitions; never upgrade 'should' to 'must'."),
            _step("Definitions & cross-references", "Pull definition-style passages and resolve/broken flag internal cross-references."),
            _step("Separate evidence layers", "Uploaded document (primary) vs OCR-derived vs external sources vs model inference vs user context — external references stay external."),
            _step("Compliance matrix & export", "Never mark 'compliant' from the document alone — issue NOT ASSESSED / REQUIRES EVIDENCE and withhold until human review flags are released."),
        ],
        "auto_run": True,
        "questions": [
            _q("document_text", "Document text", "Paste the document text (or OCR output).", kind="textarea", required=True,
               placeholder="e.g. From the Certificate of Analysis: Ashwagandha root extract ... Withanolides 5.2% ...",
               help_text="The supplied text is treated as the uploaded-document layer; OCR artefacts are stripped from structure/entity extraction and logged."),
            _q("document_kind", "Document type", "What kind of document is this?", kind="select", required=False,
               options=["Certificate of Analysis", "GMP / Manufacturing guidance", "Standard operating procedure", "Patent / claim text", "Clinical / study report", "Product registry", "Other"],
               placeholder="Certificate of Analysis"),
            _q("original_scans_available", "Original scanned PDF", "Are the original scanned pages available for image-level verification?", kind="select", required=False,
               options=["Yes — I will attach", "No — text layer only", "Not sure"],
               help_text="Page-level OCR confidence, bounding boxes and visual verification require the original page images."),
        ],
    },
    "lca_biotherapeutic": {
        "steps": [
            _step("Confirm the scope", "Objective, indication, target, modality, source, jurisdictions and development stage. If scope is missing the run is flagged, not guessed."),
            _step("Ingest candidate / patent evidence", "Paste patent claim text, candidate tables or sequence listings (real publication numbers supported; large sequences accepted)."),
            _step("Extract candidate tokens", "Pull candidate-shaped tokens only — Biologic, Candidate, Project, Description, Demo and Title are NEVER candidates."),
            _step("Run the identity gate", "A valid candidate needs a molecule name, clone, SEQ ID, construct, target + modality, or clinical code; otherwise it is rejected with a reason."),
            _step("Classify patents vs guidance/landscape", "Real WO/EP/US/IN publications become patent families; ipindia_tk_examination_guidelines, ayurveda_patent_landscape, biodiversity_act_2002_abs_nba, DSHEA and FD&C Act stay regulatory context."),
            _step("Detect modality & target", "mAb, bispecific, recombinant protein, fusion, peptide, ADC, vaccine, nucleic-acid; target fit recorded with evidence state."),
            _step("Score the evidence-gated scorecard", "9 weighted criteria (target 15%, mechanism 15%, potency 15%, selectivity 10%, developability 15%, stability 10%, safety 10%, IP 5%, manufacturing 5%) — scores issue only on evaluated data, otherwise 'Not assessed — evidence unavailable'."),
            _step("Top-5 provisional candidates or empty state", "If the gate is empty the honest output is: 'No valid biotherapeutic candidates identified; candidate ranking blocked pending actual patent/literature evidence.' Never fabricate 5-10 molecules per patent."),
            _step("Preclinical, safety, regulatory & FTO pass", "ICH S6(R1) species/route/dose/regimen rationale, dose-response plan, safety status (Characterized/Partially/Unknown), regulatory classification and a separate FTO search."),
            _step("Export the structured report", "Full traceability per candidate with gap → next-experiment mapping."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Candidate / patent space", "Describe the biologic candidates, patent space or paste claim text.", kind="textarea", required=True,
               placeholder="e.g. Anti-inflammatory monoclonal antibodies using plant-derived glycoprotein scaffolds",
               help_text="Tokens like Biologic/Candidate/Project/Demo/Title are rejected by the identity gate; supply molecule names, clones, SEQ IDs or real patent numbers."),
            _q("objective", "Analysis objective", "What should the LCA recommend?", kind="text", required=False,
               placeholder="e.g. Select 1-3 leads for dose-response validation"),
            _q("indication", "Indication / target", "Indication and target, if known.", kind="text", required=False,
               placeholder="e.g. Rheumatoid arthritis, TNF-alpha"),
            _q("modality", "Modality", "Preferred modality, if restricted.", kind="select", required=False,
               options=["Any", "mAb", "Bispecific", "Recombinant protein / enzyme", "Peptide", "Fusion protein", "ADC", "Vaccine / recombinant antigen", "Nucleic-acid / gene therapy"]),
            _q("jurisdictions", "Jurisdictions", "Markets / patent jurisdictions of interest.", kind="text", required=False,
               placeholder="e.g. India, US"),
        ],
    },
    "lca_small_molecule": {
        "steps": [
            _step("Ingest the chemical input or patent", "Register the compound input or small-molecule patent (real publication numbers only; botany/plant extracts are routed to formulation analysis)."),
            _step("Extract chemical identities", "Chemical name, IUPAC, common name, compound/example number, structure, SMILES, InChI/Key, CAS, PubChem CID, patent example, or figure/scheme with an identifiable structure."),
            _step("Run the identity gate", "Generic or project terms (Small, Molecule, Registration, Project, Description, Demo, Title, Botanical, Extract, Candidate, Compound, Target, Product, Patent) are rejected; only source-defined molecular entities become candidates."),
            _step("Separate botanicals & formulations", "Ashwagandha / Withania somnifera as a plant or extract is not a small-molecule candidate; isolated constituents (e.g. Withaferin A, Withanolide D, Bacoside A) are."),
            _step("Extract assay & properties", "Map each candidate → potency → selectivity → ADME → toxicity with reported values and qualifiers; never invent values."),
            _step("Classify patents vs guidance", "Actual WO/EP/US/IN publications form patent families; ayurveda landscape, TK-examination guidance, monographs, FD&C Act, DSHEA stay context and never count as core patents."),
            _step("Markush & claim analysis", "A claim genus is not an experimental molecule; Markush scope (WIPO PATENTSCOPE) is read separately from measured candidates."),
            _step("Score and rank the leads", "Weighted scoring (identity 5%, potency 20%, selectivity 10%, SAR 10%, solubility/permeability 10%, PK 15%, safety 15%, synthesis 5%, patent differentiation 5%, evidence completeness 5%); provisional only, never fabricate."),
            _step("Nonclinical safety & regulatory pass", "ICH M3(R2) safety pharmacology, repeated-dose toxicology, toxicokinetics, reproductive and genetic toxicology — flagged from evidence, not invented."),
        ],
        "auto_run": True,
        "questions": [
            _q("compound_desc", "Compounds / patent", "List specific small molecules (name, SMILES/InChI/CAS, patent example) or the patent to assess.", kind="textarea", required=True,
               placeholder="e.g. Withaferin A (C28H38O6), Withanolide D, Bacoside A"),
            _q("botanical_context", "Botanicals included?", "If plant/extract entries appear, should they be routed to a separate formulation analysis?", kind="select", required=False,
               options=["Yes, route botanical extracts separately", "No botanical entries present", "Yes and include isolated constituents"],
               placeholder="Default: route separately"),
        ],
    },
    "sar_data_extraction": {
        "steps": [
            _step("Enter / upload the patent", "Submit the full small-molecule patent by publication number or document file — headings and metadata alone yield no valid SAR records."),
            _step("Discard parsing artifacts", "Document headings, 'Publication Number', 'Technology Area', 'Representative Compounds', project/demo labels and generic terms are excluded — never compound codes."),
            _step("Validate compound codes", "A code is valid only if the source defines its identity; 'Compound A' with no defined structure is unresolved, not verified."),
            _step("Extract structures & activities", "Link compound identity → structure → target/subject → assay → activity value → unit, preserving manual markers (Compound 1, Example 12) and qualifiers (>/<) as-is."),
            _step("Classify structure–activity linkage", "Direct / Strong indirect / Weak indirect / Uncertain / Not linked per record; uncertain links are never 'verified'."),
            _step("Handle Markush & genera", "Explicit compounds and enumerated members are extractable; an unenumerated claim genus is not a molecule and produces no SAR record."),
            _step("Validate & export", "Human-in-the-loop check via structure/activity source links; export CSV/Excel (42-column schema) and SDF for verified structures only."),
            _step("Analyse SAR provisionally", "R-group / scaffold SAR and activity cliffs only when comparable assay data supports them; otherwise deliver a blocked empty-state report."),
        ],
        "auto_run": True,
        "questions": [
            _q("compound_desc", "Structures & activities", "Paste structures / names with activity data or the patent text to parse.", kind="textarea", required=True,
               placeholder="e.g. Compound 1: Withaferin A — IC50 0.8 µM, target NF-kB, in vitro"),
            _q("activity_metric", "Preferred metric", "Activity indicator to prioritise when multiple are present (IC50 / EC50 / Ki / MIC / % inhibition).", kind="text", required=False,
               placeholder="e.g. IC50"),
        ],
    },
    "antibody_target_predictor": {
        "steps": [
            _step("Confirm prediction scope", "Antibody type, prediction objective, available input (sequence/CDR/structure/patent/assay), species, expected target class and output use; if none of these exist the prediction is blocked or a text-only hypothesis."),
            _step("Extract antibody identity", "ID, clone name, patent example, heavy/light-chain, VH/VL, CDRs, isotype, Fc engineering, format, sequence source and quality — never run sequence prediction on titles, patent numbers or generic categories."),
            _step("Run sequence quality control", "Alphabet validity, non-standard symbols, missing residues, chain boundaries, CDR numbering scheme, VH/VL pairing and sequence length."),
            _step("Classify target evidence by hierarchy (L1–L5)", "L1 direct experimental (co-crystal, direct binding, competition, pull-down, IP, knockout) → L2 functional → L3 sequence/CDR/structure → L4 text/patent → L5 generic. L5 alone never supports a specific target."),
            _step("Generate target candidates", "List each candidate with exact name, gene/protein symbol, species, isoform, domain/epitope, target class, evidence, level, source, contradictory evidence and confidence; 'interleukin' is reported only as a family hypothesis, never a final target."),
            _step("Analyse homology, CDRs & structure", "Sequence similarity, CDR-H3 and paratope comparison, germline assignment and docking — all held as hypothesis-level support, never proof of binding."),
            _step("Cross-check affinity & binding", "Extract Kd/Ka/kon/koff/IC50/EC50 exactly with method, temperature, buffer, replicates and source; 'matched' only when target identity, antibody identity, value and source are all linked."),
            _step("Review selectivity & functional confirmation", "Family panel, off-targets, species cross-reactivity and competition; bindings vs functional vs target-dependence kept distinct."),
            _step("Score prediction transparently", "Component-weighted confidence (explicit source 30%, binding 25%, functional 15%, sequence 10%, structure 10%, selectivity 5%, data quality 5%) — never a single unexplained percentage."),
            _step("Deliver report with alternatives & validation", "Alternative shortlist when confidence is low, six-stage wet-lab validation plan, ICH Q6B developability context, and regulatory/TKDL sources excluded from target evidence."),
        ],
        "auto_run": True,
        "questions": [
            _q("antibody_desc", "Antibody / evidence", "Describe the antibody (format, sequence, CDRs), its target clues, evidence (binding/functional/affinity), or paste the relevant text.", kind="textarea", required=True,
               placeholder="e.g. Humanised IgG1; VH sequence supplied; binds a purified cytokine; refer the exact assay/Kd"),
            _q("antibody_format", "Antibody type", "Antibody format if known.", kind="select", required=False,
               options=["mAb", "Polyclonal", "Recombinant", "scFv", "Fab", "F(ab')2", "Nanobody/VHH", "Bispecific", "Fusion", "Unknown"]),
        ],
    },
    "markush_drafting": {
        "steps": [
            _step("Confirm Markush scope", "Invention type, core scaffold, target technical effect, jurisdictions, prior-art, synthesized/tested compounds and filing strategy — draft only after scaffold, numbering, R-group positions, allowed substituents, common property/activity and one supported route are confirmed."),
            _step("Parse & strip document artifacts", "Remove headings (Project Title, Core Structure Description, Demo, Technology Area), patent-reference labels and markdown from claim text; retain them only as metadata."),
            _step("Verify the core scaffold & structure representation", "Require a drawing, formula, SMILES, InChI, structure file or verified patent figure with ring numbering, attachment points and stereochemistry — a verbal scaffold description is not claim-defining."),
            _step("Extract & bound R-groups", "Define each position's meaning, closed/bounded allowed groups (never bare 'alkyl, aryl' or 'oxygen-containing groups'), valence, steric/synthetic feasibility, examples and support status."),
            _step("Build the combination matrix", "Mark each R1/R2/n combination disclosed, synthesized, tested and supported; never enumerate combinations software can parse into claimable scope."),
            _step("Check chemical validity & n/lactone definition", "Atom valence, ring closures, lactone ring definition and n-attachment; reject groups that break the ring or create impossible valence."),
            _step("Audit support & enablement", "Original-specification support, preparation routes, representative examples, credible technical effect and unity (WIPO common structure + common property/activity)."),
            _step("Review novelty, unity & TK risks", "Prior-art search over scaffold, R-groups, closest subgenus and specific species; TKDL, natural reference (Withaferin A) and biological-resource review for natural-product scaffolds."),
            _step("Draft claim versions", "Version A broad analytical (not filing-ready), Version B supported Markush claim, Version C narrow fallback species claims + composition/process/use claims."),
            _step("Gate export & deliver checklist", "Word/SDF export only for verified, individually defined structures — Markush genus is never exported as a single molecule; deliver attorney/chemist review checklist."),
        ],
        "auto_run": True,
        "questions": [
            _q("core_structure", "Core structure / claim text", "Paste the structure representation (SMILES/InChI/formula), scaffold with ring numbering, R-groups, n, lactone variation, examples and preparation — or the raw draft text to clean.", kind="textarea", required=True,
               placeholder="e.g. SMILES: O=C1O[C@@H]2[C@H]3... ; ring numbering as drawn; R1 = H, OH, OCH3 (C1, Ex. 1-3); R2 = C1-C4 alkyl; n attached to C17 side chain; lactone 5-membered"),
            _q("variant_features", "Variable positions", "Optional structured list of R-groups / n values.", kind="textarea", required=False,
               placeholder="e.g. R1 = H, OH, OCH3 | R2 = Cl, F, methyl | n = 0-2"),
        ],
    },
    # ---------------------------------------------------------------------- #
    # Materials  (2)  — Eureka Formulation + Materials Find-Solutions
    # ---------------------------------------------------------------------- #
    "formulation": {
        "steps": [
            _step("Gate the product classification", "Confirm food / Ayurveda Aahara / supplement / Ayurvedic medicine / botanical drug / pharma / cosmetic before any ingredient percentage."),
            _step("Capture objective & constraints", "Stated target, baseline, constraints and target jurisdictions — empty 'goals' blocks recommendation."),
            _step("Verify ingredient identity & function", "Map every ingredient to a technical function with a data basis — no 'functional role I' filler."),
            _step("Generate evidence-classified candidates", "Concept → literature-derived → prototype → validated; change ONE main strategy per candidate."),
            _step("Audit concentrations & ratios", "Classify as sourced / derived / proposed screening range — never present '8–14%' as validated."),
            _step("Define the process precisely", "Solvent type + ratio, temperature, duration, pH — reject vague 'hydroalcoholic / standardised extract' labels."),
            _step("Assess stability by all four types", "Chemical, microbial, physical, packaging; preservation challenge data required — base alone never proves safety."),
            _step("Run compatibility & manufacturability review", "Data required for 'screened' / 'process validated'; protocol + CPPs + CQAs + batches for validation claims."),
            _step("Review regulatory, claims & IP per jurisdiction", "Pathway only after classification; claims classified; no patentability conclusion from generic references."),
            _step("Deliver risk/decision matrices & bench plan", "Weighted decision matrix (equal transparency), risk matrix with mitigation+test, controlled bench protocol per candidate."),
        ],
        "auto_run": True,
        "questions": [
            _q("problem_text", "Product objective & constraints", "What are you trying to formulate — target, constraints, existing formula, target jurisdiction?", kind="textarea", required=True,
               placeholder="e.g. A restful-sleep liquid with Ashwagandha and Brahmi for Canada — must stay stable and preservable"),
            _q("ingredients", "Ingredients (verified names)", "Ingredients to include or replace, with any known concentrations/ratios.", kind="multi", required=True,
               placeholder="Ashwagandha (Withania somnifera) 8%? Brahmi (Bacopa monnieri) 4%?"),
            _q("formulation_text", "Existing formula / process text (optional)", "Paste any prior formula, percentages or process description to audit.", kind="textarea", required=False,
               placeholder="Paste existing formula / prior agent output for correction"),
            _q("proposed_claims", "Proposed claims", "Any claims you want evaluated (e.g. 'restful sleep support').", kind="textarea", required=False,
               placeholder="restful sleep support (structure/function wording)"),
        ],
    },
    "materials_find_solutions": {
        "steps": [
            _step("Intake material–problem scope", "Current material, grade, loading, failure, target, scale, equipment, jurisdictions, constraints, tests — missing fields block conclusions."),
            _step("Classify the problem", "Categorize failure domain and separate symptom vs root cause (material/process/product/supply)."),
            _step("Characterize the current material", "Identity, grade, physical/chemical/process properties with datasheet basis."),
            _step("Map CMA–CPP–CQA", "ICH Q8(R2) — 'critical' only when linked to a measurable CQA, never a generic passthrough table."),
            _step("Generate real solution candidates", "MS-001/002 with actual material, grade, loading, mechanism, benefit, trade-offs — never Alternative-1/2."),
            _step("Build meaningful solution mind map", "Per-node principle, problem link, improvement, risk, maturity, evidence, validation, scale-up."),
            _step("Review compatibility, cost & maturity", "Compatibility data required; cost needs baseline+quote arithmetic; maturity never from patent alone."),
            _step("Review regulatory & patent status", "Per-jurisdiction suitability; patent link requires number + claim + example + passage + status."),
            _step("Classify risks per category", "Technical / manufacturing / regulatory / cost / IP — each with basis, no 'low risk because cheaper'."),
            _step("Design validation & DOE", "MAT-EX protocol: control + ≥3 batches + replicates + CMAs/CPPs/CQAs + acceptance/failure/decision rules; then DOE. Blocked state lists the 10 required inputs."),
        ],
        "auto_run": True,
        "questions": [
            _q("material_challenge", "Material challenge", "Describe the material / excipient challenge with the observed failure and target value.", kind="textarea", required=True,
               placeholder="e.g. Extract absorbs moisture and cakes during storage; need a better anti-caking agent"),
            _q("current_material", "Current material (name, grade)", "What is currently used, with grade and loading if known.", kind="textarea", required=True,
               placeholder="e.g. Silica dioxide (Aerosil 200), 2% in blend"),
            _q("performance_target", "Performance target / KPP", "Which property must improve, with the target value.", kind="textarea", required=True,
               placeholder="e.g. moisture pick-up < 1.5% after 3 months, flow OK"),
            _q("material_notes", "Additional constraints (scale/equipment/jurisdiction/cost)", "Optional context for candidate screening.", kind="textarea", required=False,
               placeholder="e.g. tablet line, target EU/US feed; budget limit"),
        ],
    },
}

def workflow_for(slug: str) -> dict[str, Any]:
    """Return the canonical guided workflow for an agent slug."""
    entry = AGENT_WORKFLOWS.get(slug)
    if entry is None:
        return {"steps": [_step("Understand request"), _step("Retrieve evidence"), _step("Compile result")], "questions": []}
    return entry


def workflow_steps(slug: str) -> list[dict[str, str]]:
    return workflow_for(slug).get("steps", [])


def workflow_questions(slug: str) -> list[dict[str, Any]]:
    return workflow_for(slug).get("questions", [])