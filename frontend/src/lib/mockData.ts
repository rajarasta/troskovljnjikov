import type { BoQItem } from "./types";

/** Create a mock BoQ item with sensible defaults — only override what differs. */
function createMockItem(overrides: Partial<BoQItem> & { id: string; row: number; description: string }): BoQItem {
  return {
    file_id: "mock-file",
    sheet_name: "Radovi",
    item_number: null,
    full_description: null,
    parent_item_number: null,
    unit: null,
    quantity: 0,
    unit_price: 0,
    total: 0,
    project_name: "Demo projekt",
    date: "2026-02",
    material_price: null,
    labor_price: null,
    material_total: null,
    labor_total: null,
    notes: null,
    drawing_path: null,
    llm_response: null,
    file_name: null,
    ...overrides,
  };
}

/** Croatian construction BoQ mock items for layout preview */
export const MOCK_ITEMS: BoQItem[] = [
  createMockItem({
    id: "mock-1", row: 1, item_number: "1.",
    description: "BETONSKI I ARMIRANO-BETONSKI RADOVI",
  }),
  createMockItem({
    id: "mock-2", row: 2, item_number: "1.1.", parent_item_number: "1.",
    unit: "m³", quantity: 1.2,
    description: "Nabava materijala, dovoz, montaža daščane glatke rubne oplate i betoniranje armirano betonske podne ploče u prostoru stubišta i ulazu, betonom C25/30 uz upotrebu vibratora, debljine 12 cm.",
    full_description: "AB ploču armirati prema statičkom proračunu i planu armature. Armatura je obračunata u zasebnoj stavci. U cijenu uključen kompletan materijal, montaža oplate, demontaža oplate nakon sušenja, čišćenje i odvoz kao i potrebno njegovanje betona.",
  }),
  createMockItem({
    id: "mock-3", row: 3, item_number: "1.2.", parent_item_number: "1.",
    unit: "m³", quantity: 3.5,
    description: "Betoniranje armirano betonskih nadtemeljnih zidova betonom C25/30 u dvostranoj glatkoj oplati, debljine 20 cm, visine do 1.0 m.",
    full_description: "Beton ugraditi uz vibriranje. Oplatu izvesti od glatkih dasaka. U cijenu uključen sav materijal, rad, oplata, transport.",
  }),
  createMockItem({
    id: "mock-4", row: 4, item_number: "1.3.", parent_item_number: "1.",
    unit: "m³", quantity: 8.4,
    description: "Betoniranje armirano betonske ploče kata debljine 16 cm, betonom C25/30, u glatkoj oplati.",
  }),
  createMockItem({
    id: "mock-5", row: 5, item_number: "1.4.", parent_item_number: "1.",
    unit: "m³", quantity: 2.1,
    description: "Betoniranje armirano betonskih greda presjeka 20/40 cm betonom C25/30 u glatkoj oplati.",
  }),
  createMockItem({
    id: "mock-6", row: 6, item_number: "1.5.", parent_item_number: "1.",
    unit: "m³", quantity: 1.6,
    description: "Betoniranje armirano betonskih stupova presjeka 30/30 cm betonom C30/37 u glatkoj oplati, visine do 3.0 m.",
  }),
  createMockItem({
    id: "mock-7", row: 7, item_number: "2.",
    description: "ZIDARSKI RADOVI",
  }),
  createMockItem({
    id: "mock-8", row: 8, item_number: "2.1.", parent_item_number: "2.",
    unit: "m²", quantity: 145.0,
    description: "Zidanje nosivih zidova blok-opekom d=25 cm u produžnom mortu M5, uključivo sve horizontalne i vertikalne serklaže.",
  }),
  createMockItem({
    id: "mock-9", row: 9, item_number: "2.2.", parent_item_number: "2.",
    unit: "m²", quantity: 62.0,
    description: "Zidanje pregradnih zidova blok-opekom d=12 cm u produžnom mortu M5.",
  }),
  createMockItem({
    id: "mock-10", row: 10, item_number: "2.3.", parent_item_number: "2.",
    unit: "m²", quantity: 380.0,
    description: "Žbukanje unutarnjih zidova i stropova produžnim mortom M5 u dva sloja, ukupne debljine 2 cm. Površine moraju biti ravne i glatke.",
  }),
];
