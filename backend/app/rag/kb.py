import os
import json
import re
import glob
from typing import List, Dict, Any, Optional, Tuple

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

KB_SUBFOLDERS = [
    "tkdl",
    "wipo",
    "regulations",
    "patents",
    "ayurveda",
    "pharmacopoeia",
    "pubmed",
    "who",
    "metadata",
    "images",
    "links",
    "official",
]

# Default source authority metadata derived from the knowledge folder.
# authority_level mirrors authority_rank (1 = Act/Gazette ... 5 = Academic/Secondary)
FOLDER_SOURCE_META: Dict[str, Dict[str, Any]] = {
    "patents":       {"authority": "Indian Patent Office (CGPDTM)", "jurisdiction": "India", "authority_level": 1,
                      "category": "patent statute"},
    "regulations":   {"authority": "Indian Regulatory Authority (CDSCO / FSSAI)", "jurisdiction": "India", "authority_level": 2,
                      "category": "regulatory"},
    "pharmacopoeia": {"authority": "Ayurvedic Pharmacopoeia of India (PCIM&H)", "jurisdiction": "India", "authority_level": 2,
                      "category": "pharmacopoeia"},
    "tkdl":          {"authority": "CSIR-TKDL / Ministry of AYUSH", "jurisdiction": "India", "authority_level": 2,
                      "category": "tkdl"},
    "wipo":          {"authority": "WIPO", "jurisdiction": "International", "authority_level": 3,
                      "category": "international ip"},
    "who":           {"authority": "World Health Organization (WHO)", "jurisdiction": "International", "authority_level": 3,
                      "category": "who"},
    "ayurveda":      {"authority": "Classical Ayurveda Texts (NCISM curriculum)", "jurisdiction": "India", "authority_level": 4,
                      "category": "classical texts"},
    "pubmed":        {"authority": "PubMed / NCBI", "jurisdiction": "International", "authority_level": 5,
                      "category": "academic research"},
    "metadata":      {"authority": "Source Registry", "jurisdiction": "International", "authority_level": 5,
                      "category": "metadata"},
    "official":      {"authority": "Official Source", "jurisdiction": "", "authority_level": 2,
                      "category": "official"},
    "images":        {"authority": "Knowledge Base Images", "jurisdiction": "", "authority_level": 5,
                      "category": "images"},
    "links":         {"authority": "Reference Link Registry", "jurisdiction": "", "authority_level": 5,
                      "category": "links"},
    "multiomics":    {"authority": "NCBI Gene / UniProt / PubChem / PharmGKB", "jurisdiction": "International", "authority_level": 5,
                      "category": "multiomics"},
}


def kb_root() -> str:
    return os.path.abspath(os.environ.get("IP-SAKTI_KB_ROOT", os.path.join(BACKEND_ROOT, "..", "kb")))


def official_dir() -> str:
    return os.environ.get("IPSAKTI_OFFICIAL_DIR", os.path.join(BACKEND_ROOT, "data", "official"))


def blueprint_path() -> str:
    env_path = os.environ.get("IPSAKTI_BLUEPRINT_XLSX", "")
    if env_path and os.path.exists(env_path):
        return os.path.abspath(env_path)
    candidate = os.path.join(BACKEND_ROOT, "data", "blueprint.xlsx")
    return candidate if os.path.exists(candidate) else ""


def ensure_kb_layout() -> str:
    root = kb_root()
    for sub in KB_SUBFOLDERS:
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    return root


def _flatten_json_text(content: str) -> str:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return content

    parts: List[str] = []
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                parts.append(str(k))
                if isinstance(v, (dict, list)):
                    stack.append(v)
                else:
                    parts.append(str(v))
        elif isinstance(node, list):
            for v in node:
                if isinstance(v, (dict, list)):
                    stack.append(v)
                else:
                    parts.append(str(v))
    return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Front-matter style metadata parsing. Official corpus .txt files may begin with
# TITLE: / AUTHORITY: / JURISDICTION: / SOURCE: / EFFECTIVE: / SUBSECTION:
# lines. Anything following a "Sources:" / "Source:" line is captured as the
# canonical citation URL for every chunk of that file.
# ---------------------------------------------------------------------------
_META_KEYS = {
    "title": "title",
    "authority": "authority",
    "jurisdiction": "jurisdiction",
    "source": "source_url",
    "effective": "effective_date",
    "subsection": "section_heading",
}


