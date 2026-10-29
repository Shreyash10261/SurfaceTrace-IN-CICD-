"""CLI module for SurfaceTrace-IN.

Owned by Shreyash.
Provides the Typer CLI commands: collect, fetch, extract, score, run-all, export, evaluate.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from st.db import init_db, log_run, save_hits
from st.evaluate import evaluate as run_eval
from st.export import export_csv
from st.extract import extract_pending
from st.fetch import fetch_pending
from st.score import score_all

app = typer.Typer(
    name="st",
    help="SurfaceTrace-IN: Surface-web discovery pipeline for .onion footprints.",
    add_completion=False,
)

DEFAULT_QUERIES_PATH = Path(__file__).resolve().parents[2] / "config" / "queries.txt"


def load_queries(path: Path | str | None = None) -> list[str]:
    """Load query strings from queries.txt."""
    q_path = Path(path) if path else DEFAULT_QUERIES_PATH
    queries = []
    if q_path.exists():
        with open(q_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    queries.append(line)
    return queries or ['"terrorism in India" "dark web" forum']


@app.command()
def collect(
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Specific collector to run: seed, web_search, ahmia, github, rss"
    ),
    queries_file: Optional[Path] = typer.Option(None, "--queries", help="Custom queries.txt file"),
) -> None:
    """Run search queries on surface-web collectors and save result URLs."""
    init_db()
    started_at = datetime.now(timezone.utc).isoformat()
    queries = load_queries(queries_file)

    from st.collect import ahmia, github, rss, seed, web_search

    collector_map = {
        "seed": seed.search,
        "web_search": web_search.search,
        "ahmia": ahmia.search,
        "github": github.search,
        "rss": rss.search,
    }

    if source:
        if source not in collector_map:
            typer.echo(f"Error: Unknown source '{source}'. Available: {list(collector_map.keys())}")
            raise typer.Exit(code=1)
        active_collectors = {source: collector_map[source]}
    else:
        active_collectors = collector_map

    total_inserted = 0
    error_msg = None

    try:
        # Run seed collector once (it ignores query)
        if "seed" in active_collectors:
            seed_hits = active_collectors["seed"]("", max_results=50)
            total_inserted += save_hits(seed_hits)

        # Run query-based collectors
        for src_name, search_fn in active_collectors.items():
            if src_name == "seed":
                continue
            for query in queries[:10]:  # Cap per run to manage quotas and speed
                try:
                    hits = search_fn(query, max_results=10)
                    total_inserted += save_hits(hits)
                except Exception as e:
                    typer.echo(f"Warning: collector {src_name} failed on '{query}': {e}")

        typer.echo(f"✓ Collect stage complete: {total_inserted} new documents saved.")
    except Exception as e:
        error_msg = str(e)
        typer.echo(f"Error during collect stage: {e}")
        raise
    finally:
        log_run("collect", items=total_inserted, error=error_msg, started_at=started_at)


@app.command("fetch")
def fetch_cmd(
    limit: int = typer.Option(200, "--limit", "-n", help="Maximum documents to fetch"),
) -> None:
    """Fetch content for pending documents."""
    init_db()
    typer.echo(f"Fetching up to {limit} pending documents...")
    fetched = fetch_pending(limit=limit)
    typer.echo(f"✓ Fetch stage complete: {fetched} documents successfully fetched.")


@app.command()
def extract() -> None:
    """Extract and validate .onion addresses from fetched documents."""
    init_db()
    typer.echo("Extracting .onion addresses from fetched documents...")
    extracted = extract_pending()
    typer.echo(f"✓ Extract stage complete: {extracted} onion mentions extracted.")


@app.command()
def score() -> None:
    """Score all leads based on context keywords, recurrence, and source diversity."""
    init_db()
    typer.echo("Scoring onion leads...")
    scored = score_all()
    typer.echo(f"✓ Score stage complete: {scored} leads scored.")


@app.command("run-all")
def run_all(
    limit: int = typer.Option(200, "--limit", help="Max documents to fetch in this run"),
) -> None:
    """Execute collect -> fetch -> extract -> score end-to-end."""
    init_db()
    typer.echo("=" * 60)
    typer.echo("SurfaceTrace-IN: End-to-End Pipeline Execution")
    typer.echo("=" * 60)

    collect(source=None, queries_file=None)
    fetch_cmd(limit=limit)
    extract()
    score()

    from st.db import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM documents")
    docs_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM onion_mentions")
    mentions_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM leads")
    leads_cnt = cur.fetchone()[0]
    cur.execute("SELECT band, COUNT(*) FROM leads GROUP BY band")
    band_dist = dict(cur.fetchall())
    conn.close()

    typer.echo("=" * 60)
    typer.echo(
        f"✓ Pipeline Run Complete:\n"
        f"  Total Documents: {docs_cnt}\n"
        f"  Onion Mentions:  {mentions_cnt}\n"
        f"  Unique Leads:    {leads_cnt}\n"
        f"  Bands:           High: {band_dist.get('high', 0)}, "
        f"Medium: {band_dist.get('medium', 0)}, Low: {band_dist.get('low', 0)}"
    )
    typer.echo("=" * 60)


@app.command("export")
def export_cmd(
    path: str = typer.Option("output/leads.csv", "--path", "-o", help="Output CSV path"),
    mask: bool = typer.Option(True, "--mask/--no-mask", help="Mask onion addresses (first 8 chars + ...)"),
) -> None:
    """Export scored leads to CSV."""
    init_db()
    export_csv(path=path, masked=mask)
    typer.echo(f"✓ Exported leads to {path} (masked={mask})")


@app.command("evaluate")
def evaluate_cmd() -> None:
    """Evaluate pipeline precision per band and baseline comparison."""
    init_db()
    metrics = run_eval()

    typer.echo("=" * 60)
    typer.echo("SurfaceTrace-IN Evaluation Results")
    typer.echo("=" * 60)
    typer.echo(f"Total Documents: {metrics['total_documents']}")
    typer.echo(f"Total Leads:     {metrics['total_leads']} (Reviewed: {metrics['reviewed_leads']})")
    typer.echo(f"Label Counts:    {metrics['counts_per_label']}")
    typer.echo(f"Band Counts:     {metrics['counts_per_band']}")
    typer.echo("-" * 60)
    typer.echo("Precision per Band (relevant / (relevant + irrelevant)):")
    for b, data in metrics["precision_per_band"].items():
        typer.echo(f"  {b.capitalize():<8}: {data['precision'] * 100:.1f}% (rel: {data['relevant']}, irrel: {data['irrelevant']})")
    typer.echo("-" * 60)
    typer.echo(f"Documents per Source: {metrics['documents_per_source']}")
    typer.echo(f"Leads per Source:     {metrics['leads_per_source']}")
    if metrics["baseline_comparison"].get("sample_size", 0) > 0:
        base = metrics["baseline_comparison"]
        typer.echo("-" * 60)
        typer.echo(
            f"Baseline Comparison (Top {base['sample_size']} leads):\n"
            f"  Our Score Model Precision:    {base['our_model_precision'] * 100:.1f}%\n"
            f"  Doc Frequency Baseline Prec:  {base['doc_count_baseline_precision'] * 100:.1f}%"
        )
    typer.echo("=" * 60)

