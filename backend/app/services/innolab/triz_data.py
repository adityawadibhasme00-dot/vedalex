"""TRIZ knowledge base for the IP-SAKTI TRIZ Innovation agent.

Canonical Altshuller data:
  * 39 engineering parameters (the improving/worsening axes of the matrix)
  * 40 inventive principles with their core ideas
  * the full 39x39 Contradiction Matrix (1190 populated + 292 known-empty cells)

Matrix provenance: canonical Altshuller (1985) English transcription (Casey
Perno, 2007, circulated as ``triz_matrix.xls``), imported via the MIT-licensed
``kamil-szczepanik/TRIZ-Agents`` project and ``Antropocosmist/
triz-engineering-solver`` (anchor-verified).  The data is checked in
statically under ``data/triz_matrix.json`` so the agent runs fully offline and
deterministic — matrix cells are real lookups, never guessed.

This module is *data + deterministic lookup logic only*; the agent reasoning
branch lives in ``agent_executors._hub_triz``.
"""

from __future__ import annotations

import json
import os
from typing import Any

_DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "triz_matrix.json")


# --------------------------------------------------------------------------- #
# 39 engineering parameters (canonical)
# --------------------------------------------------------------------------- #
# (no, name, description)
TRIZ_PARAMETERS: list[tuple[int, str, str]] = [
    (1, "Weight of moving object", "Mass under gravity for objects that move."),
    (2, "Weight of stationary object", "Mass under gravity for objects that do not move."),
    (3, "Length of moving object", "Any linear dimension (length/width/height) of a moving object."),
    (4, "Length of stationary object", "Linear dimension of a stationary object."),
    (5, "Area of moving object", "2D extent of a moving object's surface."),
    (6, "Area of stationary object", "2D extent of a stationary object's surface."),
    (7, "Volume of moving object", "3D occupancy of a moving object."),
    (8, "Volume of stationary object", "3D occupancy of a stationary object."),
    (9, "Speed", "Velocity of an object or rate of a process/action in time."),
    (10, "Force (intensity)", "Any interaction between systems intended to change a condition."),
    (11, "Stress or pressure", "Force per unit area; tension."),
    (12, "Shape", "External contours / appearance of a system."),
    (13, "Stability of object's composition", "Wholeness, integrity, chemical/physical stability of the system."),
    (14, "Strength", "Ability to resist mechanical failure."),
    (15, "Duration of action by moving object", "Time the moving object can perform the action."),
    (16, "Duration of action by stationary object", "Time the stationary object can perform the action."),
    (17, "Temperature", "Thermal condition of the system."),
    (18, "Illumination intensity", "Brightness / light quality, including UV exposure."),
    (19, "Use of energy by moving object", "Energy consumption of the moving subsystem."),
    (20, "Use of energy by stationary object", "Energy consumption of the stationary subsystem."),
    (21, "Power", "Rate of energy use."),
    (22, "Loss of energy", "Wasted energy."),
    (23, "Loss of substance", "Wasted / lost material (e.g. low extraction yield)."),
    (24, "Loss of information", "Data / signal / traceability loss."),
    (25, "Loss of time", "Wasted time (slow batches, idle steps)."),
    (26, "Quantity of substance / matter", "Amount of material (concentration, dose, solids loading)."),
    (27, "Reliability", "Consistent function under intended conditions over the required time."),
    (28, "Measurement accuracy", "Closeness of measured value to the actual value."),
    (29, "Manufacturing precision", "Closeness of produced parameters to the specified values."),
    (30, "Object-affected harmful factors", "Harmful effects acting on the object from outside (moisture, oxygen, microbes)."),
    (31, "Object-generated harmful factors", "Harmful effects the object produces itself (degradation products, oxidation)."),
    (32, "Ease of manufacture", "Difficulty / cost of producing the object (filterability, scale-up)."),
    (33, "Ease of operation", "Convenience of using the system (handling, labour)."),
    (34, "Ease of repair", "Convenience of restoring after failure (cleaning, CIP)."),
    (35, "Adaptability or versatility", "Ability to respond to external change / serve multiple uses."),
    (36, "Device complexity", "Number and interrelation of system elements / process steps."),
    (37, "Difficulty of detecting and measuring", "Ease of monitoring / inspecting / assaying."),
    (38, "Extent of automation", "Degree of human-free operation."),
    (39, "Productivity", "Useful function performed per unit time (throughput, batch yield/time)."),
]

PARAM_BY_NO = {no: (name, desc) for no, name, desc in TRIZ_PARAMETERS}

