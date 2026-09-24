# Data Guide

## `raw/fortune500_2024.csv`

The 500-company analytic baseline comes from the MIT-licensed `evaberezovska/fortune-company-analysis` repository. It retains the source's rank, revenue, profit, employees, sector, location, market value, website, ticker and asset fields.

One transparent correction is applied: Westinghouse Air Brake Technologies is changed from duplicate rank 407 to rank 408. The source row index, row order and absent rank support the correction. Tests enforce a contiguous 1–500 range.

`raw/fortune500_2025.json` is a CC BY 4.0 secondary directory retained for provenance and future comparison; it is not used in the analysis because validation identified revenue/rank consistency problems in its lower-ranked records.

## `curated/ai_relationships.csv`

Each row is an evidence-backed directed relationship. Blank transaction amounts mean “not publicly disclosed,” never zero. `strategic_flags` are pipe-separated observable structural characteristics used by the explainable screen.

## `curated/ownership_relationships.csv`

Selected Fortune-company issuers from Berkshire Hathaway's Q2 2026 Form 13F. Values aggregate manager rows and relevant share classes. This is a focused ownership case study, not a complete beneficial-ownership database.

## `sources/source_registry.csv`

The provenance table records source IDs, publishers, dates, URLs, scope and a quality grade. Analysis rows reference source IDs so claims can be audited without searching narrative text.

