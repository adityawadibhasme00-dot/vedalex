"""Write all curated multi-omics seed records into data/multiomics/ as .txt files."""
import os, sys, textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.rag.datasources.seed.curated import (
    build_omics_seed_documents, PROTEOMICS, METABOLOMICS, PHARMACOGENOMICS, PATHWAYS,
)

BASE = os.path.join(os.path.dirname(__file__), "..", "data", "multiomics")

def write_records(records, folder_name):
    out_dir = os.path.join(BASE, folder_name)
    os.makedirs(out_dir, exist_ok=True)
    for i, rec in enumerate(records, 1):
        fname = f"{folder_name}_{i:02d}.txt"
        lines = [
            f"DOC_ID: {rec.get('doc_id', '')}",
            f"TITLE: {rec.get('title', '')}",
            f"OMICS_TYPE: {rec.get('omics_type', '')}",
            f"ORGANISM: {rec.get('organism', '')}",
            f"COMPOUND: {rec.get('compound', '')}",
            f"GENE: {rec.get('gene', '')}",
            f"PROTEIN: {rec.get('protein', '')}",
            f"UNIPROT: {rec.get('uniprot_accession', '')}",
            f"NCBI_GENE_ID: {rec.get('ncbi_gene_id', '')}",
            f"PUBCHEM_CID: {rec.get('pubchem_cid', '')}",
            f"PATHWAY: {rec.get('pathway', '')}",
            f"ASSAY_TYPE: {rec.get('assay_type', '')}",
            f"PMID: {rec.get('pmid', '')}",
            f"SOURCE_URL: {rec.get('source_url', '')}",
            f"AUTHORITY: {rec.get('authority', '')}",
            f"JURISDICTION: {rec.get('jurisdiction', '')}",
            "",
            rec.get("content", ""),
        ]
        path = os.path.join(out_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    print(f"  {folder_name}: {len(records)} files written")

def main():
    for name, records in [
        ("proteomics", PROTEOMICS),
        ("metabolomics", METABOLOMICS),
        ("pharmacogenomics", PHARMACOGENOMICS),
        ("pathway", PATHWAYS),
    ]:
        write_records(records, name)
    total = len(build_omics_seed_documents())
    print(f"\nTotal multi-omics files: {total}")
    print("DONE")

if __name__ == "__main__":
    main()