# Keyword hints used to deterministically map a user's improve/worsen phrase to
# one of the 39 parameters.  Lower pairs scan first so "stationary" words bind
# to the stationary family before the generic one.
_PARAM_HINTS: list[tuple[int, list[str]]] = [
    (1, ["moving weight", "weight of the moving", "lightweight", "unmoving weight of moving"]),
    (2, ["stationary weight", "weight of the stationary", "weight of the vessel", "weight of the tank",
         "static load", "dead weight"]),
    (3, ["length of moving", "moving length", "sheet length", "film length", "wire length"]),
    (4, ["length of stationary", "stationary length", "column height", "vessel length", "chamber length"]),
    (5, ["moving area", "area of moving", "surface area of the moving"]),
    (6, ["stationary area", "area of stationary", "filter area", "vessel surface area", "bed area", "surface area of the column"]),
    (7, ["moving volume", "volume of moving", "batch volume suspended"]),
    (8, ["stationary volume", "tank volume", "vessel volume", "reactor volume", "capacity of the tank",
         "volume of the equipment"]),
    (9, ["speed", "faster", "rate of the process", "process rate", "velocity", "throughput rate",
         "reaction rate", "extraction rate", "mixing speed", "rpm", "air velocity"]),
    (10, ["force", "torque", "load capacity", "pulling", "interaction between", "mixing force", "shear force", "magnetic force"]),
    (11, ["pressure", "stress", "tension", "vapour pressure", "operating pressure", "hydrostatic", "compressive"]),
    (12, ["shape", "geometry", "profile", "contour", "form factor", "particle shape", "droplet shape"]),
    (13, ["stability", "degradation", "degrades", "degrade", "potency loss", "loss of potency", "shelf life",
          "rancidity", "oxidise", "oxidation", "phase separation", "settling", "sedimentation", "caking",
          "clumping", "precipitate", "discolouration", "discoloration", "decompose", "hydrolysis", "bleaching"]),
    (14, ["strength", "durable", "mechanical strength", "tensile", "tear resistance", "hardness", "breaking load"]),
    (15, ["moving", "duration of moving", "runtime", "endurance"]),
    (16, ["stationary", "duration of the stationary", "service life", "storage = duration of stationary",
          "duration of storage", "storage life", "static dwell time", "long storage"]),
    (17, ["temperature", "heat", "hot", "cold", "thermal", "boiling", "evaporat", "drying temperature",
          "mild heat", "pasteuris", "sterilis", "reflux", "freez", "chill", "steam"]),
    (18, ["illumination", "light", "brightness", "uv", "uv exposure", "sunlight", "lamp", "photostability"]),
    (19, ["energy of the moving", "moving energy", "energy consumption of the moving"]),
    (20, ["energy of the stationary", "stationary energy", "furnace energy", "dryer energy", "boiler energy"]),
    (21, ["power", "kilowatt", "horsepower", "heater rating", "power draw"]),
    (22, ["loss of energy", "waste energy", "heat loss", "energy efficiency", "low efficiency", "inefficient",
          "energy wastage", "heat wasted"]),
    (23, ["loss of substance", "low yield", "yield", "losses", "material loss", "carryover", "retention loss",
          "evaporation loss", "wastage", "recovery rate", "extraction efficiency", "left behind residue"]),
    (24, ["loss of information", "lost data", "traceability", "batch records", "data loss", "documentation gap"]),
    (25, ["loss of time", "slow", "time", "delay", "waiting", "cycle time", "batch time", "idle", "takes long",
          "long drying", "overnight"]),
    (26, ["quantity of substance", "concentration", "amount of material", "dose", "active content", "solids content",
          "loaded", "loading", "potency of 20", "dilute", "excipient level"]),
    (27, ["reliability", "consistent", "reproducible", "robust", "batch-to-batch", "failure rate", "defect rate",
          "falling", "varies", "inconsistent", "reliable", "variation between batches"]),
    (28, ["measurement accuracy", "assay accuracy", "measurement", "detection limit", "quantification", "looq",
          "loq", "precise reading", "hplc result", "accurate result"]),
    (29, ["manufacturing precision", "precision", "tolerance", "uniformity", "particle size distribution",
          "homogeneous mix", "repeatability of the process", "controlled parameters", "consistency of the product"]),
    (30, ["moisture", "humidity", "oxygen", "microbial", "mould", "fungal", "contamination", "external",
          "environmental", "air ingress", "pest", "foreign matter", "dust", "rain"]),
    (31, ["generated", "byproduct", "by-product", "side product", "toxin", "odour", "taint", "off-taste",
          "degradation product", "softening of the product", "self-heating", "off-colour", "own harm"]),
    (32, ["ease of manufacture", "easy to produce", "manufacturing", "scale-up", "filterability", "filters slowly",
          "clog", "hard to process", "sticky mass", "production difficulty", "processable", "manufacturability"]),
    (33, ["ease of operation", "operator", "manual labour", "ease of use", "handling", "stirring effort",
          "difficult to operate", "skilled labour"]),
    (34, ["ease of repair", "maintenance", "repair", "cleaning", "cip", "scrub", "service"]),
    (35, ["adaptability", "versatile", "multi-purpose", "personalised", "customised", "adjustable", "tunable",
          "responding to", "different customers", "variable dosage"]),
    (36, ["device complexity", "complex", "many parts", "many steps", "number of steps", "equipment complexity",
          "extra unit", "cumbersome", "complicated system"]),
    (37, ["difficulty of detecting", "hard to measure", "hard to monitor", "inspect", "difficult to assay",
          "no quick test", "visible only in lab", "cannot detect"]),
    (38, ["automation", "automatic", "sensors", "control loop", "programmable", "process control", "auto dosing"]),
    (39, ["productivity", "throughput", "output per unit time", "batch throughput", "kg per hour", "installed capacity",
          "produce more", "scale up production", "capacity utilisation"]),
]

