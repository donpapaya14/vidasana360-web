export const CATEGORIES = {
  'nutrition': { name: 'Nutrition', slug: 'nutrition', description: 'Eat smarter with real science' },
  'fitness': { name: 'Fitness', slug: 'fitness', description: 'Workouts that actually work' },
  'weight-loss': { name: 'Weight Loss', slug: 'weight-loss', description: 'Lose fat with science' },
  'wellness': { name: 'Wellness', slug: 'wellness', description: 'Feel your best every day' },
  'mental-health': { name: 'Mental Health', slug: 'mental-health', description: 'Mental health tips backed by research' }
} as const;

export type Category = keyof typeof CATEGORIES;

export function getCategoryName(cat: Category): string {
  return CATEGORIES[cat].name;
}

export function getCategoryBadgeClass(cat: Category): string {
  return `badge badge--${cat}`;
}
