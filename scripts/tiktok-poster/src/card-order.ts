/** Problem types and their variant counts (matching ProblemType.swift) */
const PROBLEM_TYPES: Array<{ type: string; variants: number }> = [
  { type: 'staying_up_late', variants: 21 },
  { type: 'cant_wake_up', variants: 14 },
  { type: 'self_loathing', variants: 14 },
  { type: 'rumination', variants: 14 },
  { type: 'procrastination', variants: 14 },
  { type: 'anxiety', variants: 14 },
  { type: 'lying', variants: 14 },
  { type: 'bad_mouthing', variants: 14 },
  { type: 'porn_addiction', variants: 14 },
  { type: 'alcohol_dependency', variants: 14 },
  { type: 'anger', variants: 14 },
  { type: 'obsessive', variants: 14 },
  { type: 'loneliness', variants: 14 },
];

/** Generate the full card_order array (189 cards, rule-based first) */
export function generateCardOrder(): string[] {
  const order: string[] = [];
  for (const { type, variants } of PROBLEM_TYPES) {
    for (let i = 0; i < variants; i++) {
      order.push(`${type}_${i}`);
    }
  }
  return order;
}

/** Total number of cards per language */
export const TOTAL_CARDS = PROBLEM_TYPES.reduce((sum, p) => sum + p.variants, 0);

/** Extract problem type from card_id (e.g., "staying_up_late_0" → "staying_up_late") */
export function problemTypeFromCardId(cardId: string): string {
  return cardId.replace(/_\d+$/, '');
}
