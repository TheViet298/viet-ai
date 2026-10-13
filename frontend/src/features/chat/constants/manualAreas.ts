/** Local reference centres only: never a GPS fix or a geocoded address. */
export const MANUAL_AREAS = [
  { id: "ha-noi", label: "Hà Nội", aliases: ["ha noi", "hanoi", "hn", "tp ha noi"], coord: { lat: 21.0285, lng: 105.8542 } },
  { id: "ho-chi-minh", label: "TP. Hồ Chí Minh", aliases: ["ho chi minh", "tp ho chi minh", "tphcm", "tp hcm", "hcm", "sai gon", "saigon"], coord: { lat: 10.8231, lng: 106.6297 } },
  { id: "da-nang", label: "Đà Nẵng", aliases: ["da nang", "danang", "tp da nang"], coord: { lat: 16.0544, lng: 108.2022 } },
  { id: "long-thanh", label: "Cao tốc Long Thành", aliases: ["long thanh", "cao toc long thanh"], coord: { lat: 10.7712, lng: 106.945 } },
] as const;

export function normalizeAreaText(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d")
    .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

export function searchManualAreas(query: string) {
  const normalized = normalizeAreaText(query);
  return MANUAL_AREAS.filter((area) => [area.label, ...area.aliases].some((alias) => normalizeAreaText(alias).includes(normalized)));
}

export function resolveManualArea(label: string) {
  // Only exact area names are resolved. Substring guesses confuse street names
  // (e.g. Xa Lộ Hà Nội in TP.HCM) and ambiguous multi-city addresses.
  const normalized = normalizeAreaText(label);
  if (!normalized) return undefined;
  const matches = MANUAL_AREAS.filter((area) => [area.label, ...area.aliases].some((alias) => normalizeAreaText(alias) === normalized));
  return matches.length === 1 ? matches[0] : undefined;
}
