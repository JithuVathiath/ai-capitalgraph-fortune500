# Methodology and Limitations

## Research Design

This is an exploratory, cross-sectional evidence study with a reproducible computation layer. It combines:

- a 2024 Fortune 500 company and financial baseline;
- primary-source AI deployment and investment announcements dated through 24 September 2026;
- the FTC's 2025 Section 6(b) staff report on three cloud/model partnerships; and
- a public-equity ownership case study from Berkshire Hathaway's Q2 2026 Form 13F.

The editions intentionally differ. The older company baseline provides a complete, openly reusable financial cross-section. The evidence layer captures later AI events. The company panel therefore asks whether a 2024 large-company characteristic is associated with evidence observed by the 2026 cut-off; it is not a same-period causal design.

## Evidence Rules

A relationship is included only when a regulator, filing, company, or technology provider names both parties and describes a concrete investment, deployment or commercial collaboration. Provider case studies count as primary commercial evidence but may contain selection and marketing bias.

Evidence strength uses a four-point scale:

- **4:** regulator report or regulatory filing;
- **3:** named company/provider primary source;
- **2:** reputable secondary reporting with direct attribution; and
- **1:** discovery lead only, excluded from the committed register.

All committed AI records score at least 3.

## Company-Universe Quality Control

The upstream open dataset contained 500 rows but repeated rank 407 for Westinghouse Air Brake Technologies, leaving rank 408 absent. The row order, independent index and neighbouring ranks showed that this was a transcription error; the local research copy changes that company's rank to 408. The pipeline tests row count, company uniqueness and contiguous ranks on every run.

## Variable Construction

`documented_ai_company` equals one when a universe company appears as an actor in at least one model-adoption, equity-and-commercial or venture-investment edge. It equals zero otherwise. Zero means “not present in this register,” not verified non-adoption.

Financial strings are converted to USD millions. Negative profit is retained for the raw panel; log-transformed correlation inputs clip negative values at zero because `log1p` is otherwise undefined for losses below -1.

## Association Test

For revenue, employees, market capitalisation and profit, the pipeline computes Spearman's rank correlation between `log1p(scale)` and the binary evidence indicator. A two-sided permutation p-value uses 5,000 deterministic label permutations with seed 42. The test asks whether the observed rank association is unusual under exchangeability; it does not correct evidence-discovery bias.

No multiple-testing adjustment is applied because the four results are presented as a related exploratory family, not confirmatory hypothesis tests. A future paper should preregister hypotheses, broaden evidence collection and apply false-discovery control.

## Network Construction

Nodes are companies and AI providers. Directed edges point from adopter/investor/owner to provider/issuer. The combined graph contains relationship categories that are economically different; metrics must therefore be interpreted with their edge construction in mind.

- degree is the observed number of adjacent relationships;
- PageRank is computed without monetary weights to prevent large disclosed positions from overwhelming adoption relationships; and
- betweenness is descriptive on the observed directed graph.

The network visual shows only the 24 highest-degree nodes for legibility. CSV outputs include all nodes.

## Ownership Scope

Form 13F does not establish complete beneficial ownership. It covers specified 13(f) securities reported by qualifying institutional investment managers, is periodic, may aggregate affiliated managers, and excludes many private, short, derivative and non-US exposures. The repository uses one high-quality filer case study rather than claiming a complete Fortune 500 ownership map.

Reported values were aggregated across Berkshire's manager rows and, where applicable, share classes. The source filing should control if any transcription conflict appears.

## Strategic-Anomaly Score

Only investment and strategic-commercial edges are scored. The score combines:

- up to 35 points for disclosed amount using log scaling; and
- fixed, transparent weights for structural flags: reciprocal cloud spend (15), control rights (10), information rights (10), undisclosed amount (10), switching cost (8), preferred infrastructure (8), platform optionality (6), and multi-year commitment (5).

Scores are capped at 100. Thresholds are 0–25 routine, above 25–50 review, and above 50 priority review. The weights are a governance-screening heuristic, not an estimated probability. The output preserves every component, a strategic hypothesis and an alternative explanation.

## Main Limitations

1. **Ascertainment bias:** large and successful deployments are more likely to appear in provider case studies.
2. **Temporal mismatch:** 2024 financial variables precede some 2025–2026 AI evidence.
3. **Disclosure gaps:** many contracts, venture amounts and technical dependencies are private.
4. **Provider naming:** “ChatGPT,” “OpenAI models,” Azure OpenAI and embedded model access are distinct deployment forms.
5. **No performance outcome:** the study does not estimate productivity, return on investment or stock-price effects.
6. **Incomplete ownership:** one 13F case study is not a universal corporate ownership network.
7. **No causal identification:** correlations may reflect size, sector, disclosure, technology intensity or researcher coverage.
8. **Intent is unobserved:** anomaly flags do not reveal motive or wrongdoing.

## Reproduction

Run the tests before analysis. The test suite validates data contracts, source traceability, score bounds and complete output generation. CI then reruns the pipeline and checks that generated files are unchanged.