# Parameters that describe the *outcome of the whole process* vs the object.
_MOVING_PARAM_NOS = {1, 3, 5, 7, 15, 19}
_STATIONARY_PARAM_NOS = {2, 4, 6, 8, 16, 20}


def map_parameter(aspect: str) -> dict[str, Any]:
    """Deterministic mapping of a user phrase to a 39-parameter candidate.

    Returns ``{"no", "name", "confidence"}`` where confidence is high/medium/
    low.  Low confidence means the phrase did not match any domain hint and the
    mapping MUST be human-validated before relying on the matrix cell (the
    agent reports this explicitly — parameters are never silently guessed).
    """
    text = (aspect or "").lower().strip()
    if not text:
        return {"no": None, "name": "", "confidence": "low", "matched_hint": ""}

    best_no: int | None = None
    best_hits = 0
    best_hint = ""
    for no, hints in _PARAM_HINTS:
        hits = [h for h in hints if h in text]
        if not hits:
            continue
        score = 0
        for h in hits:
            # longer, more specific hints score higher
            score += 1 + min(3, len(h.split())) + (1 if h in text.split() else 0)
        if score > best_hits:
            best_hits, best_no, best_hint = score, no, hits[0]

    if best_no is None:
        return {"no": None, "name": "", "confidence": "low", "matched_hint": ""}

    if "stationary" in text or "static" in text or "vessel" in text or "tank" in text or "equipment" in text:
        if best_no in _MOVING_PARAM_NOS:
            mate = {1: 2, 3: 4, 5: 6, 7: 8, 15: 16, 19: 20}[best_no]
            best_no = mate
    elif "moving" in text or "product" in text or "batch" in text or "tablet" in text:
        if best_no in _STATIONARY_PARAM_NOS:
            mate = {2: 1, 4: 3, 6: 5, 8: 7, 16: 15, 20: 19}[best_no]
            best_no = mate

    name = PARAM_BY_NO[best_no][0]
    confidence = "high" if best_hits >= 3 else "medium" if best_hits == 2 else "low"
    return {"no": best_no, "name": name, "confidence": confidence, "matched_hint": best_hint}


