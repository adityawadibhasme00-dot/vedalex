# IP-SAKTI Knowledge Base (kb/)

This folder is the grounding source for the IP-SAKTI RAG engine. The AI Copilot and the
Innovation Passport answer ONLY from content in here (and the packaged backend `data/`
sources). Nothing is generated from memory, which is what prevents hallucination.

## How to add knowledge

Drop plain-text files (`.txt`, `.md`, `.json`) or PDFs (`.pdf`) into the matching folder.
After adding files, rebuild the vector index:

- Via API: `POST http://localhost:8000/api/v1/admin/reindex` with body
  `{"api_key": "ipsakti_secure_production_secret_key_2026"}`  (see backend `app/core/config.py`)
- Via script (from `backend/`): `venv\Scripts\python scripts\build_faiss.py`

Check status: `GET http://localhost:8000/api/v1/admin/status`

## Folder map

| Folder          | Put here                                                       |
|-----------------|----------------------------------------------------------------|
| `tkdl/`         | TKDL (Traditional Knowledge Digital Library) dumps / export PDFs, formatted prior-art text |
| `wipo/`         | WIPO patentscope dumps, WIPO Medicinal Plants reports, treaty PDFs |
| `regulations/`  | CDSCO, Drugs & Cosmetics Act, Schedule T, FSSAI 2022, US DSHEA / FD&C, Canada NHPR, EU herbal guidance |
| `patents/`      | Section 3/3(p) analysis, CNIPA/USPTO/EPO patent landscape text, TKDL defensive protection notes |
| `ayurveda/`     | Classical texts (Charaka Samhita, Sushruta, Ashtanga Hridaya) excerpts, rasa/guna/virya data |
| `pharmacopoeia/`| Ayurvedic Pharmacopoeia of India (API) monographs, standards, API quality data |
| `pubmed/`       | Peer-reviewed study abstracts / clinical evidence summaries |
| `who/`          | WHO Traditional Medicine Strategy 2014-2023, WHO herbal guidance |
| `metadata/`     | Source citation index, authority lists, glossary |
| `images/`       | Herb / formulation images (PNG/JPG/SVG) - shown by the Copilot when relevant |
| `links/`        | `resources.json` - JSON array of reference URL strings (TKDL, WIPO, ipindia, etc.) |

## Rules

1. **Text must be readable** - PDFs are auto-extracted at index time, but text files are safer.
2. **Keep each source verifiable** - the `source` field records the file path of every chunk.
3. **Re-index after every change** - otherwise the Copilot keeps serving the old snapshot.