# Official product-page supplementation: VF5, VF6, VF8 and VF9

Reviewed 2026-10-19 from the five official SRC-009 product pages supplied for this task. The web reader supplied the HTML content after direct Playwright HTML requests returned 403. Playwright downloaded all five linked brochures; acquisition statuses and SHA-256 values are recorded in `data/acquired/vf5-vf6-vf8-vf9-product-2026-10-19/manifest.json`.

Reviewed model facts and source conflicts are retained in `fixtures/knowledge/source_reviews/vf5-vf6-vf8-vf9-product-2026-10-19.json`. Brochure tables were rendered and visually inspected for VF5 page 1, VF6 page 11, VF8 legacy page 18, VF8 The All New 2026 page 6 and VF9 page 14.

## Runtime change

The existing reviewed color-answer path now serves model-level exterior palettes for VF6, VF8 and VF9 in Vietnamese and English. Answers remain partial and explicitly do not claim that each trim/year has every color or that a color is in dealer stock. VF5 colors were already covered. VF8 The All New 2026 remains a separate archived generation and is not exposed as the legacy VF8 Eco/Plus catalog.

## Source observations and conflict handling

- VF5 product page lists 326 km NEDC and dimensions 3967 x 1723 x 1579 mm. The linked older brochure says 326.4 km, without a cycle in that paragraph, and 1578 mm height. The current page values are retained in the structured observation.
- VF6 product page lists Eco/Plus prices 646m/699m VND, NEDC range 485/460 km and 25-minute 10–70% charge times. Brochure page 11 confirms 59.6 kWh, 130/150 kW and 250/310 Nm. Accessories rated 3.5/7.4 kW are kept distinct from the 7.2 kW maximum AC onboard charge rating.
- Legacy VF8 product page lists Eco/Plus 635/475 km NEDC. The linked brochure page 18 instead lists Eco 562 km NEDC and Plus 457 km WLTP. These cycle and configuration differences are not converted or reconciled; page values already present in the runtime catalog remain unchanged.
- VF8 The All New 2026 is a single published configuration: page price 899m VND, 480 km NEDC; brochure page 6 says 480–500 km depending on version and under 30 minutes from 10–70% at a 250 kW station. The brochure does not establish named trims for the upper figures, so no Eco/Plus mapping was inferred. Its 12 listed color combinations are stored under a separate generation key.
- VF9 product rows and brochure page 14 confirm Eco/Plus 626/602 km WLTP, 300 kW and 620 Nm. A generic product-page footnote says NEDC, while the variant rows and brochure specify WLTP; the explicit variant cycle is preserved. Brochure lists the Plus seating configurations as 7 and 6; current orderability and price applicability of the 6-seat configuration are unknown.

## Remaining limits

The pages do not establish dealer stock, VIN-specific configuration, current appointment availability, service tariffs, or year-specific maintenance schedules. Product-page warranty headlines are archived as observations and were not promoted to detailed battery, commercial-use, exclusions or claims policy. Dimensions and equipment beyond existing catalog capabilities are stored for future ingest; the runtime change in this task is limited to the reviewed color answers.

## Verification

The new targeted suite and adjacent VF3/VF7 regression suite passed together: 14 passed. A follow-up probe confirms VF6, VF8 and VF9 color queries retrieve SRC-009 and return partial status, and four legacy VF8 generation spellings are rejected by the legacy reviewed-gap selector. The API-level SQLite smoke rerun was not completed because automatic approval review stopped the escalation after the host usage limit was reached. No PostgreSQL database was used.