def _parse_metadata_headers(content: str) -> Tuple[Dict[str, str], str]:
    meta: Dict[str, str] = {}
    lines = content.splitlines()
    body_lines: List[str] = []
    consumed = 0
    for i, line in enumerate(lines[:25]):
        low = line.strip().lower()
        if ":" in low:
            key, _, val = line.partition(":")
            key_norm = key.strip().lower().rstrip("s")
            if key_norm in _META_KEYS and val.strip():
                meta[_META_KEYS[key_norm]] = val.strip()
                consumed = i + 1
                continue
        elif not line.strip():
            consumed = i + 1
            continue
        break
    body_lines = lines[consumed:]
    return meta, "\n".join(body_lines).strip()


def _looks_like_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 100:
        return False
    if re.match(r"^(\d+\.|\([ivxlcdm]+\)|[A-Z]{2,}\b)", s):
        return True
    if "\t" not in s and "  " not in s and len(s) < 60 and not s.endswith((".", ":", ";")):
        return True
    return False


def _structure_chunks(text: str, chunk_size: int = 700, overlap: int = 120) -> List[Dict[str, str]]:
    """Section-aware chunking.

    Splits on blank lines, keeps short heading-like lines attached to the chunk
    that follows, and emits each chunk with a section_heading when available.
    """
    chunks: List[Dict[str, str]] = []
    current: List[str] = []
    current_heading: str = ""
    current_words = 0

    def flush():
        nonlocal current, current_heading, current_words
        body = " ".join(current).strip()
        if body:
            text = body if not current_heading else f"{current_heading}\n{body}"
            chunks.append({"content": text, "section_heading": current_heading})
        current = []
        current_heading = ""
        current_words = 0

    for block in re.split(r"\n\s*\n", text):
        lines = block.splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if _looks_like_heading(line) and current_words > 40:
                flush()
                current_heading = stripped
                current = []
                current_words = 0
                continue
            current.append(stripped)
            current_words += len(line.split())
            if current_words >= chunk_size:
                prev_body = current
                # keep a small tail for overlap across the boundary
                keep = " ".join(prev_body[-int(overlap):])
                flush()
                if keep:
                    current = keep.split()
                    current_words = len(current)
    flush()
    return chunks or [{"content": text[:2000], "section_heading": ""}]


def _chunk_text(content: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    words = content.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


# ---------------------------------------------------------------------------
# Patent-Specific Intelligent Chunking Rules
# ---------------------------------------------------------------------------
# Official data sources require section-aware chunking:
#   - Patent Title -> one chunk (metadata-rich)
#   - Abstract -> one chunk
#   - Claims -> ONE claim per chunk (critical for prior-art analysis)
#   - Detailed Description -> overlapping window chunks
#   - AYUSH guideline sections -> per-section chunks
#   - API chapters -> per-chapter chunks
# ---------------------------------------------------------------------------

_PATENT_SECTION_PATTERNS = [
    (r"(?:^|\n)\s*(?:TITLE|TITLE OF THE INVENTION)\s*[:\n]", "patent_title"),
    (r"(?:^|\n)\s*(?:ABSTRACT|ABSTRACT OF THE DISCLOSURE)\s*[:\n]", "patent_abstract"),
    (r"(?:^|\n)\s*(?:CLAIMS?|WHAT IS CLAIMED|WE CLAIM|I CLAIM)\s*[:\n]", "patent_claims_header"),
    (r"(?:^|\n)\s*(?:FIELD OF THE INVENTION|FIELD OF INVENTION)\s*[:\n]", "patent_field"),
    (r"(?:^|\n)\s*(?:BACKGROUND|PRIOR ART|DESCRIPTION OF THE RELATED ART)\s*[:\n]", "patent_background"),
    (r"(?:^|\n)\s*(?:DETAILED DESCRIPTION|DESCRIPTION OF PREFERRED EMBODIMENTS?)\s*[:\n]", "patent_description"),
    (r"(?:^|\n)\s*(?:DRAWINGS?|BRIEF DESCRIPTION OF DRAWINGS?)\s*[:\n]", "patent_drawings"),
]

_CLAIM_SPLIT_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:\d+[\.\)]\s*|Claim\s+\d+[\.\:]\s*)",
    re.MULTILINE,
)