# --------------------------------------------------------------------------- #
# 40 inventive principles (canonical)
# --------------------------------------------------------------------------- #
# (no, name, core idea)
TRIZ_PRINCIPLES: list[tuple[int, str, str]] = [
    (1, "Segmentation", "Divide the object into independent parts; increase the degree of fragmentation."),
    (2, "Taking out / Extraction", "Separate the disturbing part or the necessary part from the object."),
    (3, "Local quality", "Change the object from uniform to non-uniform; let each part do a different useful job."),
    (4, "Asymmetry", "Replace a symmetrical form with an asymmetrical one; increase asymmetry."),
    (5, "Merging / Consolidation", "Bring identical or similar objects, or operations, together in space or time."),
    (6, "Universality", "Make one part perform several functions to eliminate other parts."),
    (7, "Nested doll", "Place one object inside another; pass one through a cavity of another."),
    (8, "Anti-weight / Counterweight", "Compensate the weight by joining with one that provides lift."),
    (9, "Preliminary anti-action", "Replace the action with counter-action prepared in advance to control the harm."),
    (10, "Preliminary action", "Perform the required change — fully or partially — in advance."),
    (11, "Beforehand cushioning", "Prepare emergency means in advance to compensate for low reliability."),
    (12, "Equipotentiality", "Limit position changes in a potential field; avoid raising/lowering."),
    (13, "The other way round / Inversion", "Invert the action; make movable parts fixed and fixed parts movable."),
    (14, "Spheroidality / Curvature", "Replace straight lines with curves, balls, spirals; linear motion by rotation."),
    (15, "Dynamics", "Let the object/environment be optimised at each stage; make parts adjustable or mobile."),
    (16, "Partial or excessive actions", "If 100% is hard, achieve a little less or a little more."),
    (17, "Another dimension", "Move from 1D to 2D to 3D; use multi-layer arrangements; use the other side."),
    (18, "Mechanical vibration", "Make the object oscillate or vibrate; increase frequency to ultrasonic."),
    (19, "Periodic action", "Replace continuous action with periodic/pulsed action; change the frequency."),
    (20, "Continuity of useful action", "Carry the work out continuously at full load; remove idle work."),
    (21, "Skipping / Rushing through", "Conduct the process or its stages at high speed."),
    (22, "Blessing in disguise / Convert harm into benefit", "Use aversive factors to obtain a positive effect."),
    (23, "Feedback", "Introduce feedback; if it exists, modify it."),
    (24, "Intermediary", "Use an intermediary carrier or process; merge temporarily with an easily-removed object."),
    (25, "Self-service", "Make the object service itself; use waste resources."),
    (26, "Copying", "Use simpler, inexpensive copies instead of the fragile, expensive original."),
    (27, "Cheap short-living objects", "Replace an expensive object with a multitude of inexpensive ones."),
    (28, "Mechanics substitution", "Replace a mechanical system with sensory, electric, magnetic or field effects."),
    (29, "Pneumatics and hydraulics", "Use gas/liquid parts instead of solid ones."),
    (30, "Flexible shells and thin films", "Use flexible shells and thin films instead of 3D structures."),
    (31, "Porous materials", "Make the object porous, or add porous elements; fill pores in advance."),
    (32, "Color changes", "Change the colour or transparency of the object or its environment."),
    (33, "Homogeneity", "Make interacting objects of the same material — or one with similar properties."),
    (34, "Discarding and recovering", "Make finished parts disappear (dissolve/evaporate) or restore them during work."),
    (35, "Parameter changes", "Change the physical state, concentration, density, flexibility or temperature."),
    (36, "Phase transitions", "Exploit phenomena that occur during phase transitions (volume change, heats)."),
    (37, "Thermal expansion", "Use thermal expansion of materials; use materials with different coefficients."),
    (38, "Strong oxidants / Accelerated oxidation", "Replace ordinary air with oxygen-enriched air, oxygen, then ozone."),
    (39, "Inert atmosphere", "Replace the normal environment with an inert one; add neutral additives."),
    (40, "Composite materials", "Change from uniform to composite (multiple) materials."),
]

PRINCIPLE_BY_NO = {no: (name, idea) for no, name, idea in TRIZ_PRINCIPLES}

# Known-empty-matrix rule: for contradiction cells with no canonical principles,
# the referee still proposes directions but they are explicitly tagged
# "Source: inferred".
_EMPTY_CELL_PROPOSALS: dict[tuple[int, int], list[int]] = {
    (13, 13): [35, 1, 2],  # stability vs stability → process control of degradation
    (17, 13): [1, 35, 32],
}


# --------------------------------------------------------------------------- #
# 39x39 contradiction matrix (full, static, offline)
# --------------------------------------------------------------------------- #
def load_matrix() -> dict[tuple[int, int], list[int]]:
    """Load the canonical 39x39 matrix from the checked-in JSON asset."""
    with open(_DATA_FILE, encoding="utf-8") as fh:
        raw = json.load(fh)
    cells: dict[tuple[int, int], list[int]] = {}
    for key, principles in raw.get("cells", {}).items():
        row, col = key.split(",")
        cells[(int(row), int(col))] = [int(p) for p in principles]
    return cells


_MATRIX: dict[tuple[int, int], list[int]] | None = None


def matrix() -> dict[tuple[int, int], list[int]]:
    global _MATRIX
    if _MATRIX is None:
        _MATRIX = load_matrix()
    return _MATRIX


