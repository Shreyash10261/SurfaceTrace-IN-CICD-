"""CLI tests for SurfaceTrace-IN (st.cli).

Owned by Shreyash.
Tests all CLI subcommands via typer.testing.CliRunner.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from st.cli import app
from st.db import init_db
from tests.helpers import make_valid_v3

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "SurfaceTrace-IN" in result.stdout


def test_cli_collect_and_fetch_and_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_cli.db"
    init_db(db_file)
    monkeypatch.setenv("DATABASE_PATH", str(db_file))

    valid_addr = make_valid_v3()

    # Mock seed collector
    monkeypatch.setattr(
        "st.collect.seed.search",
        lambda *args, **kwargs: [
            {"url": "https://test.org/seed1", "title": "Seed 1", "source": "seed", "query": "seed"}
        ],
    )
    # Mock other collectors to return empty
    monkeypatch.setattr("st.collect.web_search.search", lambda *args, **kwargs: [])
    monkeypatch.setattr("st.collect.ahmia.search", lambda *args, **kwargs: [])
    monkeypatch.setattr("st.collect.github.search", lambda *args, **kwargs: [])
    monkeypatch.setattr("st.collect.rss.search", lambda *args, **kwargs: [])

    # Mock fetch_url
    monkeypatch.setattr(
        "st.fetch.fetch_url",
        lambda url: (f"Disclosing terrorism in india footprint at {valid_addr} today.", "Report Title"),
    )
    monkeypatch.setattr("st.fetch.is_allowed_by_robots", lambda *args: True)

    # 1. Run collect
    res_collect = runner.invoke(app, ["collect", "--source", "seed"])
    assert res_collect.exit_code == 0
    assert "Collect stage complete" in res_collect.stdout

    # 2. Run fetch
    res_fetch = runner.invoke(app, ["fetch", "--limit", "10"])
    assert res_fetch.exit_code == 0
    assert "Fetch stage complete" in res_fetch.stdout

    # 3. Run extract
    res_extract = runner.invoke(app, ["extract"])
    assert res_extract.exit_code == 0
    assert "Extract stage complete" in res_extract.stdout

    # 4. Run score
    res_score = runner.invoke(app, ["score"])
    assert res_score.exit_code == 0
    assert "Score stage complete" in res_score.stdout

    # 5. Run evaluate
    res_eval = runner.invoke(app, ["evaluate"])
    assert res_eval.exit_code == 0
    assert "SurfaceTrace-IN Evaluation Results" in res_eval.stdout

    # 6. Run export
    export_path = tmp_path / "cli_leads.csv"
    res_exp = runner.invoke(app, ["export", "--path", str(export_path)])
    assert res_exp.exit_code == 0
    assert export_path.exists()

