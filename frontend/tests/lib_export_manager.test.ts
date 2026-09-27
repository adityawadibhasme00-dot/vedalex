import fs from 'fs';
import {
  exportFormulationCSV,
  exportInnovationPassportPDF,
} from '../src/lib/exportManager';
import type { InnovationPassport, RegulatoryFinding } from '../src/types';

interface CapturedLink {
  rawHref: string;
  href: string;
  download: string;
}

let writeSpy: jest.SpyInstance;
let clickSpy: jest.SpyInstance;
const links: CapturedLink[] = [];

function ingredient(overrides: Partial<InnovationPassport['ingredients'][number]> = {}) {
  return {
    raw_name: 'Ashwagandha',
    botanical_name: 'Withania somnifera',
    api_monograph_id: 'API-A-101',
    plant_part: 'root',
    preparation_method: 'hydroalcoholic extract',
    quantity_percentage: 40,
    source_country: 'India',
    origin_status: 'user_confirmed' as const,
    ...overrides,
  };
}

function passport(overrides: Partial<InnovationPassport> = {}): InnovationPassport {
  return {
    id: 'pass-12345678',
    case_title: 'Ashwagandha Sleep Formulation',
    product_form: 'Tablet',
    dosage_form: '500 mg',
    intended_use: 'Supports restful sleep',
    proposed_claims: ['Supports restful sleep', 'Promotes relaxation'],
    claimed_innovation: 'Standardised withanolide profile',
    process_description: 'Hydroalcoholic extraction followed by drying',
    ingredients: [
      ingredient(),
      ingredient({
        raw_name: 'Brahmi',
        botanical_name: 'Bacopa monnieri',
        api_monograph_id: 'API-B-210',
        plant_part: 'whole plant',
        preparation_method: 'aqueous decoction',
        quantity_percentage: 20,
        origin_status: 'user_confirmed' as const,
      }),
    ],
    manufacturing_location: 'Ayur SEZ, Kerala',
    target_markets: ['India', 'Canada'],
    business_role: 'Startup / MSME Founder',
    biological_resource_origin: 'Cultivated',
    existing_ip_status: 'None',
    version: 3,
    unresolved_clarifications: [],
    created_at: '2026-01-01',
    updated_at: '2026-01-02',
    ...overrides,
  };
}

function finding(overrides: Partial<RegulatoryFinding> = {}): RegulatoryFinding {
  return {
    jurisdiction: 'india',
    pathway_category: 'Regulatory pathway',
    status: 'condition_satisfied',
    confidence: 'HIGH',
    conditions_evaluated: ['Novelty search completed'],
    supporting_citations: [
      {
        act_title: 'Patents Act 1970',
        section_reference: 'Section 13',
        authority: 'Indian Patent Office',
        effective_date: '2024-01-01',
        exact_passage:
          'A patent shall not be granted in respect of an invention which is new and involves an inventive step.',
        authority_rank: 1,
      },
    ],
    missing_facts: [],
    next_action_steps: ['File the complete specification'],
    coverage_limitations: 'None',
    assumptions_made: [],
    ...overrides,
  };
}

function csvText(): string {
  expect(links).toHaveLength(1);
  const prefix = 'data:text/csv;charset=utf-8,';
  expect(links[0].rawHref.startsWith(prefix)).toBe(true);
  return decodeURIComponent(links[0].rawHref.slice(prefix.length));
}

function pdfBytes(): Buffer {
  expect(writeSpy).toHaveBeenCalled();
  const calls = writeSpy.mock.calls as Array<[string, Buffer]>;
  return calls[calls.length - 1][1];
}

beforeAll(() => {
  writeSpy = jest.spyOn(fs, 'writeFileSync').mockImplementation(() => {});
  clickSpy = jest
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(function (this: HTMLAnchorElement) {
      links.push({
        rawHref: this.getAttribute('href') || '',
        href: this.href,
        download: this.getAttribute('download') || '',
      });
    });
});

afterAll(() => {
  jest.restoreAllMocks();
});

beforeEach(() => {
  links.length = 0;
  writeSpy.mockClear();
  clickSpy.mockClear();
});