def lookup_cell(improving_no: int, worsening_no: int) -> dict[str, Any]:
    """Exact matrix-cell retrieval for an (improving, worsening) parameter pair.

    Returns the ranked principle IDs plus an explicit provenance tag:
      * "matrix"    → canonical Altshuller cell exists (loaded data).
      * "reverse"   → canonical cell for the reversed pair was used.
      * "inferred"  → no canonical cell: direction proposed by domain rule,
                      flagged for expert validation against the full matrix.
    """
    key = (int(improving_no), int(worsening_no))
    cells = matrix()
    if key in cells:
        return {"cell": f"{key[0]}→{key[1]}", "principles": cells[key], "source": "matrix"}
    if key in _EMPTY_CELL_PROPOSALS:
        return {"cell": f"{key[0]}→{key[1]}", "principles": _EMPTY_CELL_PROPOSALS[key], "source": "inferred"}
    reverse = (key[1], key[0])
    if reverse in cells:
        return {"cell": f"{key[1]}→{key[0]} (reversed)", "principles": cells[reverse], "source": "reverse"}
    return {"cell": f"{key[0]}→{key[1]}", "principles": [], "source": "empty"}


# Global principle usage frequency computed from the full matrix — used for
# the "how often does Altshuller pair this principle" ranking.
def _frequency_counts() -> dict[int, int]:
    counts: dict[int, int] = {}
    for principles in matrix().values():
        for p in principles:
            counts[p] = counts.get(p, 0) + 1
    return counts


FREQUENCY = _frequency_counts()


