import type { StyleSpecification } from "maplibre-gl";

/** Public build-time config. Invalid custom providers leave the list available. */
export function createRasterMapStyle(tileUrl?: string, attribution?: string): StyleSpecification {
  const custom = Boolean(tileUrl?.trim() || attribution?.trim());
  const url = custom ? tileUrl?.trim() ?? "" : "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const credit = custom ? attribution?.trim() ?? "" : "© OpenStreetMap contributors";
  if (!/^https:\/\//i.test(url) || !["{z}", "{x}", "{y}"].every((token) => url.includes(token)) || !credit) {
    throw new Error("A raster tile provider requires an HTTPS z/x/y URL and attribution");
  }
  const parsed = new URL(url);
  if (parsed.username || parsed.password) throw new Error("Tile URLs must not contain credentials");
  return { version: 8, sources: { basemap: { type: "raster", tiles: [url], tileSize: 256, attribution: credit } }, layers: [{ id: "basemap", type: "raster", source: "basemap" }] };
}
