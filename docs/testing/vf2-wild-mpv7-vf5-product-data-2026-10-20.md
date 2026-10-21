# Product-page review: VF 2, VF Wild, VF MPV 7 and VF 5 — 2026-10-20

## Sources and review boundary

Reviewed the four user-supplied VinFast product pages on 2026-10-20:

- [VF 2](https://vinfastauto.com/vn_vi/dat-coc-xe-vf2)
- [VF Wild](https://vinfastauto.com/vn_vi/dat-coc-xe-vf-wild)
- [VF MPV 7](https://vinfastauto.com/vn_vi/dat-coc-xe-vf-mpv7)
- [VF 5](https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf5)

The web reader exposed the official product-page body. This review did not capture raw HTML, HTTP status codes, linked brochures, or hashes. The exact observations and limits are recorded in `fixtures/knowledge/source_reviews/vf2-wild-mpv7-vf5-product-2026-10-20.json`.

## New product-page observations

| Model | Price shown | Main page facts |
|---|---:|---|
| VF 2 | List price 188,000,000 VND | 4 seats; 210 km NEDC; 18.3 kWh usable battery; 30 kW; 34 min from 10–70%; approximately 24 kW max DC; dimensions 3090 × 1496 × 1663.2 mm; 8 listed colors; warranty headline 7 years or 160,000 km, whichever comes first. |
| VF MPV 7 | List price 750,000,000 VND | 7 seats; 450 km NEDC; 60.13 kWh usable battery; 150 kW; 280 Nm; 30 min from 10–70%; AC max 6.9 kW; DC max 80 kW; dimensions 4740 × 1872 × 1734 mm; 6 listed colors; warranty headline 7 years or 160,000 km, whichever comes first. |
| VF 5 | List price 496,000,000 VND | Refreshed page confirms existing reviewed record: 5 seats; 326 km NEDC; 37.23 kWh; 100 kW; 33 min from 10–70%; AC max 6.6 kW; approximately 50 kW max DC; 6 listed colors; warranty headline 7 years or 160,000 km, whichever comes first. |

## Published exterior colors

- **VF 2:** Infinity Blanc, Desat Silver, Solar Ruby, Yellow, Sky Blue, Urban Mint, Rose Pink, Be Pebble.
- **VF MPV 7:** Infinity Blanc, Zenith Grey, Jet Black, Solar Ruby, Moonlit Ocean, Introspective Brown.
- **VF 5:** Infinity Blanc, Zenith Grey, Solar Ruby, Summer Yellow Body - Jet Black Roof, Sky Blue - Infinity Blanc Roof, Urban Mint. The two combined labels specify body and roof colors respectively.
- **VF Wild:** no color palette was exposed in the product-page content reviewed.

The exact labels are now available to the reviewed model-color answer path for VF 2 and VF MPV 7. Color availability by trim/model year and dealer stock remain unverified; the chatbot should only report the published model-level palette.

Prices are the page's listed prices, not on-road prices or confirmed offers. The pages do not establish a model year or per-trim mapping for these values. NEDC figures are laboratory-cycle figures; actual range depends on operating conditions.

## VF Wild scope

The page describes VF Wild as a range-extended electric pickup (REEV), not simply as a battery-only EV. Its page copy reports an LFP battery of 46.4 kWh, over 250 km in pure-electric mode, up to 1,000 km combined range, 160 kW, 280 Nm, 750 kg payload, dimensions 5376 × 2069 × 1873 mm, and a starting price of 860,000,000 VND. The product content also says its imagery is pre-commercial and that product information can change.

The current page content reviewed here does not establish trim structure, the test cycle behind the stated ranges, AC/DC charging ratings or times, warranty, or a color palette. These are stored as page observations only. They are not activated in the EV product-card catalog, and the 1,000 km combined figure is not treated as pure-electric range or as an NEDC/WLTP value.

## Runtime status

The verified model-color catalog now includes VF 2 and VF MPV 7, and the chat model parser routes those explicit model names to that reviewed color evidence. This does not add their prices or specifications to the vehicle-card catalog or vector index. VF 5's current color record remains in place. VF Wild has no reviewed color palette to activate.