# --------------------------------------------------------------------------- #
# Domain (IP-SAKTI: Ayurveda botanical processing) principle application cards
# --------------------------------------------------------------------------- #
# Per-principle: (IP-SAKTI application, expected benefit, trade-off,
#                validation experiment).  Written against Ayurvedic botanical
#                 extraction / formulation / pharma-lab scenarios.
_PRINCIPLE_APPLICATIONS: dict[int, tuple[str, str, str, str]] = {
    1: ("Split the extract step into staged fractions (coarse → fine), or divide the corpus of active-rich fractions and process them separately.",
        "Harsh steps touch only what they must; gentle fractions keep actives intact, raising potency retention and yield clarity.",
        "More unit operations; a longer process line.",
        "Run a two-stage vs single-stage extraction and compare marker % and potencies."),
    2: ("Remove the interfering matrix first — e.g. clarify/degum before concentrating — or pull out only the active-rich fraction and leave the inert ballast behind.",
        "Lesso co-extracted impurities and denser actives in the finished extract.",
        "Extra clarification step may lose some actives to the waste stream.",
        "Measure marker recovery in clarified vs unclarified liquor."),
    3: ("Let different zones of the contactor do different jobs: a warm zone for extraction, a cool zone for protection of thermolabile markers.",
        "High solvency where needed, low thermal stress where it matters — better overall stability.",
        "Zone control adds instrumentation and tuning effort.",
        "Compare marker retention with split-zone vs uniform temperature."),
    4: ("Use an asymmetric baffle/paddle geometry in extraction or coating to de-energise dead zones and prevent uneven heating.",
        "Uniform hydrodynamics without raising total energy input.",
        "Non-standard impeller geometry is harder to source.",
        "Do a residence-time-distribution test with a visual dye."),
    5: ("Merge the extraction and concentration stages in one vessel, or combine several botanical charges before drying to smooth batch-to-batch variation.",
        "Fewer transfers and less energy, tighter consistency across batches.",
        "Bigger vessels → higher capital.",
        "Compare inter-batch marker SD for combined vs separate runs."),
    6: ("Make one unit multi-purpose: an extractor that also concentrates, or a drier that also deodorises, cutting handling losses.",
        "Same active through fewer transfers = less carryover loss.",
        "Single multi-tasking unit becomes a failure bottleneck.",
        "Track total active recovery per kilogram input."),
    7: ("Nest jacketed vessels or use a compact column-in-column layout so the footprint stays small while the effective path gets longer.",
        "Full-duration contact in a compact footprint with shorter transfer lines.",
        "Cleaning access becomes tighter.",
        "Compare effective contact path vs active take-up in the nested build."),
    8: ("Counterweight or hydraulic-cushion heavy agitated vessels so gentle operation no longer drains operator/utility effort.",
        "Calmer process = fewer stress spikes for thermolabile actives.",
        "Hydraulic hardware adds maintenance.",
        "Measure vibration/stress and marker loss together."),
    9: ("Pre-neutralise or pre-precipitate the troublesome ballast before the run, or pre-dry the charge so humidity does not trigger caking.",
        "Harmful factors are de-fused before they can act — cleaner downstream steps.",
        "One more pre-treatment unit.",
        "Compare caking failure rate with and without pre-treatment."),
    10: ("Soak/extract the raw drug in advance (overnight pre-maceration), pre-heat lines, or pre-wet the matrix so the main run is short and mild.",
        "Shorter, gentler main extraction achieves the same take-up.",
        "Longer total elapsed time despite shorter hot phase.",
        "Compare energy and potency for pre-soaked vs direct runs."),
    11: ("Keep a chilled side-vessel or added anti-oxidant buffer ready to hand when the main batch risks overheating.",
        "Minor excursions no longer ruin an entire batch.",
        "Carrying a cool reserve wastes a little energy.",
        "Simulate a temperature excursion with/without the cushion; compare potency."),
    12: ("Arrange the plant so liquids flow downhill between extraction, concentration and drying — no pumped lifts, no re-heating losses.",
        "Lower energy bill and gentler handling of the actives.",
        "Site layout constraints.",
        "Compare energy per kg dried with gravity vs pumped routing."),
    13: ("Invert the process: instead of concentrating a dilute extract (long heating), strip the product out of a concentrated feed with a counter-current, or dry first and extract dry later.",
        "Avoids the long worst-case heating window entirely.",
        "Process conventions must change; scale-up plan re-done.",
        "Compare marker profile between conventional and inverted route."),
    14: ("Use spiral heat exchangers, peristaltic loops, or rotary-film evaporation so contact is curved and thin rather than deep and long.",
        "High heat-transfer in thin films = short exposure = less degradation.",
        "Thin-film equipment is costlier to clean and operate.",
        "Compare potency hold-up in a thin-film vs stirred-batch evaporator."),
    15: ("Make the temperature, solvent ratio and agitation adaptive to the stage (start strong, ramp down as marker nears release).",
        "Optimal energy and solvency at each stage; less total thermal stress.",
        "Needs a control loop and stage sensors.",
        "Run a staged profile vs constant conditions; compare yield and potency."),
    16: ("Slightly over- or under-dilute: use a touch less solvent then a gentle re-extract, or concentrate to slightly-higher solids to stabilise.",
        "Cheap way past stubborn equilibria without harsh conditions.",
        "May slightly change solids/ratio targets.",
        "Compare recovery with nominal vs slightly adjusted solvent ratios."),
    17: ("Move to multi-layer bed configurations, use both faces of the contactor, or rotary/vertical layouts to lengthen contact without a footprint blow-up.",
        "Longer exposure/contact with less floor space.",
        "Vertical plant needs more headroom and pumps.",
        "Compare take-up in stacked-bed vs single-bed variants."),
    18: ("Vibrate the extraction bed, apply ultrasonic agitation, or use a vibrating sieve after drying to break mass-transfer resistance.",
        "Faster extraction without raising temperature — actives stay cool.",
        "Reasonable power draw; adds noise and maintenance.",
        "Compare marker yield with vs without ultrasound at equal temperature."),
    19: ("Use pulsed extraction and pulsed sprays (intermittent percolation, pulsed vacuum) instead of a continuous hot boil.",
        "Peak solvency with a lower thermal duty; periodic breathing removes vapour.",
        "Pulsing may extend total elapsed time.",
        "Compare potency after pulsed vs continuous run at equal yield."),
    20: ("Keep the line hot and the flows continuous — pipe the extract straight from extraction into concentration instead of cooling, storing and re-heating.",
        "No repeated heat-cool cycles; fewer energy and actives losses.",
        "Continuous line is harder to schedule around batches.",
        "Track heat-cool cycle count vs potency loss across runs."),
    21: ("Flash-evaporate or dry at high speed (short-path, thin-film, rapid dehumidification) so the vulnerable window is minimised.",
        "The product spends less time under stress = better retention.",
        "Fast machines are pricey and need careful control.",
        "Compare dry-basis potency between flash and slow drying."),
    22: ("Turn the offending heat/oxidation into a benefit — e.g. use recovered waste heat to pre-dry, or harness the colour-forming step as a natural indicator of done-ness.",
        "Waste stream becomes a resource; process gains a free signal.",
        "Requires re-plumbing heat recovery.",
        "Measure energy recovered and use it to offset a drying step."),
    23: ("Add inline feedback: moisture/refractive-index/colour sensors drive the process set-points automatically so the run self-corrects.",
        "Steady output despite feed variability — fewer off-spec batches.",
        "Sensor calibration and maintenance.",
        "Compare off-spec rate with vs without the feedback loop."),
    24: ("Use an intermediary — an adsorbent/filter-aid bed, a chelating agent, or a sacrificial co-solvent — to shuttle the actives through gentler conditions.",
        "The delicate active is shielded while the work still gets done.",
        "Intermediary needs removal; residue checks do add cost.",
        "Verify intermediate does not contaminate the final extract (residue assay)."),
    25: ("Make the vessel clean itself by circulating the spent solvent or steam-blow back the waste bed — no manual scrape-down.",
        "Less operator exposure and faster turnarounds per shift.",
        "CIP skids add floor space and water demand.",
        "Measure cleaning time and residual carryover between batches."),
    26: ("Use a simpler twin (a surrogate botanical, a laboratory mini-column, or a model solvent) to run the expensive optimisation experiments before the real batch.",
        "Cheap, fast parameter sweeps protect prime raw material.",
        "The surrogate may not mirror every behaviour exactly — validate the fit.",
        "Confirm surrogate results transfer to the real charge (correlation check)."),
    27: ("Use multiple small, inexpensive pretreatment cartridges instead of one heavy-duty refining unit — replace cartridges rather than fight scaling.",
        "Consistent performance and simple maintenance at low cost.",
        "Disposable consumables add recurring cost.",
        "Compare yield consistency between cartridge-sets and a single big unit."),
    28: ("Replace mechanical stirring with magnetic stir-bars, acoustic/ultrasonic excitation, or electromagnetic-assisted percolation.",
        "No shaft penetrations — sealed system, less friction heat.",
        "Field-based drives can be unfamiliar to operators.",
        "Compare extraction efficiency and marker retention vs mechanical agitation."),
    29: ("Use gas-assisted or liquid-fluidised bed extraction/aeration to move the bed without churning (sparged mixing).",
        "Mild, even agitation with no hot-wall gradient.",
        "Foaming control may be needed.",
        "Measure temperature uniformity under sparge vs mechanical mixing."),
    30: ("Run the operation behind a flexible membrane/vapour film (sealed flexible-lid vessels, thin-film coats on the wet bed) to cap evaporation and oxygen ingress.",
        "Little thermal and oxidative exposure — the mass stays 'protected'.",
        "Membrane/film materials must be food-legal and removable.",
        "Assay oxidation markers (rancidity) with vs without the film cover."),
    31: ("Use porous carrier matrices (rice-hull-like bed media, porous silica or macroporous resin) to hold solvent and spread contact into the bed.",
        "Solvent and actives get deep, uniform contact at low heat.",
        "Carrier may need to be sieved out afterwards.",
        "Compare active take-up into a porous matrix bed vs plain bed."),
    32: ("Use colour changes as a cheap process indicator — a natural dye in the extract signals concentration or endpoint; a colour card grades dryness.",
        "Instant, cheap endpoint detection without lab waits.",
        "Colour is subjective; keep a reference set.",
        "Correlate the colour index against lab assay on the same samples."),
    33: ("Match like-with-like: keep solvent, vessel and filter materials chemically compatible with the extract so nothing leaches or binds the markers.",
        "Fewer losses to wall adsorption and leachables — cleaner product.",
        "Material choices narrow (fewer cheap options).",
        "Assay marker recovery from glass vs polymer surfaces."),
    34: ("Discard spent solids efficiently (extract-leached marc) or regenerate the resin/adsorbent bed during operation — keep only the loaded phase.",
        "The process does not carry dead weight; beds keep peak capacity.",
        "Spent-marc handling and regeneration chemistry add steps.",
        "Measure bed capacity across regeneration cycles."),
    35: ("Change process parameters — shift the solvent ratio, concentration, drying temperature or co-solvent concentration to a sweeter window for the markers.",
        "Simply changing the operating window is often the cheapest fix.",
        "Each parameter change needs a small experiment to confirm.",
        "Sweep solvent ratio / temperature in a small design-of-experiments."),
    36: ("Exploit phase transitions — use melt/crystallise purifications, freeze concentration, or adsorption-desorption swings to separate actives from ballast.",
        "Effectively sharp separations using latent-heat effects.",
        "Cryo/crystallisation plant is capital heavy.",
        "Test freeze-concentration vs vacuum evaporation for marker retention."),
    37: ("Use differential thermal expansion — e.g. bimetallic or thermally-responsive fittings that open/close as the vessel heats — to automate pressure/venting without sensors.",
        "Passive, self-acting process control that never drifts.",
        "Moving thermal elements can fatigue.",
        "Cycle-test the thermal actuator for repeatable open/close over runs."),
    38: ("Controlled accelerated oxidation — flash-pasteurise or use micro-oxygenation instead of long open-air boil for stabilisation (and as sanitisation).",
        "Short sharp exposure cleans and stabilises without long heating.",
        "Ozone/oxygen handling safety.",
        "Compare microbial load and marker retention after flash-oxidation."),
    39: ("Run the extraction under inert atmosphere (nitrogen blanketing / vacuum) to cut oxidation of heat-sensitive actives.",
        "Marker oxidation drops dramatically — longer shelf life.",
        "Inert-gas supply and sealed vessels add cost.",
        "Assay oxidation markers with vs without N₂ blanket."),
    40: ("Use composite materials — a co-processed excipient blend, a layered film, or reinforcements in the tablet matrix — to get properties no single material has.",
        "Combined stability, flow and release behaviour in one system.",
        "Composites must be verified as the last processing change.",
        "Compare tablet CQAs between single-excipient and co-processed matrix."),
}
_APPLICATION_FALLBACK = (
    "Translate this principle into your system by asking: what would it mean for this product/process?",
    "A cleaner, more targeted solution than the status quo.",
    "Verify no new harm is introduced.",
    "Run a focused A/B experiment on the changed parameter.",
)


