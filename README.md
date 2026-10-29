# SurfaceTrace-IN

**Surface-web OSINT pipeline** to find dark-web (`.onion`) sites, forums, and communities linked to "terrorism in India", searching exclusively on the surface web.

> ⚠️ **Hard Ethical Rule:** SurfaceTrace-IN **never** visits, connects to, or routes traffic through Tor or any `.onion` address. It performs text reconnaissance strictly on public surface-web pages.

---

## 1. Overview & Architecture

```
[1] Search (Shivang)  ──>  [2] Fetch (Shivang)   ──>  [3] Extract (Devanshi)
  • seed_urls.txt            • robots.txt check          • regex & defanging
  • web_search.py            • rate limit (1s/domain)    • v3 checksum verify
  • ahmia / github / rss     • trafilatura clean text    • 300-char context window
                                                                 │
                                                                 ▼
[6] Evaluate (Shreyash) <── [5] Review (Team)     <── [4] Score (Devanshi)
  • precision per band        • Streamlit dashboard       • keywords (strong/med/weak)
  • baseline comparison       • masked addresses          • recurrence & diversity
  • agreement on shared 20    • Relevant / Irrelevant     • High / Med / Low bands
```

All stages decouple communication through a single SQLite database (`data/st.db`) operating in Write-Ahead Logging (WAL) mode.

---

## 2. Quick Start (Clean Setup in Under 10 Minutes)

### Prerequisites
- Python 3.11+
- Git
- (Optional) Docker & Docker Compose

### Local Installation
```bash
# 1. Clone & Navigate
git clone <repo-url>
cd surfacetrace

# 2. Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Environment Variables
cp .env.example .env
# Edit .env with any optional API keys (SEARCH_API_KEY, GITHUB_TOKEN)
```

---

## 3. Running the Pipeline

Run end-to-end with the CLI:
```bash
# Run collect -> fetch -> extract -> score
python -m st run-all
```

Or execute individual pipeline stages:
```bash
# 1. Collect candidate URLs from seed list and search sources
python -m st collect

# 2. Fetch HTML content and clean text (max 20,000 chars)
python -m st fetch --limit 200

# 3. Extract and cryptographically validate v3 .onion addresses
python -m st extract

# 4. Score leads (0-100) and assign bands (high, medium, low)
python -m st score

# 5. Export results to CSV (masked addresses by default: abcdefgh...)
python -m st export --path output/leads.csv

# 6. Evaluate accuracy metrics and compare with document frequency baseline
python -m st evaluate
```

---

## 4. Review Dashboard

Launch the human review Streamlit dashboard on localhost:
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser:
- **1. Overview:** View counts for documents, mentions, leads, score band distribution, and source breakdown.
- **2. Leads:** Filter by band, source, or review status; search text; download masked CSV.
- **3. Lead Detail:** Inspect score breakdown and contextual mentions; label leads as **Relevant**, **Irrelevant**, or **Escalate**; record reviewer notes.
- **Safety Toggle:** Addresses are masked by default (`abcdefgh...`) with a team toggle; addresses are never rendered as clickable links.

---

## 5. Docker Deployment

Run the complete pipeline or launch the dashboard with Docker Compose:
```bash
# Launch the Review Dashboard (127.0.0.1:8501)
docker compose up dashboard

# Run the pipeline once
docker compose run --rm pipeline
```

---

## 6. Testing & Quality Checks

Run the automated test suite (all tests use local fixtures and mocks — **zero live network calls**):
```bash
# Run tests
pytest tests/ -v

# Run linting
ruff check src/ tests/ app.py
```

---

## 7. Team & Ownership Matrix

| Member | Role | Files Owned |
| :--- | :--- | :--- |
| **Shreyash** | Platform & Evaluation | `db.py`, `cli.py`, `export.py`, `evaluate.py`, `tests/`, `Dockerfile`, `docker-compose.yml`, `README.md` |
| **Shivang** | Collection Layer | `collect/*.py`, `fetch.py`, `config/queries.txt`, `config/seed_urls.txt`, `config/blocklist.txt` |
| **Devanshi** | Extraction & Scoring | `extract.py`, `score.py`, `config/keywords.yml`, `app.py` |

---

## 8. Hard Rules

1. **No Tor, no .onion access.** The system never initiates connections to Tor or hidden services.
2. **No logins, no posting, no interaction** with any forum, community, or channel.
3. **Store minimal data:** URL, title, cleaned text (max 20,000 characters), and 300-character context snippets.
4. **CSAM Stop Rule:** If prohibited material is identified, delete the record immediately and report to supervisor.
5. **Polite Fetching:** Honor robots.txt and limit traffic to 1 request/second per domain.
6. **Masking:** Addresses are masked in exports, presentations, and screenshots.
