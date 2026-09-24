from pathlib import Path

import pandas as pd

from aicapitalgraph.analysis import (
    ProjectPaths,
    anomaly_scores,
    company_panel,
    load_relationships,
    load_universe,
    run_analysis,
    validate_inputs,
)


ROOT = Path(__file__).resolve().parents[1]


def test_universe_is_complete_and_clean() -> None:
    universe = load_universe(ROOT / "data/raw/fortune500_2024.csv")
    assert len(universe) == 500
    assert universe["rank"].tolist() == list(range(1, 501))
    assert universe["company"].nunique() == 500
    assert universe["revenue_usd_millions"].notna().all()


def test_relationships_are_traceable() -> None:
    relationships = load_relationships(ROOT / "data/curated/ai_relationships.csv")
    sources = pd.read_csv(ROOT / "data/sources/source_registry.csv")
    assert len(relationships) >= 35
    assert set(relationships["source_id"]).issubset(set(sources["source_id"]))
    assert relationships["evidence_strength"].min() >= 3


def test_validation_and_panel() -> None:
    universe = load_universe(ROOT / "data/raw/fortune500_2024.csv")
    relationships = load_relationships(ROOT / "data/curated/ai_relationships.csv")
    ownership = pd.read_csv(ROOT / "data/curated/ownership_relationships.csv")
    assert validate_inputs(universe, relationships, ownership) == []
    panel = company_panel(universe, relationships)
    assert panel["documented_ai_company"].isin([0, 1]).all()
    assert panel["documented_ai_company"].sum() >= 20


def test_anomaly_scoring_is_bounded_and_explainable() -> None:
    relationships = load_relationships(ROOT / "data/curated/ai_relationships.csv")
    scores = anomaly_scores(relationships)
    assert scores["anomaly_score"].between(0, 100).all()
    assert scores["screening_hypothesis"].str.len().min() > 20
    assert scores["alternative_explanation"].str.len().min() > 20
    assert scores.iloc[0]["anomaly_score"] >= scores.iloc[-1]["anomaly_score"]


def test_end_to_end_pipeline(tmp_path: Path) -> None:
    for directory in ["data/raw", "data/curated", "reports"]:
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    for relative in [
        "data/raw/fortune500_2024.csv",
        "data/curated/ai_relationships.csv",
        "data/curated/ownership_relationships.csv",
    ]:
        (tmp_path / relative).write_bytes((ROOT / relative).read_bytes())
    summary = run_analysis(ProjectPaths(tmp_path))
    assert summary["universe_companies"] == 500
    assert (tmp_path / "results/correlation_results.csv").exists()
    assert (tmp_path / "figures/capitalgraph_network.png").stat().st_size > 10_000
    assert "Bottom Line" in (tmp_path / "reports/generated_findings.md").read_text()

