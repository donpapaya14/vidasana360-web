export const CATEGORIES = {
  nutricion: { name: 'Nutricion', slug: 'nutricion', description: 'Alimentacion basada en evidencia' },
  ejercicio: { name: 'Ejercicio', slug: 'ejercicio', description: 'Movimiento y fitness con ciencia' },
  mente: { name: 'Mente', slug: 'mente', description: 'Salud mental y bienestar emocional' },
  longevidad: { name: 'Longevidad', slug: 'longevidad', description: 'Envejecer mejor con ciencia' },
  recetas: { name: 'Recetas Saludables', slug: 'recetas', description: 'Cocina sana y deliciosa' },
} as const;

export type Category = keyof typeof CATEGORIES;

export function getCategoryName(cat: Category): string {
  return CATEGORIES[cat].name;
}

export function getCategoryBadgeClass(cat: Category): string {
  return `badge badge--${cat}`;
}