def principle_application(no: int) -> tuple[str, str, str, str]:
    return _PRINCIPLE_APPLICATIONS.get(no, _APPLICATION_FALLBACK)


# One-line "what this principle means for IP-SAKTI" shift used in ranking.
_IPSAKTI_FIT: dict[int, int] = {
    1: 8, 2: 9, 3: 8, 4: 4, 5: 6, 6: 6, 7: 3, 8: 2, 9: 7, 10: 8,
    11: 5, 12: 3, 13: 7, 14: 5, 15: 8, 16: 6, 17: 4, 18: 7, 19: 6, 20: 6,
    21: 7, 22: 6, 23: 8, 24: 7, 25: 6, 26: 6, 27: 4, 28: 7, 29: 4, 30: 7,
    31: 7, 32: 5, 33: 6, 34: 6, 35: 9, 36: 7, 37: 3, 38: 5, 39: 8, 40: 5,
}


# --------------------------------------------------------------------------- #
# Root-cause hypothesis templates (Ayurveda botanical processing domain)
# --------------------------------------------------------------------------- #
RCA_HYPOTHESES: list[dict[str, str]] = [
    {
        "id": "rca-1",
        "title": "Thermal pathway",
        "detail": "Sustained heating (hot boil, long evaporation, hot drying) degrades thermolabile markers and accelerates discoloration — the exposed mass spends too long above its degradation temperature.",
        "confirm": "Run the extraction/evaporation at a 10-15°C lower jacket temperature for the same yield target; assay marker % before/after.",
    },
    {
        "id": "rca-2",
        "title": "Oxidative / moisture pathway",
        "detail": "Open-air operation lets oxygen and humidity reach the wet mass; unsaturated markers oxidise, hydrolyse or develop rancidity/off-taste during processing and storage.",
        "confirm": "Cycle the same batch with N₂ blanketing vs open air; compare oxidation markers (peroxide/aldehyde index, colour).",
    },
    {
        "id": "rca-3",
        "title": "Physical state pathway",
        "detail": "Concentration and cooling drive precipitation, phase separation, caking or settling of gums/resins — actives get trapped in an unusable phase or the product becomes non-uniform.",
        "confirm": "Centrifuge or sieve the finished concentrate and assay the separated phases for marker content.",
    },
    {
        "id": "rca-4",
        "title": "Mass-transfer pathway",
        "detail": "The solvent cannot reach the actives inside intact cell walls or dense matrices — so yield is low and operators push energy/time harder, which then harms stability.",
        "confirm": "Compare marker yield after size-reduction/pre-maceration vs direct extraction at identical conditions.",
    },
    {
        "id": "rca-5",
        "title": "Process-configuration pathway",
        "detail": "The contradiction is enforced by the process layout itself — single-stage hot extraction couples yield to temperature, so any yield push inevitably spikes thermal stress.",
        "confirm": "Model a staged/counter-current flow vs single stage at the same total energy and compare both yield and marker retention.",
    },
]


def brief_context(text: str) -> str:
    """Tiny deterministic signal extractor used to flavour output sections."""
    low = text.lower()
    hints = []
    for key in ("stability", "yield", "potency", "temperature", "energy", "cost", "time",
                "extract", "tablet", "dry", "shelf life", "moisture", "batch", "scale"):
        if key in low:
            hints.append(key)
    return ", ".join(hints) or "the stated problem"