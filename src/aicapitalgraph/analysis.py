from __future__ import annotations

import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "aicapitalgraph-mpl"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ALIASES = {
    "Alphabet Inc.": "Alphabet",
    "Amazon.com": "Amazon",
    "Bank of New York Mellon": "Bank of New York Mellon",
    "Bristol-Myers Squibb": "Bristol-Myers Squibb",
    "Cisco Systems": "Cisco",
    "Coca Cola": "Coca-Cola",
    "Exxon Mobil": "Exxon Mobil",
    "International Business Machines": "IBM",
    "Lowe's": "Lowe's",
    "Lumen Technologies": "Lumen Technologies",
    "Procter & Gamble": "Procter & Gamble",
    "T-Mobile US": "T-Mobile US",
    "Thermo Fisher Scientific": "Thermo Fisher Scientific",
}


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def universe(self) -> Path:
        return self.root / "data/raw/fortune500_2024.csv"

    @property
    def relationships(self) -> Path:
        return self.root / "data/curated/ai_relationships.csv"

    @property
    def ownership(self) -> Path:
        return self.root / "data/curated/ownership_relationships.csv"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def figures(self) -> Path:
        return self.root / "figures"


def _money_to_float(value: object) -> float:
    if pd.isna(value):
        return np.nan
    match = re.search(r"-?[0-9.]+", str(value).replace(",", ""))
    return float(match.group()) if match else np.nan


def normalize_name(value: object) -> str:
    text = str(value).strip()
    return ALIASES.get(text, text)


