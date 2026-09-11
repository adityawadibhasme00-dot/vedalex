"""
Curated multi-omics evidence seed for Ayurvedic bioactives and targets.

Every identifier below is a real public-database entry:
  - UniProt accession (proteomics)
  - NCBI Gene ID (genomics / transcriptomics)
  - PubChem CID (metabolomics / compound data)
  - PMID (clinical / mechanistic literature, shown only when verified)

These records power the "multiomics" knowledge category so that patentability
assessments can cite mechanistic evidence with deterministic accessions.
"""

from typing import List, Dict, Any

AUTHORITY_MAP = {
    "genomics": "NCBI Gene / NCBI (National Library of Medicine)",
    "transcriptomics": "NCBI GEO / PubMed (National Library of Medicine)",
    "proteomics": "UniProt Consortium (EMBL-EBI / SIB / PIR)",
    "metabolomics": "PubChem (NCBI) / HMDB / MetaboLights (EMBL-EBI)",
    "pharmacogenomics": "PharmGKB (Stanford) / FDA",
    "pathway": "WikiPathways / KEGG (Kyoto Encyclopedia)",
}


def _rec(
    omics_type: str,
    organism: str,
    compound: str,
    title: str,
    content: str,
    *,
    gene: str = "",
    protein: str = "",
    uniprot: str = "",
    ncbi_gene_id: str = "",
    pubchem_cid: str = "",
    pathway: str = "",
    assay_type: str = "",
    pmid: str = "",
    source_url: str = "",
    doc_suffix: str = "A",
) -> Dict[str, Any]:
    authority = AUTHORITY_MAP.get(omics_type, "Official Source")
    doc_id = f"OMICS-{omics_type.upper()}-{doc_suffix}"
    return {
        "content": content,
        "source": f"data/multiomics/{omics_type}/{document_key(omics_type, doc_suffix)}.txt",
        "category": "multiomics",
        "chunk_index": 0,
        "doc_id": doc_id,
        "title": title,
        "authority": authority,
        "jurisdiction": "International",
        "authority_level": 5,
        "authority_rank": 2,
        "source_url": source_url,
        "effective_date": "",
        "section_heading": omics_type,
        "patent_number": "",
        "publication_year": 0,
        "omics_type": omics_type,
        "organism": organism,
        "compound": compound,
        "gene": gene,
        "protein": protein,
        "uniprot_accession": uniprot,
        "ncbi_gene_id": ncbi_gene_id,
        "pubchem_cid": pubchem_cid,
        "pathway": pathway,
        "assay_type": assay_type,
        "pmid": pmid,
    }


def document_key(omics_type: str, suffix: str) -> str:
    return omics_type.lower()


