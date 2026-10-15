# Methodology, assumptions and data dictionary

## Scenario and provenance

USGS event ci38457511, Ridgecrest, 6 July 2019 UTC (5 July local time), magnitude 7.1. The pinned USGS Atlas ShakeMap version is encoded in the grid URL. It can differ from the original event-time product. `data/raw/source.json` records download UTC, source URL and SHA-256; `outputs/validation.json` records the actual grid hash used by each run. Retain both when distributing results. Cached data is never silently replaced following a network failure.

The complete USGS grid contains longitude, latitude and modeled shaking attributes. This project uses MMI (Modified Mercalli Intensity). Epicentral distance buffers are not used as substitutes for shaking intensity. Grid values are converted into axis-aligned cell footprints centered on each grid point, using the published nominal grid spacing. MMI 5≤x<6 is labeled V, 6≤x<7 VI, and x≥7 VII+. These are analyst-defined threshold bands on continuous MMI, rather than rounding each cell to an integer intensity.

Cells are snapped to 0.000001 degree precision before dissolving. Points on shared boundaries take the higher band; each property is counted once. Points within the full grid footprint outside these zones are labeled Below V. Points outside the grid footprint are explicitly Outside ShakeMap and excluded from the VI+ exposure metric, while retained in accepted total value. A one-cell footprint approximation at zone boundaries is a material spatial-resolution limitation.

## Property input contract

CSV header names are case-sensitive. UTF-8 with decimal-point numeric values. Each row represents a property, not a policy or coverage section; TIV must already be consolidated to one property and expressed in USD. No currency conversion is performed.

| Field | Rule |
|---|---|
| property_id | Nonblank unique property identifier; exact duplicate copies removed first |
| city | Nonblank descriptive city; not inferred from coordinates |
| longitude | Finite WGS84 x coordinate, -180 to 180 and within study extent |
| latitude | Finite WGS84 y coordinate, -90 to 90 and within study extent |
| occupancy | Residential, Commercial or Industrial |
| construction | Wood, Masonry or Concrete |
| year_built | Integer, 1800–2026 |
| tiv_usd | Finite, positive total insured value in USD |

Study extent is longitude [-125,-114], latitude [32,42]. It detects gross scope errors but includes ocean and neighboring jurisdictions. It is not a cadastral or land validation. Missing, swapped and invalid coordinates are quarantined, never automatically repaired. Two distinct records sharing an ID are both quarantined; choosing a winner would conceal an unresolved value conflict. Exact duplicates compare required input columns only and keep the first source occurrence. Each output retains the source CSV row number including the header.

Rule counts overlap. Disposition counts do not: raw = accepted + removed duplicate copies + quarantined. All attributes are required in this demonstration, so an occupancy exception also removes the record's TIV from accepted exposure. Excluded exposures are not zero-valued properties; report the quarantine population beside accepted metrics.

## Concentration and value interpretation

Reproject accepted points from EPSG:4326 to California Albers EPSG:3310, assign floor(x/10000), floor(y/10000), and aggregate counts and TIV within fixed 10 km square cells. Cell IDs refer to this fixed origin and CRS, not official administrative zones. Portfolio shares use accepted TIV as denominator. The Streamlit concentration tab recalculates shares for its filtered portfolio.

TIV in VI+ is the sum of asset values in this historical scenario's VI and VII+ zones. There are no damage curves, deductibles, vulnerability functions, return periods or modeled losses. Occupancy, construction and vintage are available for segmentation; they do not alter the hazard value. Event shaking may differ from future shaking at the same site. Synthetic locations do not verify the existence of buildings or land parcels.

## Profiling and improvement priorities

The seeded portfolio intentionally includes missing IDs and coordinates, invalid coordinates, swapped axes, nonpositive values, invalid vintage, missing occupancy, out-of-scope locations, exact duplicates and conflicting IDs. Review `validation.json`, `exceptions.csv` and `quarantine.csv`. Add source-system ID uniqueness, coordinate bounds and currency/value controls. Resolve quarantine records with authoritative owners before including their exposures. Extend future work with address geocoding confidence, real administrative boundaries, additional perils, official probabilistic hazard surfaces and documented source refresh policies.
