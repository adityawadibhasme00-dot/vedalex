"""External official-dataset harvesters for VEDALEX RAG.

The multi-omics seed corpus carries curated records. This module supplements
them with records fetched from four official, no-registration, scriptable public
sources, and can replay a committed snapshot so the platform works offline:

    GBIF        Global Biodiversity Information Facility
                https://www.gbif.org/  - CC-BY 4.0 / CC0
                Plant nomenclature: accepted name, taxon key, family,
                taxonomic status and synonyms for the medicinal plants already
                present in botanical_synonyms.json.
                https://techdocs.gbif.org/en/openapi/

    PubChem     NCBI PubChem PUG-REST
                https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest - public domain
                Canonical identifiers (CID, InChIKey, SMILES, formula) for the
                marker compounds the corpus already cites.

    UniProt     UniProtKB REST
                https://rest.uniprot.org/ - CC BY 4.0
                Reviewed protein entries and their function annotations.

    NCBI        NCBI E-utilities
                https://www.ncbi.nlm.nih.gov/books/NBK25501/ - public domain
                Gene IDs, symbols and summaries via esummary.

Every record carries a real, resolvable identifier so the hallucination guard can
cite it deterministically. Sources that are unreachable (PharmGKB, HMDB,
WikiPathways) are recorded in UNAVAILABLE_SOURCES with the reason rather than
being faked.

Nothing here ever raises into the knowledge-base load path: a harvester returns
[] on any failure so an offline deployment still starts.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SNAPSHOT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "data",
    "external",
)

USER_AGENT = (
    "VEDALEX-IP-SAKTI/1.0 (research prototype; "
    "+https://github.com/adityawadibhasme00-dot/vedalex)"
)

SOURCE_LICENSES: dict[str, dict[str, str]] = {
    "gbif": {
        "publisher": "Global Biodiversity Information Facility (GBIF) Secretariat",
        "homepage": "https://www.gbif.org/",
        "license": "CC-BY 4.0 / CC0 1.0",
        "license_url": "https://www.gbif.org/copyright-guidelines",
        "citation": "GBIF.org contributors, accessed via the GBIF API.",
    },
    "pubchem": {
        "publisher": "National Center for Biotechnology Information (NCBI)",
        "homepage": "https://pubchem.ncbi.nlm.nih.gov/",
        "license": "Public domain (US Government work)",
        "license_url": "https://www.ncbi.nlm.nih.gov/home/about/policies/",
        "citation": "Kim S. et al. PubChem 2023, Nucleic Acids Res. 51(D1):D1373-D1380.",
    },
    "uniprot": {
        "publisher": "UniProt Consortium",
        "homepage": "https://www.uniprot.org/",
        "license": "CC BY 4.0",
        "license_url": "https://www.uniprot.org/help/license",
        "citation": "UniProt Consortium, UniProtKB, accessed via the UniProt REST API.",
    },
    "ncbi_gene": {
        "publisher": "National Center for Biotechnology Information (NCBI)",
        "homepage": "https://www.ncbi.nlm.nih.gov/gene",
        "license": "Public domain (US Government work)",
        "license_url": "https://www.ncbi.nlm.nih.gov/home/about/policies/",
        "citation": "NCBI Gene, accessed via NCBI E-utilities.",
    },
}

UNAVAILABLE_SOURCES: list[dict[str, str]] = [
    {
        "source": "pharmgkb",
        "status": "unreachable",
        "reason": "api.pharmgkb.org failed DNS resolution from the build host; "
                  "no snapshot could be retrieved.",
    },
    {
        "source": "hmdb",
        "status": "forbidden",
        "reason": "hmdb.ca/unearth returned HTTP 403 to scripted access.",
    },
    {
        "source": "wikipathways",
        "status": "unavailable",
        "reason": "webservice.wikipathways.org findPathwaysByText returned HTTP 404; "
                  "the legacy endpoint is no longer served.",
    },
    {
        "source": "tkdl",
        "status": "restricted",
        "reason": "TKDL access requires a registered user account and per-request "
                  "approval from the Department of Science and Technology. No "
                  "open bulk release exists, so permitted TK prior art stays "
                  "limited to the cited classical texts.",
    },
    {
        "source": "api_monographs",
        "status": "restricted",
        "reason": "The Ayurvedic Pharmacopoeia of India is a priced publication of "
                  "the Government of India and has no open machine-readable "
                  "release. Only the already-cited monograph identifiers are used.",
    },
    {
        "source": "patent_fulltext",
        "status": "not_bulk_feasible",
        "reason": "Google Patents Public Datasets are multi-terabyte; the bulk "
                  "release is inappropriate for this repository. Retrieval stays "
                  "on the official India patent and WIPO search interfaces.",
    },
]

# The nine medicinal plants already indexed in botanical_synonyms.json.
TARGET_PLANTS: list[tuple[str, str]] = [
    ("ING-ASHWAGANDHA", "Withania somnifera"),
    ("ING-BRAHMI", "Bacopa monnieri"),
    ("ING-SHANKHAPUSHPI", "Convolvulus pluricaulis"),
    ("ING-HARIDRA", "Curcuma longa"),
    ("ING-TULSI", "Ocimum sanctum"),
    ("ING-GUGGULU", "Commiphora wightii"),
    ("ING-NEEM", "Azadirachta indica"),
    ("ING-SHATAVARI", "Asparagus racemosus"),
    ("ING-SARPAGANDHA", "Rauvolfia serpentina"),
]

# Marker compounds the curated corpus already names in its evidence text.
TARGET_COMPOUNDS: list[str] = [
    "curcumin",
    "withaferin A",
    "withanolide D",
    "ursolic acid",
    "eugenol",
    "rutin",
    "azadirachtin",
    "guggulsterone",
    "boswellic acid",
    "berberine",
]

TARGET_GENES: list[tuple[str, str]] = [
    ("NFE2L2", "NFE2L2"),
    ("PTGS2", "PTGS2"),
    ("ALOX5", "ALOX5"),
    ("CAT", "CAT"),
    ("SOD1", "SOD1"),
    ("NRF1", "NRF1"),
]


def _http_json(url: str, timeout: int = 15) -> Any | None:
    """GET a JSON document, or return None on any failure."""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _doc(
    doc_id: str,
    title: str,
    content: str,
    *,
    category: str,
    source: str,
    source_url: str,
    authority: str,
    authority_level: int,
    **extra: Any,
) -> dict[str, Any]:
    doc = {
        "content": content,
        "source": source,
        "category": category,
        "chunk_index": 0,
        "doc_id": doc_id,
        "title": title,
        "authority": authority,
        "jurisdiction": "International",
        "authority_level": authority_level,
        "authority_rank": 2,
        "source_url": source_url,
        "effective_date": "",
        "section_heading": category,
        "patent_number": "",
        "publication_year": 0,
    }
    doc.update(extra)
    return doc


# ---------------------------------------------------------------------------
# GBIF - plant nomenclature
# ---------------------------------------------------------------------------

def harvest_gbif_taxonomy(limit: int = 9, timeout: int = 15) -> list[dict[str, Any]]:
    """Authoritative plant nomenclature for TARGET_PLANTS via the GBIF API."""
    docs: list[dict[str, Any]] = []
    for canonical_id, name in TARGET_PLANTS[:limit]:
        qs = urllib.parse.urlencode({"name": name, "verbose": "true"})
        match = _http_json(f"https://api.gbif.org/v1/species/match?{qs}", timeout)
        if not match or "usageKey" not in match:
            continue
        key = match["usageKey"]
        detail = _http_json(f"https://api.gbif.org/v1/species/{key}", timeout) or {}
        synonyms = _http_json(f"https://api.gbif.org/v1/species/{key}/synonyms?limit=25", timeout) or {}

        accepted = (
            detail.get("scientificName")
            or match.get("scientificName")
            or name
        )
        family = detail.get("family", "")
        status = match.get("status", "")
        syn_names = [
            r.get("scientificName", "")
            for r in synonyms.get("results", [])
            if r.get("scientificName") and r.get("scientificName") != accepted
        ][:15]

        lines = [
            f"GBIF taxon {key} ({accepted}) is the {status.lower() or 'matched'} "
            f"backbone record for {name}.",
            f"Family: {family or 'unresolved'}.",
            f"Match confidence: {match.get('confidence', 'n/a')}.",
            f"Kingdom: {detail.get('kingdom', '')}; "
            f"genus: {detail.get('genus', '')}; "
            f"species: {detail.get('species', '')}.",
        ]
        if syn_names:
            lines.append("Accepted synonyms in the GBIF backbone: " + "; ".join(syn_names) + ".")

        docs.append(_doc(
            f"GBIF-TAXON-{key}",
            f"GBIF nomenclature: {accepted}",
            " ".join(lines),
            category="botanical_taxonomy",
            source=f"external/gbif/taxonomy/{key}.json",
            source_url=f"https://www.gbif.org/species/{key}",
            authority="GBIF Backbone Taxonomy",
            authority_level=5,
            omics_type="taxonomy",
            organism="Plantae",
            canonical_id=canonical_id,
            botanical_name=accepted,
            gbif_usage_key=str(key),
            gbif_family=family,
            gbif_status=status,
            gbif_confidence=match.get("confidence"),
            gbif_synonyms=syn_names,
        ))
    return docs


# ---------------------------------------------------------------------------
# PubChem - compound identifiers
# ---------------------------------------------------------------------------

PUBCHEM_PROPERTIES = (
    "MolecularFormula,MolecularWeight,InChIKey,CanonicalSMILES,IsomericSMILES,IUPACName"
)


def _pubchem_cid(compound: str, timeout: int) -> int | None:
    data = _http_json(
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{urllib.parse.quote(compound)}/cids/JSON",
        timeout,
    )
    cids = (data or {}).get("IdentifierList", {}).get("CID") or []
    return cids[0] if cids else None


def harvest_pubchem_compounds(limit: int = 10, timeout: int = 15) -> list[dict[str, Any]]:
    """Canonical compound identifiers for TARGET_COMPOUNDS via PubChem PUG-REST."""
    docs: list[dict[str, Any]] = []
    for compound in TARGET_COMPOUNDS[:limit]:
        cid = _pubchem_cid(compound, timeout)
        if cid is None:
            continue
        # Property names are a path segment, not a query parameter.
        data = _http_json(
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
            f"{cid}/property/{PUBCHEM_PROPERTIES}/JSON",
            timeout,
        )
        props = ((data or {}).get("PropertyTable", {}).get("Properties") or [{}])[0]
        if not props:
            continue

        # PubChem renamed the SMILES properties; accept either generation.
        canonical = props.get("CanonicalSMILES") or props.get("SMILES") or ""
        isomeric = props.get("IsomericSMILES") or props.get("SMILES") or ""
        smiles = isomeric or canonical

        content = (
            f"PubChem CID {cid} is the deposited record for {compound}. "
            f"Molecular formula {props.get('MolecularFormula', 'n/a')}, "
            f"molecular weight {props.get('MolecularWeight', 'n/a')} Da. "
            f"InChIKey {props.get('InChIKey', 'n/a')}."
        )
        iupac = props.get("IUPACName") or ""
        if iupac:
            content += f" Preferred IUPAC name: {iupac}."
        if smiles:
            content += f" Isomeric SMILES: {smiles}."

        docs.append(_doc(
            f"PUBCHEM-CID-{cid}",
            f"PubChem compound: {compound} (CID {cid})",
            content,
            category="compound_identity",
            source=f"external/pubchem/compounds/{cid}.json",
            source_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
            authority="PubChem",
            authority_level=5,
            omics_type="metabolomics",
            compound=compound,
            pubchem_cid=str(cid),
            molecular_formula=props.get("MolecularFormula", ""),
            molecular_weight=props.get("MolecularWeight", ""),
            inchi_key=props.get("InChIKey", ""),
            canonical_smiles=canonical,
            isomeric_smiles=isomeric,
            iupac_name=iupac,
        ))
    return docs


# ---------------------------------------------------------------------------
# UniProt - protein entries
# ---------------------------------------------------------------------------

def harvest_uniprot_entries(limit: int = 8, timeout: int = 20) -> list[dict[str, Any]]:
    """Reviewed human entries relevant to the curated mechanism claims.

    One exact gene-at-a-time query rather than a single OR expression: an OR
    expression also matched unrelated entries, which then showed up as records
    for a mechanism the corpus never claimed.
    """
    wanted = [sym for sym, _ in TARGET_GENES]
    found: dict[str, dict[str, Any]] = {}
    for symbol in wanted:
        query = f'gene_exact:{symbol} AND organism_id:9606 AND reviewed:true'
        qs = urllib.parse.urlencode(
            {
                "query": query,
                "format": "json",
                "size": "1",
                "fields": "accession,id,protein_name,gene_names,organism_name,cc_function",
            }
        )
        data = _http_json(f"https://rest.uniprot.org/uniprotkb/search?{qs}", timeout)
        for entry in (data or {}).get("results", []):
            if entry.get("primaryAccession"):
                found[symbol] = entry
                break

    docs: list[dict[str, Any]] = []
    for symbol, entry in list(found.items())[:limit]:
        acc = entry.get("primaryAccession", "")
        protein = ((entry.get("proteinDescription") or {}).get("recommendedName") or {}).get(
            "fullName", {}
        ).get("value", "")
        genes = [g.get("geneName", {}).get("value", "") for g in entry.get("genes", [])]
        genes = [g for g in genes if g]
        comments = [
            c.get("texts", [{}])[0].get("value", "")
            for c in entry.get("comments", [])
            if c.get("commentType") == "FUNCTION"
        ]
        function = next((c for c in comments if c), "")

        content = (
            f"UniProtKB reviewed entry {acc} ({entry.get('uniProtkbId', acc)}) for "
            f"{entry.get('organism', {}).get('scientificName', 'Homo sapiens')}."
        )
        if protein:
            content += f" Protein name: {protein}."
        if genes:
            content += f" Gene: {', '.join(genes)}."
        if function:
            content += f" FUNCTION: {function[:600]}"

        docs.append(_doc(
            f"UNIPROT-{acc}",
            f"UniProtKB: {protein or acc}",
            content,
            category="protein_function",
            source=f"external/uniprot/entries/{acc}.json",
            source_url=f"https://www.uniprot.org/uniprotkb/{acc}",
            authority="UniProtKB",
            authority_level=5,
            omics_type="proteomics",
            organism=entry.get("organism", {}).get("scientificName", ""),
            protein=protein,
            gene="; ".join(genes) or symbol,
            uniprot_accession=acc,
        ))
    return docs


# ---------------------------------------------------------------------------
# NCBI E-utilities - gene records
# ---------------------------------------------------------------------------

def harvest_ncbi_genes(limit: int = 6, timeout: int = 20) -> list[dict[str, Any]]:
    """Gene summaries for TARGET_GENES via esearch + esummary."""
    ids: list[tuple[str, str]] = []
    for symbol, query_term in TARGET_GENES:
        qs = urllib.parse.urlencode(
            {"db": "gene", "term": f"{query_term}[sym] AND human[orgn]", "retmode": "json"}
        )
        data = _http_json(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{qs}", timeout)
        found = ((data or {}).get("esearchresult") or {}).get("idlist") or []
        if found:
            ids.append((symbol, found[0]))
        if len(ids) >= limit:
            break
    if not ids:
        return []

    qs = urllib.parse.urlencode(
        {"db": "gene", "id": ",".join(g for _, g in ids), "retmode": "json"}
    )
    data = _http_json(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{qs}", timeout)
    result = (data or {}).get("result", {})

    docs: list[dict[str, Any]] = []
    for symbol, gene_id in ids:
        rec = result.get(gene_id) or {}
        if not rec:
            continue
        summary = rec.get("summary", "")
        content = (
            f"NCBI Gene {gene_id} ({rec.get('name', symbol)}) is the human gene record "
            f"for {symbol}. Official symbol: {rec.get('description', symbol)}."
        )
        if summary:
            content += f" Summary: {summary[:600]}"
        raw_map = rec.get("maplocation")
        if isinstance(raw_map, str):
            maps = [raw_map]
        else:
            maps = [
                m.get("display_str", "")
                for m in (raw_map or [])
                if isinstance(m, dict)
            ]
        maps = [m for m in maps if m]
        if maps:
            content += f" Map location: {', '.join(maps)}."

        docs.append(_doc(
            f"NCBI-GENE-{gene_id}",
            f"NCBI Gene: {symbol} ({gene_id})",
            content,
            category="gene_record",
            source=f"external/ncbi_gene/genes/{gene_id}.json",
            source_url=f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}",
            authority="NCBI Gene",
            authority_level=5,
            omics_type="genomics",
            organism="Homo sapiens",
            gene=rec.get("name", symbol),
            ncbi_gene_id=gene_id,
        ))
    return docs


# ---------------------------------------------------------------------------
# Snapshot replay
# ---------------------------------------------------------------------------

def snapshot_manifest() -> dict[str, Any] | None:
    path = os.path.join(SNAPSHOT_DIR, "provenance.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def load_external_snapshot() -> list[dict[str, Any]]:
    """Replay the committed snapshot. Returns [] when no snapshot is present."""
    manifest = snapshot_manifest()
    if not manifest:
        return []
    docs: list[dict[str, Any]] = []
    for entry in manifest.get("datasets", []):
        rel = entry.get("file", "")
        if not rel:
            continue
        path = os.path.join(SNAPSHOT_DIR, rel.replace("/", os.sep))
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:
            continue
        for doc in payload.get("documents", []):
            doc.setdefault("external_source", entry.get("source", ""))
            doc.setdefault("external_retrieved", manifest.get("retrieved_at", ""))
            doc.setdefault("external_license", entry.get("license", ""))
            docs.append(doc)
    return docs


def external_status() -> dict[str, Any]:
    """Provenance summary for the admin/status surface."""
    manifest = snapshot_manifest()
    if not manifest:
        return {
            "snapshot_present": False,
            "datasets": [],
            "unavailable_sources": UNAVAILABLE_SOURCES,
        }
    return {
        "snapshot_present": True,
        "retrieved_at": manifest.get("retrieved_at"),
        "corpus_version": manifest.get("corpus_version"),
        "datasets": [
            {
                "source": d.get("source"),
                "records": d.get("records"),
                "license": d.get("license"),
                "sha256": d.get("sha256"),
            }
            for d in manifest.get("datasets", [])
        ],
        "unavailable_sources": UNAVAILABLE_SOURCES,
    }