# ---------------------------------------------------------------------------
# PROTEOMICS — protein targets modulated by Ayurvedic bioactives.
# ---------------------------------------------------------------------------
PROTEOMICS = [
    _rec(
        "proteomics", "Homo sapiens", "Withaferin A (Withania somnifera)",
        "NFE2L2 (Nrf2) - master antioxidant transcription factor",
        "The transcription factor NFE2L2 (known as Nrf2) coordinates the antioxidant response via the Nrf2-ARE signalling pathway. Withaferin A, a withanolide from Withania somnifera (Ashwagandha), is reported to induce Nrf2 nuclear translocation and downstream expression of HMOX1 (heme oxygenase 1). Mechanistic evidence at the protein level supports cytoprotective, anti-inflammatory bioactivity relevant to wound-healing and neuroprotective claims.",
        gene="NFE2L2", protein="Nuclear factor erythroid 2-related factor 2",
        uniprot="Q16236", ncbi_gene_id="4780", pathway="Nrf2-ARE antioxidant response",
        assay_type="Western blot; luciferase reporter", source_url="https://www.uniprot.org/uniprotkb/Q16236",
        doc_suffix="01",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Curcumin (Curcuma longa)",
        "PTGS2 (COX-2) - inducible prostaglandin synthase",
        "PTGS2 encodes the inducible cyclooxygenase-2 enzyme that converts arachidonic acid into pro-inflammatory prostaglandins. Curcumin, the principal curcuminoid of Curcuma longa (turmeric), is documented to down-regulate PTGS2 expression through blockade of NF-kB signalling. Suppression of COX-2 protein is a well-characterized, evidence-linked mechanism supporting anti-inflammatory claims.",
        gene="PTGS2", protein="Prostaglandin-endoperoxide synthase 2 (COX-2)",
        uniprot="P35354", ncbi_gene_id="5743", pathway="Arachidonic acid metabolism; NF-kB",
        assay_type="Western blot; qRT-PCR", source_url="https://www.uniprot.org/uniprotkb/P35354",
        doc_suffix="02",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Boswellic acid (AKBA) (Boswellia serrata)",
        "ALOX5 (5-lipoxygenase) - leukotriene biosynthesis",
        "ALOX5 (5-lipoxygenase) initiates leukotriene biosynthesis from arachidonic acid. 3-O-acetyl-11-keto-beta-boswellic acid (AKBA) from Boswellia serrata gum resin is documented as a direct inhibitor of 5-lipoxygenase, a protein-level mechanism that distinguishes boswellic acids from classical COX inhibitors in the treatment of inflammatory and autoimmune conditions.",
        gene="ALOX5", protein="Arachidonate 5-lipoxygenase",
        uniprot="P09917", ncbi_gene_id="240", pathway="Arachidonic acid metabolism; leukotriene synthesis",
        assay_type="Enzyme activity assay", source_url="https://www.uniprot.org/uniprotkb/P09917",
        doc_suffix="03",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Berberine (Berberis aristata / Tinospora cordifolia)",
        "PRKAA1 (AMPK alpha-1) - cellular energy sensor",
        "PRKAA1 encodes the catalytic alpha-1 subunit of AMP-activated protein kinase (AMPK), the central cellular energy sensor. Berberine, an isoquinoline alkaloid from Berberis species, is documented to activate AMPK signalling, a mechanism associated with improved glucose and lipid metabolism. This protein-level evidence supports metabolic and cardiometabolic claims.",
        gene="PRKAA1", protein="5'-AMP-activated protein kinase catalytic subunit alpha-1",
        uniprot="Q13131", ncbi_gene_id="5562", pathway="AMPK signalling",
        assay_type="Phospho-protein assay (p-AMPK/AMPK)", source_url="https://www.uniprot.org/uniprotkb/Q13131",
        doc_suffix="04",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Withaferin A (Withania somnifera)",
        "STAT3 - signal transducer and activator of transcription 3",
        "STAT3 is a transcription factor that mediates inflammation, proliferation and survival signals. Withaferin A is reported to inhibit constitutive and inducible STAT3 activation (Tyr705 phosphorylation) and to down-regulate STAT3 target genes. The protein-level inhibition of STAT3 provides mechanistic evidence for anti-inflammatory and anti-proliferative effects of Ashwagandha-derived withanolides.",
        gene="STAT3", protein="Signal transducer and activator of transcription 3",
        uniprot="P40763", ncbi_gene_id="6774", pathway="JAK-STAT signalling",
        assay_type="Western blot (p-STAT3/STAT3)", source_url="https://www.uniprot.org/uniprotkb/P40763",
        doc_suffix="05",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Curcumin (Curcuma longa)",
        "TP53 (p53) - tumour suppressor and apoptosis regulator",
        "TP53 encodes the p53 tumour suppressor that regulates DNA repair, cell-cycle arrest and apoptosis. Curcumin is documented to modulate p53 pathway activity and to influence downstream apoptosis regulators such as CASP3 (caspase-3). Protein-level modulation of the p53 axis is frequently cited in mechanistic rationales for curcumin-based chemopreventive claims.",
        gene="TP53", protein="Cellular tumour antigen p53",
        uniprot="P04637", ncbi_gene_id="7157", pathway="p53 signalling; apoptosis",
        assay_type="Western blot; flow cytometry", source_url="https://www.uniprot.org/uniprotkb/P04637",
        doc_suffix="06",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Bacopa monnieri (Brahmi) extract",
        "BDNF - brain-derived neurotrophic factor",
        "BDNF (brain-derived neurotrophic factor) supports neuronal survival, synaptic plasticity and memory. Standardised bacosides from Bacopa monnieri are documented to increase BDNF expression and signalling in models of cognitive enhancement. Protein-level elevation of BDNF is a recognised mechanistic marker for nootropic claims.",
        gene="BDNF", protein="Brain-derived neurotrophic factor",
        uniprot="P23560", ncbi_gene_id="627", pathway="Neurotrophin signalling; synaptic plasticity",
        assay_type="ELISA; Western blot", source_url="https://www.uniprot.org/uniprotkb/P23560",
        doc_suffix="07",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Withania somnifera (Ashwagandha)",
        "GABRA1 - GABA-A receptor alpha-1 subunit (anxiolytic target)",
        "GABRA1 encodes the alpha-1 subunit of the GABA-A receptor, the principal inhibitory ionotropic receptor in the central nervous system and the target of many anxiolytics. Withania somnifera glycowithanolides are documented to modulate GABAergic signalling, a mechanism consistent with the anxiolytic and sleep-promoting effects reported in clinical studies of Ashwagandha root extracts.",
        gene="GABRA1", protein="Gamma-aminobutyric acid receptor subunit alpha-1",
        uniprot="P14867", ncbi_gene_id="2554", pathway="GABAergic synapse",
        assay_type="Binding assay; electrophysiology", source_url="https://www.uniprot.org/uniprotkb/P14867",
        doc_suffix="08",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Guggulsterone (Commiphora mukul)",
        "NR1H4 (FXR) - farnesoid X receptor",
        "NR1H4 encodes the farnesoid X receptor (FXR), a nuclear receptor that regulates bile acid, lipid and glucose homeostasis. Guggulsterone, the plant sterol from Commiphora mukul (guggul), is documented as a natural antagonist-modulator of FXR, a protein-level mechanism supporting lipid-modulating claims.",
        gene="NR1H4", protein="Bile acid receptor (FXR)",
        uniprot="Q96RI1", ncbi_gene_id="9971", pathway="Bile acid metabolism; nuclear receptor signalling",
        assay_type="Reporter assay; SPR", source_url="https://www.uniprot.org/uniprotkb/Q96RI1",
        doc_suffix="09",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Piperine (Piper nigrum)",
        "CYP3A4 - cytochrome P450 3A4 (drug metabolism)",
        "CYP3A4 is the principal drug-metabolizing cytochrome P450 in human liver, responsible for metabolizing roughly half of all marketed drugs. Piperine from Piper nigrum (black pepper) is documented to inhibit CYP3A4-mediated metabolism, a mechanistic basis for the clinically reported increase in bioavailability of co-administered compounds such as curcumin and rifampicin (herbal-drug interaction).",
        gene="CYP3A4", protein="Cytochrome P450 3A4",
        uniprot="P08684", ncbi_gene_id="1576", pathway="Xenobiotic metabolism; Phase I",
        assay_type="Microsomal activity assay", source_url="https://www.uniprot.org/uniprotkb/P08684",
        doc_suffix="10",
    ),
    _rec(
        "proteomics", "Homo sapiens", "Curcumin (Curcuma longa)",
        "ABCB1 (P-glycoprotein) - efflux transporter modulating bioavailability",
        "ABCB1 encodes the ATP-binding cassette efflux transporter P-glycoprotein (P-gp) that limits intestinal and blood-brain barrier uptake of xenobiotics. Curcumin and its metabolites are documented to modulate ABCB1/P-gp activity, influencing the pharmacokinetic profile of co-administered drugs and supporting claims about enhanced bioavailability when combined with P-gp-modulating bioactives.",
        gene="ABCB1", protein="ATP-dependent translocase ABCB1 (P-glycoprotein 1)",
        uniprot="P08183", ncbi_gene_id="5243", pathway="Xenobiotic efflux; ADME",
        assay_type="Efflux assay (Caco-2)", source_url="https://www.uniprot.org/uniprotkb/P08183",
        doc_suffix="11",
    ),
]


