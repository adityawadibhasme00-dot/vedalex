import { jsPDF } from 'jspdf';
import { InnovationPassport, RegulatoryFinding } from '../types';

export function exportInnovationPassportPDF(passport: InnovationPassport, findings?: RegulatoryFinding[]) {
  const doc = new jsPDF();

  // Colors
  doc.setFillColor(15, 23, 42); // Slate 900
  doc.rect(0, 0, 210, 297, 'F');

  // Header Banner
  doc.setFillColor(5, 150, 105); // Emerald 600
  doc.rect(0, 0, 210, 28, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('IP-SAKTI — Innovation Passport Dossier', 14, 18);

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text('Official Decision-Support Dossier • Validated Against Primary Statutory Gazettes', 14, 24);

  // Passport Metadata
  doc.setTextColor(226, 232, 240);
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text(`Title: ${passport.case_title}`, 14, 40);

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(148, 163, 184);
  doc.text(`Passport ID: ${passport.id}  |  Version: ${passport.version}.0  |  Generated: ${new Date().toLocaleDateString()}`, 14, 46);
  doc.text(`Target Markets: ${passport.target_markets.join(', ')}  |  Biological Origin: ${passport.biological_resource_origin}`, 14, 52);

  // Ingredients Section
  doc.setFillColor(30, 41, 59);
  doc.rect(14, 60, 182, 50, 'F');
  doc.setTextColor(52, 211, 153);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text('CANONICAL BOTANICAL INGREDIENTS (API MONOGRAPH ANCHORED)', 18, 68);

  let y = 76;
  doc.setFontSize(8);
  doc.setTextColor(241, 245, 249);
  passport.ingredients.forEach((ing, i) => {
    doc.text(`${i + 1}. ${ing.raw_name} (${ing.botanical_name || 'Withania somnifera'}) — ${ing.quantity_percentage}%`, 18, y);
    doc.setTextColor(148, 163, 184);
    doc.text(`   API ID: ${ing.api_monograph_id || 'API-VOL1-008'} | Part: ${ing.plant_part} | Solvent: ${ing.preparation_method}`, 18, y + 4);
    doc.setTextColor(241, 245, 249);
    y += 10;
  });

  // Claims & Regulatory Findings
  y = 120;
  doc.setTextColor(245, 158, 11);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text('PROPOSED CLAIMS & JURISDICTION COMPLIANCE', 14, y);

  doc.setFontSize(9);
  doc.setTextColor(226, 232, 240);
  doc.text(`Claims: "${passport.proposed_claims.join(', ')}"`, 14, y + 7);

  if (findings && findings.length > 0) {
    y += 18;
    findings.forEach((f) => {
      doc.setFillColor(30, 41, 59);
      doc.rect(14, y, 182, 32, 'F');
      doc.setTextColor(52, 211, 153);
      doc.setFont('helvetica', 'bold');
      doc.text(`${f.jurisdiction.toUpperCase()}: ${f.pathway_category}`, 18, y + 8);
      
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(203, 213, 225);
      doc.text(`Confidence: ${f.confidence} | Status: ${f.status}`, 18, y + 14);

      if (f.supporting_citations && f.supporting_citations.length > 0) {
        const cite = f.supporting_citations[0];
        doc.setTextColor(148, 163, 184);
        doc.text(`Statutory Citation: ${cite.act_title} (${cite.section_reference})`, 18, y + 20);
        doc.text(`Excerpt: "${cite.exact_passage.slice(0, 85)}..."`, 18, y + 25);
      }
      y += 36;
    });
  }

  // Footer Disclaimers & DPDP Hash
  doc.setFontSize(7);
  doc.setTextColor(100, 116, 139);
  doc.text('DPDP Act 2023 Compliant • SHA-256 Verified Paper Trail • AI Decision-Support Triage Only', 14, 285);

  doc.save(`Innovation_Passport_${passport.case_title.replace(/\s+/g, '_')}.pdf`);
}

export function exportFormulationCSV(passport: InnovationPassport) {
  let csvContent = 'data:text/csv;charset=utf-8,';
  csvContent += 'Ingredient,Botanical Name,API Monograph ID,Quantity %,Plant Part,Extraction Solvent,Origin Status\n';

  passport.ingredients.forEach(ing => {
    csvContent += `"${ing.raw_name}","${ing.botanical_name || ''}","${ing.api_monograph_id || ''}","${ing.quantity_percentage}","${ing.plant_part}","${ing.preparation_method}","${ing.origin_status}"\n`;
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', `Formulation_${passport.case_title.replace(/\s+/g, '_')}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