_REGULATORY_SECTION_PATTERNS = [
    (r"(?:^|\n)\s*(?:SECTION\s+\d+|Section\s+\d+)\s*[:\-]", "regulatory_section"),
    (r"(?:^|\n)\s*(?:CHAPTER\s+\d+|Chapter\s+\d+)\s*[:\-]", "regulatory_chapter"),
    (r"(?:^|\n)\s*(?:SCHEDULE\s+[IVXLC]+|Schedule\s+\d+)\s*[:\-]", "regulatory_schedule"),
    (r"(?:^|\n)\s*(?:GUIDELINE|REGULATION|NOTIFICATION|ORDER)\s*[:\-]", "regulatory_guideline"),
]

_API_SECTION_PATTERNS = [
    (r"(?:^|\n)\s*(?:MONOGRAPH|PHARMACOPOEIA)\s+[:\-]", "api_monograph"),
    (r"(?:^|\n)\s*(?:IDENTITY AND PURITY|IDENTITY & PURITY)", "api_identity"),
    (r"(?:^|\n)\s*(?:CHARACTERS|DESCRIPTION)", "api_characters"),
    (r"(?:^|\n)\s*(?:TESTS|TEST FOR)", "api_tests"),
    (r"(?:^|\n)\s*(?:STORAGE|STORAGE CONDITIONS)", "api_storage"),
    (r"(?:^|\n)\s*(?:ACTION|PHARMACOLOGICAL ACTION)", "api_action"),
    (r"(?:^|\n)\s*(?:USES?|THERAPEUTIC USES?)", "api_uses"),
    (r"(?:^|\n)\s*(?:DOSAGE|DOSAGE FORMS?)", "api_dosage"),
]


def _detect_document_type(content: str, filepath: str) -> str:
    """Detect whether content is a patent, regulatory document, or API monograph."""
    lower_content = content[:3000].lower()
    path_lower = filepath.lower()

    if any(k in lower_content for k in ["claim 1.", "claim 1:", "what is claimed", "we claim"]):
        return "patent"
    if any(k in path_lower for k in ["patent", "inpass", "patentscope"]):
        return "patent"
    if any(k in lower_content for k in ["section 3(p)", "patents act", "regulation", "notification"]):
        return "regulatory"
    if any(k in path_lower for k in ["pharmacopoeia", "api_", "monograph"]):
        return "api"
    if any(k in lower_content for k in ["guideline", "schedule t", "cdsco", "fssai"]):
        return "regulatory"
    return "general"