# ---------------------------------------------------------------------------
# METABOLOMICS — phytochemical identity data (PubChem CID, verified entries).
# ---------------------------------------------------------------------------
METABOLOMICS = [
    _rec(
        "metabolomics", "Withania somnifera", "Withaferin A",
        "Withaferin A - steroidal lactone marker of Ashwagandha",
        "Withaferin A is a C28 steroidal lactone typically considered a characteristic phytoconstituent of Withania somnifera (Ashwagandha) roots and leaves. It is the most-studied withanolide and is registered in PubChem (CID 265237). Its identity as a withanolide marker is routinely used in quality control and metabolomic profiling of Ashwagandha raw material and extracts.",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="265237", pathway="Withanolide biosynthesis",
        assay_type="HPLC-PDA / LC-MS", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/265237",
        doc_suffix="01",
    ),
    _rec(
        "metabolomics", "Curcuma longa", "Curcumin",
        "Curcumin - diarylheptanoid biomarker of turmeric",
        "Curcumin (diferuloylmethane) is the principal bioactive diarylheptanoid of Curcuma longa (turmeric) rhizomes and is registered in PubChem (CID 969516). Metabolomic fingerprinting of turmeric grades curcumin alongside demethoxycurcumin and bisdemethoxycurcumin as the three main curcuminoids used for standardisation (typically '95% curcuminoids').",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="969516", pathway="Phenylpropanoid biosynthesis",
        assay_type="HPLC-DAD / LC-MS/MS", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/969516",
        doc_suffix="02",
    ),
    _rec(
        "metabolomics", "Piper nigrum", "Piperine",
        "Piperine - pungent alkaloid of black pepper",
        "Piperine is the pungent piperidine-alkaloid responsible for the taste of Piper nigrum (black pepper) and is registered in PubChem (CID 638024). Beyond its sensory role it is documented as a bioenhancer that inhibits CYP3A4 and P-glycoprotein, increasing the oral bioavailability of co-administered phytochemicals such as curcumin.",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="638024", pathway="Alkaloid biosynthesis",
        assay_type="HPLC / UPLC-MS", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/638024",
        doc_suffix="03",
    ),
    _rec(
        "metabolomics", "Berberis aristata / Tinospora cordifolia", "Berberine",
        "Berberine - isoquinoline alkaloid with metabolic activity",
        "Berberine is an isoquinoline alkaloid found in Berberis species and reported in Tinospora cordifolia, and is registered in PubChem (CID 2353). It is widely studied for AMPK-dependent effects on glucose and lipid metabolism. Its common name and structure make it a canonical metabolomic marker for berberine-containing botanicals.",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="2353", pathway="Isoquinoline alkaloid biosynthesis",
        assay_type="HPLC / LC-MS", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/2353",
        doc_suffix="04",
    ),
    _rec(
        "metabolomics", "Rheum / Raphanus sativus / Polygonum", "Emodin",
        "Emodin - anthraquinone with laxative and anti-inflammatory markers",
        "Emodin is a hydroxyanthraquinone found in Rheum species roots, Polygonum cuspidatum and Cassia, and is registered in PubChem (CID 3220). It is a marker constituent in metabolomic and quality-control profiling of rheum and related laxative botanicals.",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="3220", pathway="Anthraquinone biosynthesis",
        assay_type="HPLC / TLC-densitometry", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/3220",
        doc_suffix="05",
    ),
    _rec(
        "metabolomics", "Glycyrrhiza glabra", "Glycyrrhizic acid",
        "Glycyrrhizic acid - triterpenoid saponin marker of liquorice",
        "Glycyrrhizic acid (glycyrrhizin) is the bioactive triterpenoid saponin of Glycyrrhiza glabra (liquorice/yashtimadhu) and is registered in PubChem (CID 14982). It is used as a chemical marker in pharmacopoeial standards and its presence defines the sweet taste and expectorant profile of liquorice extracts.",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="14982", pathway="Triterpenoid saponin biosynthesis",
        assay_type="HPLC-UV / LC-MS", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/14982",
        doc_suffix="06",
    ),
    _rec(
        "metabolomics", "Andrographis paniculata", "Andrographolide",
        "Andrographolide - labdane diterpenoid of Kalmegh / Andrographis",
        "Andrographolide is the major labdane diterpenoid lactone of Andrographis paniculata (Kalmegh / Bhuinimb) and is registered in PubChem (CID 5318517). It is a standard marker for raw-material identity and is studied for NF-kB-mediated anti-inflammatory effects.",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="5318517", pathway="Diterpenoid biosynthesis",
        assay_type="HPLC / LC-MS/MS", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/5318517",
        doc_suffix="07",
    ),
    _rec(
        "metabolomics", "Emblica officinalis / Phyllanthus", "Quercetin and gallic acid",
        "Amla (Emblica officinalis) polyphenol profile",
        "Emblica officinalis (Amla/Indian gooseberry) is characterised by a polyphenol metabolome dominated by hydrolysable tannins, flavonoids such as quercetin (PubChem CID 5280343) and phenolic acids including gallic acid (PubChem CID 370). These markers underpin its antioxidant and immunomodulatory monograph requirements.",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="5280343", pathway="Phenylpropanoid / tannin biosynthesis",
        assay_type="RP-HPLC / UHPLC-QTOF", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/5280343",
        doc_suffix="08",
    ),
    _rec(
        "metabolomics", "Ocimum sanctum", "Ursolic acid",
        "Ursolic acid - pentacyclic triterpene marker of Tulsi",
        "Ursolic acid is a pentacyclic triterpenoid that is a characteristic marker of Ocimum sanctum (Tulsi/holy basil) leaves and is registered in PubChem (CID 64945). Together with oleanolic acid (CID 10494) and eugenol-derived metabolites, it defines the chemotaxonomic metabolomic profile used in Tulsi QC.",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="64945", pathway="Triterpenoid biosynthesis",
        assay_type="HPLC / GC-MS", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/64945",
        doc_suffix="09",
    ),
    _rec(
        "metabolomics", "Cajanus/Zingiber officinale (ginger)", "Total phenolic metabolome",
        "Ginger (Zingiber officinale) oleoresin markers",
        "Ginger oleoresin metabolomics are dominated by gingerols (e.g. 6-gingerol) and shogaols, with flavonoids such as kaempferol (PubChem CID 5280863) and apigenin (CID 5280443) reported in minor fractions. These markers are used in the standardisation of ginger extracts for anti-nausea and anti-inflammatory indications.",
        gene="", protein="", uniprot="", ncbi_gene_id="",
        pubchem_cid="5280863", pathway="Phenylpropanoid / gingerol biosynthesis",
        assay_type="UHPLC-MS", source_url="https://pubchem.ncbi.nlm.nih.gov/compound/5280863",
        doc_suffix="10",
    ),
]


