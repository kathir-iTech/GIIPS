const ZONE_WARDS: Record<string, number[]> = {
  North: [1, 2, 3, 4, 10, 11, 12, 13, 14, 15, 18, 19, 20, 21, 25, 26, 27, 28, 29, 30],
  East: [5, 6, 7, 8, 9, 22, 23, 24, ...Array.from({ length: 12 }, (_, index) => index + 50)],
  Central: [31, 32, ...Array.from({ length: 4 }, (_, index) => index + 46), ...Array.from({ length: 9 }, (_, index) => index + 62), ...Array.from({ length: 5 }, (_, index) => index + 80)],
  West: [16, 17, ...Array.from({ length: 13 }, (_, index) => index + 33), ...Array.from({ length: 5 }, (_, index) => index + 71)],
  South: [...Array.from({ length: 4 }, (_, index) => index + 76), ...Array.from({ length: 16 }, (_, index) => index + 85)],
};

const WARD_ZONE = Object.entries(ZONE_WARDS).reduce<Record<string, string>>((lookup, [zone, wards]) => {
  wards.forEach(ward => { lookup[String(ward)] = zone; });
  return lookup;
}, {});

export const normalizeWard = (value?: string | null): string | null => {
  const match = value?.match(/\d+/);
  return match ? String(Number(match[0])) : null;
};

export const getCoimbatoreZone = (ward?: string | null): string | null => {
  const normalizedWard = normalizeWard(ward);
  return normalizedWard ? WARD_ZONE[normalizedWard] || null : null;
};