def _extract_patent_number(content: str) -> str:
    """Extract patent number from document content."""
    patterns = [
        r"(?:Patent\s+(?:No|Number|#|Application\s+No)[.\:]\s*)([A-Z]{2}[-/]?\d{4,}[-/]?\d{0,6})",
        r"(?:Application\s+No[.\:]\s*)(\d{4,}[-/]?\d{0,6})",
        r"(?: Publication\s+No[.\:]\s*)([A-Z]{2}[-/]?\d{4,}[-/]?\d{0,6})",
        r"\b(IN|US|WO|EP|JP|CN|KR|CA|AU)-?\d{4,}[-/]?\d{0,6}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1) if match.lastindex else match.group(0)
    return ""


def _extract_publication_year(content: str) -> int:
    """Extract publication year from document content."""
    patterns = [
        r"(?:Publication\s+Date|Published|Filing\s+Date|Date\s+of\s+Publication)[.\:]\s*\d{4}",
        r"\b(19|20)\d{2}\b",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            for m in matches:
                year = int(m[:4]) if len(m) == 4 else int(m)
                if 1970 <= year <= 2030:
                    return year
    return 0


def _chunk_patent_document(content: str) -> List[Dict[str, str]]:
    """
    Patent-specific chunking:
    - Title: one chunk
    - Abstract: one chunk
    - Claims: ONE claim per chunk (critical for prior-art matching)
    - Description: overlapping window chunks (700 words, 120 overlap)
    """
    chunks: List[Dict[str, str]] = []
    patent_num = _extract_patent_number(content)
    pub_year = _extract_publication_year(content)

    # Try to split by major sections
    sections = _split_by_section_headers(content, _PATENT_SECTION_PATTERNS)

    if not sections:
        # Fallback: treat entire content as description
        text_chunks = _structure_chunks(content, chunk_size=700, overlap=120)
        for tc in text_chunks:
            chunks.append({
                "content": tc["content"],
                "section_heading": "Description",
                "patent_number": patent_num,
                "publication_year": pub_year,
            })
        return chunks

    for section_type, section_text in sections:
        if section_type == "patent_claims_header":
            # Split into individual claims
            claims = _split_individual_claims(section_text)
            for i, claim in enumerate(claims, 1):
                chunks.append({
                    "content": claim,
                    "section_heading": f"Claim {i}",
                    "patent_number": patent_num,
                    "publication_year": pub_year,
                })
        elif section_type in ("patent_title", "patent_abstract"):
            # Single chunk for title/abstract
            chunks.append({
                "content": section_text.strip()[:2000],
                "section_heading": section_type.replace("patent_", "").title(),
                "patent_number": patent_num,
                "publication_year": pub_year,
            })
        else:
            # Overlapping window chunks for description/field/background
            text_chunks = _structure_chunks(section_text, chunk_size=700, overlap=120)
            heading = section_type.replace("patent_", "").title()
            for tc in text_chunks:
                chunks.append({
                    "content": tc["content"],
                    "section_heading": heading,
                    "patent_number": patent_num,
                    "publication_year": pub_year,
                })

    return chunks


def _chunk_regulatory_document(content: str) -> List[Dict[str, str]]:
    """Regulatory document chunking: per-section with overlap."""
    chunks: List[Dict[str, str]] = []
    sections = _split_by_section_headers(content, _REGULATORY_SECTION_PATTERNS)

    if not sections:
        text_chunks = _structure_chunks(content, chunk_size=700, overlap=120)
        for tc in text_chunks:
            chunks.append({
                "content": tc["content"],
                "section_heading": "Regulatory Text",
            })
        return chunks

    for section_type, section_text in sections:
        heading = section_type.replace("regulatory_", "").title()
        text_chunks = _structure_chunks(section_text, chunk_size=700, overlap=120)
        for tc in text_chunks:
            chunks.append({
                "content": tc["content"],
                "section_heading": heading,
            })

    return chunks


def _chunk_api_document(content: str) -> List[Dict[str, str]]:
    """API (Ayurvedic Pharmacopoeia) monograph chunking."""
    chunks: List[Dict[str, str]] = []
    sections = _split_by_section_headers(content, _API_SECTION_PATTERNS)

    if not sections:
        text_chunks = _structure_chunks(content, chunk_size=500, overlap=100)
        for tc in text_chunks:
            chunks.append({
                "content": tc["content"],
                "section_heading": "API Monograph",
            })
        return chunks

    for section_type, section_text in sections:
        heading = section_type.replace("api_", "").title()
        text_chunks = _structure_chunks(section_text, chunk_size=500, overlap=100)
        for tc in text_chunks:
            chunks.append({
                "content": tc["content"],
                "section_heading": heading,
            })

    return chunks


def _split_by_section_headers(
    content: str,
    patterns: List[tuple],
) -> List[Tuple[str, str]]:
    """Split content by detected section headers."""
    # Find all section boundaries
    boundaries = []
    for pattern, section_type in patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            boundaries.append((match.start(), section_type))

    if not boundaries:
        return []

    boundaries.sort(key=lambda x: x[0])

    sections = []
    for i, (start, section_type) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(content)
        section_text = content[start:end].strip()
        if section_text:
            sections.append((section_type, section_text))

    return sections


def _split_individual_claims(text: str) -> List[str]:
    """Split patent claims into individual claim chunks."""
    # Remove the header
    header_match = re.search(
        r"(?:CLAIMS?|WHAT IS CLAIMED|WE CLAIM|I CLAIM)\s*[:\n]",
        text, re.IGNORECASE,
    )
    if header_match:
        text = text[header_match.end():]

    # Split on claim numbers
    claim_parts = _CLAIM_SPLIT_PATTERN.split(text)
    claims = []
    for part in claim_parts:
        cleaned = part.strip()
        if cleaned and len(cleaned.split()) >= 5:  # Minimum 5 words for a valid claim
            claims.append(cleaned)

    # If no claims found, return the whole text as one claim
    if not claims and text.strip():
        claims = [text.strip()]

    return claims


def _add_doc_metadata(doc: Dict[str, Any], filepath: str, category: str, file_meta: Dict[str, str], chunk: Dict[str, str], index: int) -> Dict[str, Any]:
    stem = os.path.splitext(os.path.basename(filepath))[0]
    folder_defaults = FOLDER_SOURCE_META.get(category, {})
    relpath = os.path.relpath(filepath, BACKEND_ROOT).replace(os.sep, "/")
    doc_id = file_meta.get("doc_id", "") or f"{stem.upper()}-C{index:03d}"
    authority = file_meta.get("authority") or folder_defaults.get("authority", "Official Source")
    jurisdiction = file_meta.get("jurisdiction") or folder_defaults.get("jurisdiction", "")
    authority_level = int(file_meta.get("authority_level") or folder_defaults.get("authority_level", 3))
    source_url = file_meta.get("source_url") or ""
    effective = file_meta.get("effective_date") or ""
    section = chunk.get("section_heading") or file_meta.get("section_heading") or ""

    return {
        "content": chunk["content"],
        "source": relpath,
        "category": category,
        "chunk_index": index,
        "doc_id": doc_id,
        "title": file_meta.get("title") or stem,
        "authority": authority,
        "jurisdiction": jurisdiction,
        "authority_level": authority_level,
        "source_url": source_url,
        "effective_date": effective,
        "section_heading": section,
        "patent_number": chunk.get("patent_number", ""),
        "publication_year": int(chunk.get("publication_year", 0)) if chunk.get("publication_year") else 0,
    }


def load_documents_from_dir(base_dir: str, source_category: str, recursive: bool = True) -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    if not os.path.isdir(base_dir):
        return documents

    patterns = ["*.txt", "*.md", "*.json"]
    for ext in patterns:
        matches = sorted(glob.glob(os.path.join(base_dir, "**", ext), recursive=recursive))
        matches += [m for m in sorted(glob.glob(os.path.join(base_dir, ext))) if m not in matches]
        for filepath in matches:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if ext == "*.json":
                    content = _flatten_json_text(content)
                file_meta, body = _parse_metadata_headers(content)
                if not body.strip():
                    continue

                # Patent-specific chunking for patent documents
                if source_category == "patents":
                    doc_type = _detect_document_type(body, filepath)
                    if doc_type == "patent":
                        chunks = _chunk_patent_document(body)
                    else:
                        chunks = _structure_chunks(body)
                elif source_category in ("regulations", "official"):
                    doc_type = _detect_document_type(body, filepath)
                    if doc_type == "regulatory":
                        chunks = _chunk_regulatory_document(body)
                    else:
                        chunks = _structure_chunks(body)
                elif source_category == "pharmacopoeia":
                    doc_type = _detect_document_type(body, filepath)
                    if doc_type == "api":
                        chunks = _chunk_api_document(body)
                    else:
                        chunks = _structure_chunks(body)
                elif source_category in ("metadata", "images", "links"):
                    chunks = [{"content": body, "section_heading": ""}]
                else:
                    chunks = _structure_chunks(body)

                for i, chunk in enumerate(chunks):
                    documents.append(_add_doc_metadata({"content": chunk["content"]}, filepath, source_category, file_meta, chunk, i))
            except Exception as e:
                print(f"Error loading {filepath}: {e}")

    return documents


def load_pdfs_from_dir(base_dir: str, source_category: str, recursive: bool = True) -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    try:
        import fitz
    except Exception:
        return documents

    matches = sorted(glob.glob(os.path.join(base_dir, "**", "*.pdf"), recursive=recursive))
    for filepath in matches:
        try:
            with fitz.open(filepath) as pdf:
                content = " ".join(page.get_text() for page in pdf)
            if content.strip():
                # Patent-specific chunking for patent PDFs
                if source_category == "patents":
                    doc_type = _detect_document_type(content, filepath)
                    if doc_type == "patent":
                        chunks = _chunk_patent_document(content)
                    else:
                        chunks = _structure_chunks(content)
                elif source_category in ("regulations", "official"):
                    doc_type = _detect_document_type(content, filepath)
                    if doc_type == "regulatory":
                        chunks = _chunk_regulatory_document(content)
                    else:
                        chunks = _structure_chunks(content)
                elif source_category == "pharmacopoeia":
                    doc_type = _detect_document_type(content, filepath)
                    if doc_type == "api":
                        chunks = _chunk_api_document(content)
                    else:
                        chunks = _structure_chunks(content)
                else:
                    chunks = _structure_chunks(content)

                for i, chunk in enumerate(chunks):
                    documents.append(_add_doc_metadata({"content": chunk["content"]}, filepath, source_category, {}, chunk, i))
        except Exception as e:
            print(f"Error loading PDF {filepath}: {e}")
    return documents


def list_reference_links(root: str = None) -> List[Dict[str, str]]:
    root = root or kb_root()
    links_file = os.path.join(root, "links", "resources.json")
    urls = [u for u in (
        "https://tkdl.res.in/tkdl/langdefault/common/Home.asp",
        "https://ipindia.gov.in/",
        "https://www.wipo.int/",
        "https://dgft.gov.in/",
        "https://www.fda.gov/",
        "https://www.who.int/",
    ) if u.startswith("http")]
    if os.path.exists(links_file):
        try:
            with open(links_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                urls = [str(item) for item in data]
        except Exception:
            pass
    return [{"url": u} for u in urls]


def collect_knowledge_documents(root: str = None) -> List[Dict[str, Any]]:
    root = root or kb_root()
    ensure_kb_layout()

    all_documents: List[Dict[str, Any]] = []

    data_base = os.path.join(BACKEND_ROOT, "data")
    for sub in ["pharmacopoeia", "ayurveda", "regulations", "patents", "pubmed", "who", "metadata", "official"]:
        all_documents.extend(load_documents_from_dir(os.path.join(data_base, sub), sub))
        all_documents.extend(load_pdfs_from_dir(os.path.join(data_base, sub), sub))

    for sub in ["tkdl", "wipo", "regulations", "patents", "ayurveda", "pharmacopoeia", "pubmed", "who", "metadata", "official"]:
        all_documents.extend(load_documents_from_dir(os.path.join(root, sub), sub))
        all_documents.extend(load_pdfs_from_dir(os.path.join(root, sub), sub))

    knowledge_dir = os.path.join(BACKEND_ROOT, "app", "knowledge")
    for kfile in ["acts_and_gazettes.json", "api_monographs.json", "botanical_synonyms.json", "permitted_tk_prior_art.json"]:
        abs_path = os.path.join(knowledge_dir, kfile)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    content = _flatten_json_text(f.read())
                if content.strip():
                    stem = os.path.splitext(kfile)[0]
                    all_documents.append({
                        "content": content[:2000],
                        "source": f"app/knowledge/{kfile}",
                        "category": "knowledge",
                        "chunk_index": 0,
                        "doc_id": f"{stem.upper()}-K00",
                        "title": stem,
                        "authority": "Statutory / Canonical Knowledge Base",
                        "jurisdiction": "",
                        "authority_level": 2,
                        "source_url": "",
                        "effective_date": "",
                        "section_heading": "",
                    })
            except Exception as e:
                print(f"Error loading knowledge file {kfile}: {e}")

    # Excel RAG metadata blueprint (13-sheet workbook), if present.
    try:
        from app.rag.xlsx_pipeline import load_blueprint_documents
        all_documents.extend(load_blueprint_documents())
    except Exception as e:
        print(f"(kb) blueprint loader skipped: {e}")

    # Multi-omics evidence suite (proteomics, metabolomics, pharmacogenomics,
    # pathway, transcriptomics/genomics). Curated seed always loads; live
    # API harvest is additive and network-guarded.
    try:
        from app.rag.datasources import harvest_multiomics
        omics_docs = harvest_multiomics(include_live=False)
        all_documents.extend(omics_docs)
        print(f"(kb) multiomics: {len(omics_docs)} curated records loaded")
    except Exception as e:
        print(f"(kb) multiomics skipped: {e}")

    return all_documents


def find_relevant_images(query: str, root: str = None, top_k: int = 3) -> List[str]:
    root = root or kb_root()
    img_dir = os.path.join(root, "images")
    if not os.path.isdir(img_dir):
        return []

    exts = ("*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.svg")
    candidates = []
    for ext in exts:
        candidates.extend(glob.glob(os.path.join(img_dir, "**", ext), recursive=True))

    if not candidates:
        return []

    query_toks = set(query.lower().split())
    scored = []
    for path in candidates:
        stem = os.path.splitext(os.path.basename(path))[0].lower().replace("_", " ").replace("-", " ")
        toks = set(stem.split())
        overlap = len(query_toks.intersection(toks))
        scored.append((overlap, path))

    scored.sort(key=lambda x: x[0], reverse=True)
    matches = [p for s, p in scored if s > 0][:top_k]
    return [f"copilot/media/{os.path.relpath(p, img_dir).replace(os.sep, '/')}" for p in matches] if matches else []