# ---------------------------------------------------------------------------
# PHARMACOGENOMICS — herb-drug interaction genes and reported pharmacokinetics.
# ---------------------------------------------------------------------------
PHARMACOGENOMICS = [
    _rec(
        "pharmacogenomics", "Homo sapiens", "Piperine + Curcumin",
        "Piperine increases curcumin oral bioavailability ~2000%",
        "The landmark interaction study documented that co-administration of piperine (20 mg) with curcumin (2 g) increased serum curcumin concentration by 2000% in human volunteers compared with curcumin alone, attributed to inhibition of hepatic and intestinal glucuronidation, CYP3A4 and P-glycoprotein (ABCB1). The underlying gene network spans UGT1A1, CYP3A4 and ABCB1. Direct citation: Shoba et al., Planta Medica 1998;64(4):353-6 (PMID 9619120).",
        gene="CYP3A4; ABCB1; UGT1A1", protein="P450 3A4; P-gp; UDP-glucuronosyltransferase",
        uniprot="P08684", ncbi_gene_id="1576", pathway="Phase I/II metabolism; efflux",
        assay_type="Human pharmacokinetic study", pmid="9619120",
        source_url="https://pubmed.ncbi.nlm.nih.gov/9619120/", doc_suffix="01",
    ),
    _rec(
        "pharmacogenomics", "Homo sapiens", "Withania somnifera (Ashwagandha)",
        "Ashwagandha - CYP3A4/CYP2C9 interaction risk flag",
        "Withania somnifera root extracts containing withanolides are documented as potential inhibitors of CYP3A4 and CYP2C9 in preclinical interaction screening. The clinical relevance applies to patients co-medicated with CYP3A4 substrates (statins, calcium-channel blockers, immunosuppressants). The absence of a large phase-I human interaction dataset should be flagged rather than affirmed. Database reference: NLM/DrugBank-grade interaction flags.",
        gene="CYP3A4; CYP2C9", protein="Cytochrome P450 3A4; 2C9",
        uniprot="P08684", ncbi_gene_id="1576", pathway="Xenobiotic (Phase I) metabolism",
        assay_type="In vitro inhibition screen", source_url="https://www.uniprot.org/uniprotkb/P08684",
        doc_suffix="02",
    ),
    _rec(
        "pharmacogenomics", "Homo sapiens", "Curcumin (Curcuma longa)",
        "Curcumin modulates ABCB1/P-gp and UGT-mediated disposition",
        "Curcumin is documented to modulate P-glycoprotein (ABCB1) and UDP-glucuronosyltransferase activity, which can alter the exposure of orally administered drugs (digoxin, irinotecan, anticoagulants). Pharmacogenomic counselling should consider ABCB1 and UGT1A1 genotype when dose-customising curcumin-combination claims.",
        gene="ABCB1; UGT1A1", protein="P-glycoprotein; UGT1A1",
        uniprot="P08183", ncbi_gene_id="5243", pathway="Efflux and conjugation disposition",
        assay_type="Human and animal PK studies", source_url="https://www.uniprot.org/uniprotkb/P08183",
        doc_suffix="03",
    ),
    _rec(
        "pharmacogenomics", "Homo sapiens", "Berberine (Tinospora cordifolia)",
        "Berberine - CYP2D6/CYP3A4 and SLC22A1 (OCT1) interplay",
        "Berberine's metabolism involves CYP2D6 and CYP3A4, and its hepatic uptake is mediated by the organic cation transporter SLC22A1 (OCT1, NCBI Gene 6560). Polymorphisms in SLC22A1 alter berberine disposition, informing personalised dosing for its glucose-lowering and lipid-modulating claims.",
        gene="SLC22A1; CYP2D6; CYP3A4", protein="Organic cation transporter 1; CYP2D6; CYP3A4",
        uniprot="O15245", ncbi_gene_id="6560", pathway="Hepatic uptake; Phase I metabolism",
        assay_type="In vitro transport and metabolism assays", source_url="https://www.uniprot.org/uniprotkb/O15245",
        doc_suffix="04",
    ),
    _rec(
        "pharmacogenomics", "Homo sapiens", "Ginkgo/Panax-derived scutellarein", "Flavonoid SLC-family transporter interactions",
        "Plant flavonoids (incl. baicalein, PubChem CID 5281605 and apigenin) are documented as substrates/inhibitors of the organic anion-transporting polypeptide (OATP) and multidrug resistance transporters, informing interaction flags for co-administered statins (simvastatin) and antihypertensives. The relevant pharmacogenes include SLCO1B1 and ABCB1.",
        gene="SLCO1B1; ABCB1", protein="OATP1B1; P-glycoprotein",
        uniprot="Q9Y6L6", ncbi_gene_id="10599", pathway="Hepatic sinusoidal uptake; efflux",
        assay_type="OATP/IVIVC transporter assays", source_url="https://www.uniprot.org/uniprotkb/Q9Y6L6",
        doc_suffix="05",
    ),
]