def load_universe(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    data = data.loc[:, ~data.columns.str.startswith("Unnamed")].copy()
    expected = {"company", "rank", "revenues", "employees", "sector", "market_cap", "profits", "assets"}
    missing = expected.difference(data.columns)
    if missing:
        raise ValueError(f"Universe is missing required columns: {sorted(missing)}")
    data["company"] = data["company"].map(normalize_name)
    for source, target in [
        ("revenues", "revenue_usd_millions"),
        ("profits", "profit_usd_millions"),
        ("market_cap", "market_cap_usd_millions"),
        ("assets", "assets_usd_millions"),
    ]:
        data[target] = data[source].map(_money_to_float)
    data["employees"] = pd.to_numeric(data["employees"], errors="coerce")
    data["rank"] = pd.to_numeric(data["rank"], errors="raise").astype(int)
    return data.sort_values("rank").reset_index(drop=True)


def load_relationships(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    data["actor"] = data["actor"].map(normalize_name)
    data["target"] = data["target"].map(normalize_name)
    data["amount_usd_millions"] = pd.to_numeric(data["amount_usd_millions"], errors="coerce")
    data["evidence_strength"] = pd.to_numeric(data["evidence_strength"], errors="raise")
    return data


def validate_inputs(universe: pd.DataFrame, relationships: pd.DataFrame, ownership: pd.DataFrame) -> list[str]:
    problems: list[str] = []
    if len(universe) != 500 or universe["rank"].nunique() != 500:
        problems.append("The universe must contain 500 unique ranks.")
    if universe["company"].duplicated().any():
        problems.append("Company names must be unique in the universe.")
    if not universe["rank"].tolist() == list(range(1, 501)):
        problems.append("Ranks must be contiguous from 1 to 500.")
    required_types = {"model_adoption", "equity_and_commercial", "venture_investment", "strategic_commercial"}
    if not required_types.issubset(set(relationships["relationship_type"])):
        problems.append("Relationship evidence is missing a required research category.")
    if relationships[["actor", "target", "source_id"]].isna().any().any():
        problems.append("Relationship evidence contains a missing actor, target, or source.")
    if (ownership["reported_value_usd"] <= 0).any():
        problems.append("Ownership values must be positive.")
    return problems


def _permutation_spearman(x: pd.Series, y: pd.Series, seed: int = 42, iterations: int = 5000) -> tuple[float, float]:
    mask = x.notna() & y.notna()
    x_values = x[mask].to_numpy(dtype=float)
    y_values = y[mask].to_numpy(dtype=float)
    if len(np.unique(y_values)) < 2:
        return float("nan"), float("nan")
    observed = float(spearmanr(x_values, y_values).statistic)
    rng = np.random.default_rng(seed)
    extreme = 0
    for _ in range(iterations):
        shuffled = rng.permutation(y_values)
        permuted = float(spearmanr(x_values, shuffled).statistic)
        extreme += abs(permuted) >= abs(observed)
    return observed, (extreme + 1) / (iterations + 1)


def company_panel(universe: pd.DataFrame, relationships: pd.DataFrame) -> pd.DataFrame:
    adoption = relationships[relationships["relationship_type"] == "model_adoption"]
    investment = relationships[relationships["relationship_type"].isin(["equity_and_commercial", "venture_investment"])]
    adoption_counts = adoption.groupby("actor").size().rename("documented_adoption_edges")
    investment_counts = investment.groupby("actor").size().rename("documented_investment_edges")
    panel = universe.merge(adoption_counts, how="left", left_on="company", right_index=True)
    panel = panel.merge(investment_counts, how="left", left_on="company", right_index=True)
    for column in ["documented_adoption_edges", "documented_investment_edges"]:
        panel[column] = panel[column].fillna(0).astype(int)
    panel["documented_ai_company"] = (
        panel["documented_adoption_edges"] + panel["documented_investment_edges"] > 0
    ).astype(int)
    return panel


def correlation_results(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable in ["revenue_usd_millions", "employees", "market_cap_usd_millions", "profit_usd_millions"]:
        rho, p_value = _permutation_spearman(
            np.log1p(panel[variable].clip(lower=0)), panel["documented_ai_company"]
        )
        rows.append(
            {
                "exposure_variable": variable,
                "outcome": "documented_ai_company",
                "spearman_rho": rho,
                "permutation_p_value": p_value,
                "n": int(panel[[variable, "documented_ai_company"]].dropna().shape[0]),
                "interpretation": "descriptive association; evidence-discovery bias prevents causal interpretation",
            }
        )
    return pd.DataFrame(rows)


FLAG_WEIGHTS = {
    "reciprocal_cloud_spend": 15,
    "control_rights": 10,
    "information_rights": 10,
    "switching_cost": 8,
    "preferred_infrastructure": 8,
    "undisclosed_amount": 10,
    "platform_optionality": 6,
    "multi_year_commitment": 5,
}


def anomaly_scores(relationships: pd.DataFrame) -> pd.DataFrame:
    strategic = relationships[
        relationships["relationship_type"].isin(
            ["equity_and_commercial", "venture_investment", "strategic_commercial"]
        )
    ].copy()
    maximum = strategic["amount_usd_millions"].max()
    strategic["amount_component"] = strategic["amount_usd_millions"].fillna(0).map(
        lambda value: 35 * math.log1p(value) / math.log1p(maximum) if maximum > 0 else 0
    )

    def flag_component(flags: object) -> float:
        active = set(str(flags).split("|")) if pd.notna(flags) else set()
        return float(sum(weight for flag, weight in FLAG_WEIGHTS.items() if flag in active))

    strategic["structural_component"] = strategic["strategic_flags"].map(flag_component)
    strategic["anomaly_score"] = (strategic["amount_component"] + strategic["structural_component"]).clip(upper=100).round(1)
    strategic["review_tier"] = pd.cut(
        strategic["anomaly_score"], bins=[-0.1, 25, 50, 100], labels=["routine", "review", "priority_review"]
    ).astype(str)
    strategic["screening_hypothesis"] = strategic.apply(
        lambda row: (
            "Investment may secure infrastructure demand, distribution, and strategic information advantages."
            if row["relationship_type"] == "equity_and_commercial"
            else "Portfolio position may preserve access to multiple technical pathways and future partners."
            if row["relationship_type"] == "venture_investment"
            else "Long-duration commercial alignment may secure supply and specialized AI capacity."
        ),
        axis=1,
    )
    strategic["alternative_explanation"] = strategic["relationship_type"].map(
        {
            "equity_and_commercial": "Scale economics and joint product delivery can explain the same structure without anti-competitive intent.",
            "venture_investment": "Conventional venture diversification and financial return may be sufficient explanations.",
            "strategic_commercial": "Supply-chain resilience and ordinary procurement planning may explain the commitment.",
        }
    )
    return strategic.sort_values(["anomaly_score", "actor"], ascending=[False, True])


def build_network_metrics(relationships: pd.DataFrame, ownership: pd.DataFrame) -> tuple[pd.DataFrame, nx.DiGraph]:
    graph = nx.DiGraph()
    for row in relationships.itertuples(index=False):
        graph.add_edge(
            row.actor,
            row.target,
            category=row.relationship_type,
            weight=float(row.amount_usd_millions) if pd.notna(row.amount_usd_millions) else 1.0,
        )
    for row in ownership.itertuples(index=False):
        graph.add_edge(
            normalize_name(row.owner),
            normalize_name(row.issuer),
            category="public_equity_holding",
            weight=float(row.reported_value_usd) / 1_000_000,
        )
    pagerank = nx.pagerank(graph, alpha=0.85, weight=None)
    betweenness = nx.betweenness_centrality(graph, normalized=True, weight=None)
    rows = []
    for node in graph.nodes:
        rows.append(
            {
                "node": node,
                "in_degree": graph.in_degree(node),
                "out_degree": graph.out_degree(node),
                "total_degree": graph.degree(node),
                "pagerank": pagerank[node],
                "betweenness": betweenness[node],
            }
        )
    metrics = pd.DataFrame(rows).sort_values(["total_degree", "pagerank"], ascending=False)
    return metrics, graph


def industry_summary(panel: pd.DataFrame) -> pd.DataFrame:
    summary = (
        panel.groupby("sector", as_index=False)
        .agg(
            companies=("company", "size"),
            documented_ai_companies=("documented_ai_company", "sum"),
            median_revenue_usd_millions=("revenue_usd_millions", "median"),
        )
    )
    summary["documented_ai_evidence_rate"] = summary["documented_ai_companies"] / summary["companies"]
    return summary.sort_values(["documented_ai_evidence_rate", "companies"], ascending=False)


def create_figures(
    panel: pd.DataFrame,
    industry: pd.DataFrame,
    ownership: pd.DataFrame,
    graph: nx.DiGraph,
    figures_dir: Path,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    top = industry[industry["companies"] >= 5].head(12).sort_values("documented_ai_evidence_rate")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top["sector"], top["documented_ai_evidence_rate"] * 100, color="#4f46e5")
    ax.set_xlabel("Companies with documented AI evidence (%)")
    ax.set_title("Documented AI Evidence by Fortune 500 Sector")
    ax.text(0, -0.16, "Evidence coverage is not an estimate of true adoption.", transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    fig.savefig(figures_dir / "ai_evidence_by_sector.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    holdings = ownership.nlargest(12, "reported_value_usd").sort_values("reported_value_usd")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(holdings["issuer"], holdings["reported_value_usd"] / 1e9, color="#0891b2")
    ax.set_xlabel("Reported value at 30 June 2026 (USD billions)")
    ax.set_title("Berkshire Hathaway: Selected Fortune 500 Equity Holdings")
    fig.tight_layout()
    fig.savefig(figures_dir / "berkshire_holdings.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    degree_nodes = sorted(graph.nodes, key=lambda node: graph.degree(node), reverse=True)[:24]
    subgraph = graph.subgraph(degree_nodes).copy()
    positions = nx.spring_layout(subgraph, seed=42, k=0.9)
    categories = nx.get_edge_attributes(subgraph, "category")
    colors = [
        "#dc2626" if "investment" in categories[edge] or categories[edge] == "equity_and_commercial"
        else "#0891b2" if categories[edge] == "public_equity_holding"
        else "#64748b"
        for edge in subgraph.edges
    ]
    sizes = [450 + 140 * subgraph.degree(node) for node in subgraph.nodes]
    fig, ax = plt.subplots(figsize=(13, 9))
    nx.draw_networkx(
        subgraph,
        positions,
        ax=ax,
        node_color="#eef2ff",
        edgecolors="#312e81",
        node_size=sizes,
        font_size=8,
        arrowsize=13,
        edge_color=colors,
        width=1.4,
    )
    ax.legend(
        handles=[
            Line2D([0], [0], color="#dc2626", lw=2, label="Strategic investment / commitment"),
            Line2D([0], [0], color="#0891b2", lw=2, label="Public-equity holding"),
            Line2D([0], [0], color="#64748b", lw=2, label="Model deployment"),
        ],
        loc="lower right",
        frameon=True,
    )
    ax.set_title("AI CapitalGraph: High-Connectivity Evidence Network")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(figures_dir / "capitalgraph_network.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_generated_report(
    path: Path,
    panel: pd.DataFrame,
    relationships: pd.DataFrame,
    correlations: pd.DataFrame,
    anomalies: pd.DataFrame,
    metrics: pd.DataFrame,
    ownership: pd.DataFrame,
) -> None:
    adopters = int(panel["documented_ai_company"].sum())
    adoption_edges = int((relationships["relationship_type"] == "model_adoption").sum())
    disclosed = relationships["amount_usd_millions"].sum(min_count=1)
    top_nodes = ", ".join(metrics.head(5)["node"].tolist())
    top_anomaly = anomalies.iloc[0]
    strongest = correlations.iloc[correlations["spearman_rho"].abs().argmax()]
    text = f"""# Generated Findings Snapshot

Generated deterministically from the committed evidence on **24 September 2026**.

## What the Data Shows

- The research register contains **{len(relationships)}** AI relationships, including **{adoption_edges}** deployment/adoption edges.
- **{adopters} of 500** universe companies have at least one directly documented AI adoption or investment edge. This is a lower-bound evidence count, not a market-adoption rate.
- Disclosed transaction amounts in the register total **${disclosed:,.0f} million**. Undisclosed venture positions are deliberately excluded from that sum.
- The SEC ownership case study covers **{len(ownership)}** Fortune-company issuers with **${ownership['reported_value_usd'].sum()/1e9:,.1f} billion** in aggregated reported value.
- The most connected nodes in the combined network are: **{top_nodes}**.

## Exploratory Association

The largest absolute company-scale association is **{strongest['exposure_variable']}** versus documented AI evidence: Spearman rho **{strongest['spearman_rho']:.3f}**, permutation p-value **{strongest['permutation_p_value']:.4f}** (n={int(strongest['n'])}). This cannot establish causation and is likely influenced by public-disclosure and research-coverage bias.

## Highest-Priority Screening Signal

**{top_anomaly['actor']} → {top_anomaly['target']}** scores **{top_anomaly['anomaly_score']:.1f}/100**. The score reflects disclosed scale and structural flags; it is a review-priority indicator, not proof of misconduct or a hidden agenda.

## Bottom Line

The clearest pattern is a two-layer enterprise AI market: a small set of infrastructure/model providers accumulate investment, distribution and compute ties, while large operating companies adopt several competing model ecosystems. Reciprocal cloud-spend and information-right structures warrant governance attention, but ordinary scale economics and joint product delivery remain credible alternative explanations.
"""
    path.write_text(text, encoding="utf-8")


def run_analysis(paths: ProjectPaths) -> dict[str, object]:
    paths.results.mkdir(parents=True, exist_ok=True)
    paths.figures.mkdir(parents=True, exist_ok=True)
    universe = load_universe(paths.universe)
    relationships = load_relationships(paths.relationships)
    ownership = pd.read_csv(paths.ownership)
    ownership["owner"] = ownership["owner"].map(normalize_name)
    ownership["issuer"] = ownership["issuer"].map(normalize_name)
    problems = validate_inputs(universe, relationships, ownership)
    if problems:
        raise ValueError("Input validation failed: " + " ".join(problems))

    panel = company_panel(universe, relationships)
    correlations = correlation_results(panel)
    anomalies = anomaly_scores(relationships)
    metrics, graph = build_network_metrics(relationships, ownership)
    industries = industry_summary(panel)

    panel.to_csv(paths.results / "company_ai_evidence_panel.csv", index=False)
    correlations.to_csv(paths.results / "correlation_results.csv", index=False)
    anomalies.to_csv(paths.results / "strategic_anomaly_scores.csv", index=False)
    metrics.to_csv(paths.results / "network_metrics.csv", index=False)
    industries.to_csv(paths.results / "industry_summary.csv", index=False)
    create_figures(panel, industries, ownership, graph, paths.figures)
    write_generated_report(
        paths.root / "reports/generated_findings.md",
        panel,
        relationships,
        correlations,
        anomalies,
        metrics,
        ownership,
    )

    summary = {
        "universe_companies": int(len(universe)),
        "relationships": int(len(relationships)),
        "documented_company_count": int(panel["documented_ai_company"].sum()),
        "ownership_edges": int(len(ownership)),
        "network_nodes": int(graph.number_of_nodes()),
        "network_edges": int(graph.number_of_edges()),
        "data_cutoff": "2026-09-24",
        "random_seed": 42,
    }
    (paths.results / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