describe('exportInnovationPassportPDF', () => {
  test('writes a pdf named after the case title', () => {
    exportInnovationPassportPDF(passport());
    expect(writeSpy).toHaveBeenCalledTimes(1);
    const calls = writeSpy.mock.calls as Array<[string, Buffer]>;
    expect(calls[0][0]).toBe('Innovation_Passport_Ashwagandha_Sleep_Formulation.pdf');
    expect(calls[0][1].subarray(0, 4).toString('utf8')).toBe('%PDF');
    expect(links).toHaveLength(0);
  });

  test('embeds passport identity, markets and ingredients', () => {
    exportInnovationPassportPDF(passport());
    const text = pdfBytes().toString('latin1');
    expect(text).toContain('IP-SAKTI');
    expect(text).toContain('Title: Ashwagandha Sleep Formulation');
    expect(text).toContain('Passport ID: pass-12345678');
    expect(text).toContain('India, Canada');
    expect(text).toContain('Withania somnifera');
    expect(text).toContain('Bacopa monnieri');
    expect(text).toContain('Supports restful sleep');
  });

  test('renders regulatory findings with their citations', () => {
    exportInnovationPassportPDF(passport(), [finding()]);
    const text = pdfBytes().toString('latin1');
    expect(text).toContain('PROPOSED CLAIMS & JURISDICTION COMPLIANCE');
    expect(text).toContain('INDIA: Regulatory pathway');
    expect(text).toContain('Confidence: HIGH | Status: condition_satisfied');
    expect(text).toContain('Statutory Citation: Patents Act 1970');
  });

  test('renders the first excerpt of a long citation passage', () => {
    const longFinding = finding({
      supporting_citations: [
        {
          act_title: 'Industrial Designs Act 2000',
          section_reference: 'Section 4',
          authority: 'Controller General of Patents',
          effective_date: '2024-06-01',
          exact_passage: 'x'.repeat(200),
          authority_rank: 2,
        },
      ],
    });
    exportInnovationPassportPDF(passport(), [longFinding]);
    const text = pdfBytes().toString('latin1');
    expect(text).toContain('Statutory Citation: Industrial Designs Act 2000');
    expect(text).toContain('x'.repeat(85) + '...');
    expect(text).not.toContain('x'.repeat(90));
  });

  test('exports without any findings supplied', () => {
    expect(() => exportInnovationPassportPDF(passport(), undefined)).not.toThrow();
    expect(writeSpy).toHaveBeenCalledTimes(1);
    const text = pdfBytes().toString('latin1');
    expect(text).not.toContain('Statutory Citation');
  });

  test('exports a passport with no optional citation data', () => {
    const bareFinding = finding({ supporting_citations: [] });
    expect(() => exportInnovationPassportPDF(passport(), [bareFinding])).not.toThrow();
    expect(writeSpy).toHaveBeenCalledTimes(1);
  });

  test.failing('a failed write is reported to the caller instead of throwing', () => {
    writeSpy.mockImplementationOnce(() => {
      throw new Error('disk full');
    });
    expect(() => exportInnovationPassportPDF(passport())).not.toThrow();
  });
});

describe('exportFormulationCSV', () => {
  test('writes a header row and one row per ingredient', () => {
    exportFormulationCSV(passport());
    expect(links).toHaveLength(1);
    expect(writeSpy).not.toHaveBeenCalled();
    const rows = csvText().trim().split('\n');
    expect(rows[0]).toBe(
      'Ingredient,Botanical Name,API Monograph ID,Quantity %,Plant Part,Extraction Solvent,Origin Status'
    );
    expect(rows).toHaveLength(3);
    expect(rows[1]).toBe(
      '"Ashwagandha","Withania somnifera","API-A-101","40","root","hydroalcoholic extract","user_confirmed"'
    );
    expect(rows[2]).toContain('"Brahmi"');
  });

  test('names the download after the case title', () => {
    exportFormulationCSV(passport());
    expect(links[0].download).toBe('Formulation_Ashwagandha_Sleep_Formulation.csv');
  });

  test('renders missing optional fields as empty values', () => {
    exportFormulationCSV(
      passport({
        ingredients: [
          ingredient({ raw_name: 'Brahmi', botanical_name: '', api_monograph_id: '' }),
        ],
      })
    );
    const rows = csvText().trim().split('\n');
    expect(rows[1]).toBe('"Brahmi","","","40","root","hydroalcoholic extract","user_confirmed"');
    expect(rows[1]).not.toContain('undefined');
  });

  test('exports a header only row when there are no ingredients', () => {
    exportFormulationCSV(passport({ ingredients: [] }));
    const rows = csvText().trim().split('\n');
    expect(rows).toHaveLength(1);
    expect(rows[0]).toContain('Ingredient,Botanical Name');
  });

  test('removes the temporary anchor from the document', () => {
    exportFormulationCSV(passport());
    expect(document.querySelectorAll('a[download]')).toHaveLength(0);
  });

  test('keeps every row intact in the data uri', () => {
    exportFormulationCSV(passport());
    expect(new URL(links[0].href).hash).toBe('');
    expect(csvText()).toContain('"Withania somnifera"');
  });

  test.failing('embedded double quotes are escaped for spreadsheet parsers', () => {
    exportFormulationCSV(
      passport({
        ingredients: [ingredient({ raw_name: 'Weird "Quote" herb' })],
      })
    );
    expect(csvText()).toContain('"Weird ""Quote"" herb"');
  });

  test.failing('a value containing # does not truncate the data uri', () => {
    exportFormulationCSV(
      passport({
        ingredients: [ingredient({ raw_name: 'Ashwagandha #1' })],
      })
    );
    expect(new URL(links[0].href).hash).toBe('');
  });
});

describe('export file naming', () => {
  test.failing('export file names never contain characters that are illegal on disk', () => {
    const awkward = passport({ case_title: 'Sleep / Recovery: v2?' });
    exportInnovationPassportPDF(awkward);
    exportFormulationCSV(awkward);
    expect(writeSpy).toHaveBeenCalledTimes(1);
    expect(links).toHaveLength(1);
    const illegal = /[\\/:*?"<>|]/;
    expect((writeSpy.mock.calls[0] as Array<[string, Buffer]>)[0]).not.toMatch(illegal);
    expect(links[0].download).not.toMatch(illegal);
  });
});