# ---------------------------------------------------------------------------
# PATHWAY — signalling pathways engaged by Ayurvedic bioactives.
# ---------------------------------------------------------------------------
PATHWAYS = [
    _rec(
        "pathway", "Homo sapiens", "Withaferin A / Curcumin",
        "Nrf2-ARE antioxidant response pathway",
        "The Nrf2-ARE pathway (NFE2L2 -> KEAP1 -> ARE) is the canonical cellular antioxidant response axis. Bioactives including withaferin A and curcumin are documented to liberate Nrf2 from KEAP1, driving transcription of HMOX1, NQO1 and phase-II enzymes. Reference: WikiPathways WP5239-aligned redox pathway components.",
        gene="NFE2L2; KEAP1; HMOX1; NQO1", protein="Nrf2; Keap1; HMOX1; NQO1",
        uniprot="Q16236", ncbi_gene_id="4780", pathway="Nrf2-ARE antioxidant response",
        assay_type="Pathway reporter assays", source_url="https://www.wikipathways.org/pathways/WP5239.html",
        doc_suffix="01",
    ),
    _rec(
        "pathway", "Homo sapiens", "Curcumin / Boswellic acid",
        "NF-kB inflammatory signalling pathway",
        "The NF-kB pathway (RELA/p65, NFKB1, IKBKB, NFKBIA) is the master regulator of pro-inflammatory gene expression. Curcumin and boswellic acids are documented NF-kB pathway suppressors via IKK inhibition, reducing PTGS2 (COX-2), TNF, IL6 and IL1B output.",
        gene="NFKB1; RELA; IKBKB; PTGS2; TNF; IL6", protein="NF-kB p50/p65; IKK-beta; COX-2; TNF; IL-6",
        uniprot="P19838", ncbi_gene_id="4790", pathway="NF-kB signalling",
        assay_type="Luciferase NF-kB reporter; cytokine ELISA", source_url="https://www.wikipathways.org/pathways/WP5609.html",
        doc_suffix="02",
    ),
    _rec(
        "pathway", "Homo sapiens", "Ashwagandha glycowithanolides",
        "GABAergic anxiolytic signalling pathway",
        "GABAergic signalling (GABRA1/GABRB3 receptor subunits, GABA synthesis via GAD1) mediates inhibitory neurotransmission and is the canonical target for anxiolytics. Withania somnifera glycowithanolides are documented to enhance GABAergic activity, consistent with anxiolytic clinical claims.",
        gene="GABRA1; GAD1; GABBR1", protein="GABA-A alpha-1; GAD1; GABA-B1",
        uniprot="P14867", ncbi_gene_id="2554", pathway="GABAergic synapse",
        assay_type="Binding displacement assays", source_url="https://www.wikipathways.org/pathways/WP1362.html",
        doc_suffix="03",
    ),
    _rec(
        "pathway", "Homo sapiens", "Berberine",
        "AMPK metabolic sensing pathway",
        "AMPK signalling (PRKAA1/PRKAA2, STK11/LKB1) is the energy-sensing axis governing glucose uptake, fatty-acid oxidation and autophagy. Berberine is documented to activate AMPK, improving hepatic and muscle insulin sensitivity in pre-clinical and clinical settings.",
        gene="PRKAA1; STK11; SLC2A4", protein="AMPK alpha-1; LKB1; GLUT4",
        uniprot="Q13131", ncbi_gene_id="5562", pathway="AMPK signalling",
        assay_type="p-AMPK immunoassay; glucose uptake", source_url="https://www.wikipathways.org/pathways/WP1406.html",
        doc_suffix="04",
    ),
    _rec(
        "pathway", "Homo sapiens", "Resveratrol / curcumin",
        "PI3K-Akt-mTOR survival pathway",
        "The PI3K/Akt/mTOR pathway (PIK3CA->AKT1->MTOR) couples growth signals to protein synthesis and survival. Polyphenols including curcumin and resveratrol are documented to modulate AKT1 phosphorylation, providing mechanistic rationale for anti-proliferative and longevity claims.",
        gene="PIK3CA; AKT1; MTOR", protein="PI3K; AKT1; mTOR",
        uniprot="P31749", ncbi_gene_id="207", pathway="PI3K-Akt-mTOR signalling",
        assay_type="Phospho-AKT Western blot", source_url="https://www.wikipathways.org/pathways/WP2843.html",
        doc_suffix="05",
    ),
]


def build_omics_seed_documents() -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for omics in (PROTEOMICS, METABOLOMICS, PHARMACOGENOMICS, PATHWAYS):
        docs.extend(omics)
    # Genomics subset folded into proteomics/transcriptomics via gene-level
    # records (gene id + protein accession are already attached).
    return docs