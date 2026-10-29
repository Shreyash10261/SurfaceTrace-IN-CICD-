# SurfaceTrace-IN: Project Blueprint

**Project:** Pipeline to find dark-web (.onion) sites, forums and communities linked to "terrorism in India", searching only the surface web. **Team:** Shreyash (platform and evaluation), Shivang (collection), Devanshi (extraction, scoring, dashboard). **Plan:** final version, 28 days plus 2 spare.

## 1. Goal, scope and rules

In 28 days (days 29 and 30 are spare buffer) we build a Python pipeline that finds `.onion` address strings mentioned on public surface-web pages about terrorism in India, scores them, shows them in a dashboard, and evaluates how accurate the ranking is. **It never visits any .onion site.**

What we deliver: working code, a dashboard, an evaluation with real numbers, a report, slides and a rehearsed demo.

Rules (everyone, including any AI you use):

1. No Tor, no .onion access. We only find address text on normal web pages.
2. No logins, no joining forums or channels, no posting, no contacting anyone.
3. Store only URL, title, cleaned page text (max 20,000 characters) and 300-character contexts. No images or files.
4. If you come across child abuse material or other clearly illegal content, stop, do not store or share it, delete the row, and tell your teacher.
5. Respect robots.txt and send at most 1 request per second per website.
6. Get written approval from your teacher for the topic and this scope **before Day 3**. Keep the message or email.
7. Never publish or share the address list. In slides, screenshots and exports, addresses are masked (first 8 characters plus `...`).
8. We analyse text only. We do not try to identify people, and we do not take any action against any site.

## 2. How it works

1. **Search** (Shivang): run queries on surface-web sources and save the result URLs. A hand-picked list of public pages (the seed list) is always included so the demo never runs empty.
2. **Fetch** (Shivang): download each page and save its cleaned text.
3. **Extract** (Devanshi): find `.onion` addresses, validate them, save a 300-character context around each.
4. **Score** (Devanshi): rank each address by how strongly its context matches terrorism-in-India keywords and how often and where it appears.
5. **Review** (Devanshi, then everyone): a Streamlit dashboard where we label each lead Relevant, Irrelevant or Escalate.
6. **Evaluate** (Shreyash): compare scores with our labels and report precision per band.

Steps only talk to each other through the database (Section 5).

**Definition of "relevant" (used for labelling):** a lead is *Relevant* if the surface page's context clearly ties that address to terrorism, extremism or radicalisation involving India. *Irrelevant* if the context is unrelated (a general list, a news article about something else, a joke). *Escalate* if the context looks seriously harmful or illegal; stop and tell your teacher. We label the page context, not the hidden site, because we never open it.

## 3. Tech stack

| Part | Use |
| --- | --- |
| Language | Python 3.11 |
| Database | SQLite in WAL mode, one file `data/st.db` |
| HTTP and parsing | `requests`, `beautifulsoup4`, `lxml`, `trafilatura` |
| CLI | `typer` |
| Dashboard | `streamlit`, `pandas`, `altair` (comes with Streamlit) |
| Config | `pyyaml`, `python-dotenv` |
| Tests and style | `pytest`, `ruff` |
| Packaging | `Dockerfile` and `docker-compose.yml` (Shreyash, week 3) |

Pin versions with `pip freeze > requirements.txt` right after the first install. Nobody adds a library without telling the team in chat.

## 4. Team, files and working rules

| Person | Owns | Files |
| --- | --- | --- |
| **Shreyash** | Repo, database, CLI, logging, tests, Docker, evaluation, README, report assembly | `db.py`, `cli.py`, `export.py`, `evaluate.py`, `tests/`, `Dockerfile`, `docker-compose.yml`, `README.md` |
| **Shivang** | Search sources, seed list, fetcher, query set | `collect/*.py`, `fetch.py`, `config/queries.txt`, `config/seed_urls.txt`, `config/blocklist.txt` |
| **Devanshi** | Extractor, keywords, scorer, dashboard, labelling guide | `extract.py`, `score.py`, `config/keywords.yml`, `app.py` |

```
surfacetrace/
  README.md  requirements.txt  .env.example  .gitignore
  Dockerfile  docker-compose.yml
  config/ queries.txt  seed_urls.txt  blocklist.txt  keywords.yml
  data/   (st.db and demo.db live here; never committed)
  src/st/ __init__.py __main__.py db.py cli.py fetch.py extract.py score.py
          export.py evaluate.py
          collect/ __init__.py seed.py web_search.py ahmia.py github.py rss.py
  app.py
  tests/  helpers.py test_extract.py test_score.py test_db.py test_fetch.py ...
  docs/   report.md  slides_outline.md  labelling_guide.md  contract_changes.md
```

Working rules:

- Git: `main` is always working. Each person works on `feat/<name>-<topic>` and opens a pull request; another teammate reviews it before merging. Commit messages start with `feat:`, `fix:`, `test:` or `docs:`.
- Only `db.py` writes SQL for shared tables, and it opens the database in WAL mode so the dashboard can read while the pipeline writes. Everyone else calls its functions.
- Store all times in UTC as ISO text.
- Secrets go in `.env` (never committed). `.env.example` lists the names: `SEARCH_API_KEY`, `SEARCH_ENGINE_ID`, `GITHUB_TOKEN`.
- 10-minute stand-up every day in chat: done yesterday, doing today, blocked.
- Changing anything in Section 5 needs all three to agree; write one line in `docs/contract_changes.md`.
- Tests use saved fixtures only. **No live network in tests.**

## 5. Shared contract (follow exactly)

Database, created by `db.init_db()` (Shreyash):

```sql
CREATE TABLE documents (
  id INTEGER PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  title TEXT,
  source TEXT NOT NULL,         -- 'seed' | 'web_search' | 'ahmia' | 'github' | 'rss'
  query TEXT,
  text TEXT,                    -- cleaned page text, max 20000 chars
  status TEXT NOT NULL DEFAULT 'new',  -- new | fetched | done | failed | blocked
  error TEXT,
  fetched_at TEXT               -- UTC ISO
);
CREATE TABLE onion_mentions (
  id INTEGER PRIMARY KEY,
  onion TEXT NOT NULL,          -- lowercase, ends with .onion, passed v3 checksum
  doc_id INTEGER NOT NULL REFERENCES documents(id),
  context TEXT NOT NULL,        -- max 300 chars
  UNIQUE (onion, doc_id)
);
CREATE TABLE leads (
  onion TEXT PRIMARY KEY,
  score INTEGER NOT NULL DEFAULT 0,          -- 0..100
  band TEXT NOT NULL DEFAULT 'low',          -- low | medium | high
  doc_count INTEGER NOT NULL DEFAULT 0,
  source_count INTEGER NOT NULL DEFAULT 0,
  review_status TEXT NOT NULL DEFAULT 'new', -- new | relevant | irrelevant | escalate
  reviewer TEXT,
  note TEXT,
  updated_at TEXT
);
CREATE TABLE runs (
  id INTEGER PRIMARY KEY,
  stage TEXT NOT NULL,          -- collect | fetch | extract | score
  started_at TEXT NOT NULL,
  finished_at TEXT,
  items INTEGER DEFAULT 0,
  error TEXT
);
```

Function signatures (do not rename):

```python
# db.py (Shreyash)
def init_db() -> None: ...
def get_conn() -> sqlite3.Connection: ...         # WAL mode, row_factory = sqlite3.Row
def save_hits(hits: list[dict]) -> int: ...       # hit = {"url","title","source","query"}; ignores duplicate urls; returns number inserted
def log_run(stage: str, items: int, error: str | None = None) -> None: ...

# collect/<name>.py (Shivang), every collector has the same function
def search(query: str, max_results: int = 10) -> list[dict]: ...   # returns hit dicts; seed.py ignores query and returns all seed urls

# fetch.py (Shivang)
def fetch_pending(limit: int = 200) -> int: ...   # 'new' -> 'fetched' | 'failed' | 'blocked'; returns number fetched

# extract.py (Devanshi)
def find_onions(text: str) -> list[tuple[str, int, int]]: ...   # (address, start, end), valid v3 only
def extract_pending() -> int: ...                 # 'fetched' -> 'done', fills onion_mentions

# score.py (Devanshi)
def score_lead(contexts: list[str], doc_count: int, source_count: int) -> int: ...
def score_all() -> int: ...                       # rebuilds score/band/counts in leads; never touches review fields

# export.py, evaluate.py (Shreyash)
def export_csv(path: str, masked: bool = True) -> None: ...
def evaluate() -> dict: ...                       # precision per band, counts, agreement
```

CLI (Shreyash): `python -m st collect [--source NAME]`, `fetch`, `extract`, `score`, `run-all`, `export`, `evaluate`. Dashboard: `streamlit run app.py`.

## 6. Reference code (copy this, do not let an AI rewrite it)

Extraction and checksum (`extract.py` and `tests/helpers.py`):

```python
import base64, hashlib, os, re

ONION = re.compile(r"(?<![a-z0-9])([a-z2-7]{56})\.onion(?![a-z0-9])", re.I)
DEFANG = re.compile(r"\s*[\[\(]\s*(?:\.|dot)\s*[\]\)]\s*onion", re.I)

def clean_text(text: str) -> str:
    """Turn 'abc[.]onion' or 'abc(dot)onion' into 'abc.onion'."""
    return DEFANG.sub(".onion", text)

def is_valid_v3(address: str) -> bool:
    name = address.lower().removesuffix(".onion")
    if len(name) != 56:
        return False
    try:
        raw = base64.b32decode(name.upper())
    except Exception:
        return False
    key, checksum, version = raw[:32], raw[32:34], raw[34:35]
    if version != b"\x03":
        return False
    expected = hashlib.sha3_256(b".onion checksum" + key + version).digest()[:2]
    return checksum == expected

def find_onions(text: str) -> list[tuple[str, int, int]]:
    text = clean_text(text)
    found, seen = [], set()
    for m in ONION.finditer(text):
        addr = m.group(0).lower()
        if addr not in seen and is_valid_v3(addr):
            seen.add(addr)
            found.append((addr, m.start(), m.end()))
    return found

def make_valid_v3() -> str:   # tests only: generates a random VALID fake address
    key, version = os.urandom(32), b"\x03"
    checksum = hashlib.sha3_256(b".onion checksum" + key + version).digest()[:2]
    return base64.b32encode(key + checksum + version).decode().lower() + ".onion"
```

Note: offsets refer to the cleaned text, so `extract_pending` must cut contexts from `clean_text(text)`. Tests must never contain real onion addresses; use `make_valid_v3()`.

## 7. Part specifications

**Sources (Shivang).** All collectors return the same hit dict and write a row to `runs`.

| Collector | What it does | Notes |
| --- | --- | --- |
| `seed.py` | Reads `config/seed_urls.txt` (20 to 30 public pages: research reports, security-vendor blogs, news features, academic papers on dark-web extremism in India) | **Required. Guarantees demo data.** Only reputable public pages. |
| `web_search.py` | One search API behind one function. Day 1: check which is available and free for you (Google Programmable Search JSON API, Brave Search API, or a self-hosted SearXNG); pick one and keep the provider name in `.env` | Quotas and access change, so verify on Day 1. |
| `ahmia.py` | Query Ahmia's clearnet search page and parse result links | Check page structure and terms first. |
| `github.py` | GitHub REST search API for public repos and issues that list onion links or datasets | Needs a token; respect rate limits. |
| `rss.py` | Reads feeds listed in `config/feeds.txt` (Indian news and security blogs), keeps items matching keywords | Use `feedparser` only if the team agrees. |

`config/queries.txt`: about 40 queries, one per line, from three groups: dark-web wording (`"dark web"`, `".onion"`, `"darknet forum"`, `"hidden service"`), India wording (`"terrorism in India"`, `Kashmir`, `Maoist`, `Khalistan`) and public group names from official lists (`Lashkar-e-Taiba`, `Jaish-e-Mohammed`, `Hizbul Mujahideen`, `Indian Mujahideen`). Example: `"terrorism in India" "dark web" forum`. Add Hindi transliterations only if time remains.

**Fetcher (Shivang).** Timeout 20 s; 1 request per second per domain; honour robots.txt; HTML only; skip bodies over 2 MB; `trafilatura` for text; 2 retries with 1 s then 2 s wait on timeout, 429 or 5xx; check `config/blocklist.txt` (domains and words) before saving; one bad URL never stops the run (set `status='failed'` and `error`). Use a clear User-Agent such as `SurfaceTrace-ClassProject (contact: <your college email>)`.

**Extractor (Devanshi).** Use the reference code in Section 6. For each match store a context of up to 150 characters on each side (300 maximum). Run is idempotent: running twice creates no duplicates.

**Scorer (Devanshi).** Keywords are in `config/keywords.yml` in three weights, for example: strong (10 points): `terrorism in india`, group names; medium (5): `jihadi`, `extremist`, `maoist`, `radicalization`, `recruitment`; weak (2): `india`, `kashmir`, `dark web`, `forum`. Negative words (minus 5 each): `movie`, `web series`, `game`, `quiz`. Match whole words or phrases, lowercase, each distinct keyword counted once per context.

```
score = min(50, points of the best context, minimum 0)
      + min(25, 8  * number of documents mentioning it)
      + min(25, 12 * number of distinct sources mentioning it)
band  = high if score >= 60, medium if score >= 30, else low
```

**Dashboard (Devanshi).** Three pages, all on localhost:

1. **Overview:** totals (documents, leads, reviewed), bar chart of leads per band, bar chart of documents per source, review progress.
2. **Leads:** table sorted by score, filters for band, source and review status, search box.
3. **Lead detail:** score breakdown, every context with its source URL, buttons Relevant, Irrelevant, Escalate, a note box, reviewer name in the sidebar.

Addresses are shown masked by default with a toggle for the team; never rendered as clickable links. A button exports the masked CSV.

**Evaluation (Shreyash with everyone).**

- Label at least **100 leads** using the definition in Section 2 and `docs/labelling_guide.md`. Each person labels about 33, plus a shared set of 20 labelled by all three to measure agreement (percent of leads where all agree).
- Split labelled leads in two halves: tune keyword weights on half A only, report final numbers on half B (avoids fooling ourselves).
- `evaluate.py` outputs: precision per band (relevant divided by relevant plus irrelevant), counts per label, agreement on the shared set, documents per source, and leads per source.
- Baseline for comparison: ranking by number of documents only. Show that our scoring beats it (or honestly report if it does not).

**Docker (Shreyash).** `docker-compose.yml` with two services, `pipeline` (runs `python -m st run-all` once) and `dashboard` (Streamlit on 127.0.0.1:8501), both mounting `./data`. No Tor service. The README must work from a clean clone in under 10 minutes; Devanshi tests it on a fresh machine or VM.

## 8. 28-day plan

| Days | Shreyash | Shivang | Devanshi | Gate |
| --- | --- | --- | --- | --- |
| 1-2 | Repo, `.gitignore`, `.env.example`, `db.py`, schema, WAL | **Check search API access**, write `queries.txt` | Extractor with reference code, tests with `make_valid_v3()` | Teacher approval requested |
| 3-4 | CLI skeleton with `run-all` (stubs), logging, `runs` table | `seed.py`, first `seed_urls.txt` (20 pages), `web_search.py` | `extract_pending`, context cutter, tests | Teacher approval received |
| 5-7 | `db` tests, pre-commit `ruff`, CI optional | `fetch.py`, blocklist, fetch tests with fixtures | `keywords.yml`, `score.py`, tests on 10 hand-made cases | **Gate 1 (day 7):** `run-all` works end to end on seed pages; `pytest` green |
| 8-10 | Integration, error handling, `export.py` | `ahmia.py`, `github.py` | Dashboard: Leads page |  |
| 11-14 | First real run, bug fixing | `rss.py`, expand queries to 40 | Dashboard: Lead detail and review buttons, Overview page | **Gate 2 (day 14):** 4 sources, at least 150 documents, review buttons save |
| 15-17 | Dockerfile, compose, README | Full-source run, fix source issues | `labelling_guide.md`, start labelling |  |
| 18-21 | `evaluate.py`, baseline comparison | Label 33 leads, fix fetch failures | Label 34 leads, shared 20 | **Gate 3 (day 21):** 100 leads labelled, `evaluate.py` prints a table, Docker works from a clean clone |
| 22-23 | Tuning support, per-source stats | More seed pages if leads are thin | Tune weights on half A |  |
| 24 | **Final full run**, copy `data/st.db` to `data/demo.db` | Check data quality | Final scoring, label remaining new leads | Data frozen |
| 25 | Code freeze, final tests, README | Screenshots of pipeline logs | Dashboard screenshots (masked) | **Gate 4 (day 25):** code frozen |
| 25-27 | Report assembly | Report: sources and methods | Report: dashboard and results |  |
| 27-28 | Slides, rehearsal 2 times, record backup demo video | Rehearse | Rehearse | Submission ready |
| 29-30 | Buffer | Buffer | Buffer |  |

If a gate fails, stop adding features and fix the gate first. Drop order if behind: Docker, `rss.py`, Overview page, Hindi keywords. Never drop the rules, the evaluation or the seed list.

## 9. Targets and how they map to marks

Targets for the final run: at least 300 documents, 4 sources, 40 leads, 100 labelled leads. If leads are fewer than 40 by day 18, add seed pages and queries (this is why the seed list exists).

Grading usually rewards the items below; confirm your teacher's rubric and adjust.

| Typical criterion | What we show |
| --- | --- |
| Problem understanding and relevance | Section 1 and 2, background in the report, definition of relevant |
| Design and architecture | Architecture diagram, shared contract, ownership table |
| Implementation quality | Working `run-all`, tests, clean repo, Docker, README |
| Results and evaluation | Precision per band, baseline comparison, agreement, per-source yield |
| Ethics and safety | Approval, no Tor, masking, data minimisation, limitations section |
| Presentation and demo | Rehearsed talk, live demo with backup video |
| Documentation and teamwork | Report, commit history by all three, `contract_changes.md` |

## 10. Report, slides and demo

**Report outline (`docs/report.md`, about 12 to 15 pages):** Abstract; 1 Introduction and motivation; 2 Background (OSINT, dark-web monitoring, ethics, legal context in India, in general terms); 3 System design (architecture diagram, database, stages); 4 Implementation (sources, extraction and checksum validation, scoring formula, dashboard); 5 Results and evaluation (counts, precision table, baseline, agreement, per-source yield, examples with masked addresses); 6 Ethics, risks and limitations; 7 Conclusion and future work (classifier, Hindi support, approved liveness checks); References; Appendix (schema, queries, keywords, labelling guide). Shreyash: 3, 5 (tables), 7. Shivang: 4 (sources, fetcher), 2. Devanshi: 4 (extraction, scoring, dashboard), 5 (examples), 6.

**Slides (12 slides, 10 to 12 minutes):** 1 Title; 2 Problem and why it matters; 3 Scope and ethics (surface web only); 4 Architecture diagram; 5 Sources; 6 Extraction and checksum validation; 7 Scoring; 8 Dashboard screenshot (masked); 9 Evaluation method; 10 Results table and baseline; 11 Limitations and future work; 12 Thank you and questions. One speaker per block: Shivang slides 5 to 6, Devanshi 7 to 8, Shreyash 2 to 4 and 9 to 11.

**Live demo (5 minutes):** (1) show `data/demo.db` loaded, never a fresh run; (2) Overview page numbers; (3) open one high lead, show its context and score breakdown; (4) mark it Relevant and show the review log; (5) show the masked CSV export; (6) show `pytest` passing. **Backup:** a recorded video of the same steps and a PDF of screenshots, in case the laptop or network fails.

## 11. Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| Search API unavailable or quota hit | Switch provider in `.env`; seed list and Ahmia still give data |
| Few addresses found | Add seed pages and queries; every extra page counts toward the 300 documents |
| Many false positives | Negative keywords, checksum filter, labelling shows true precision; report honestly |
| A site blocks us | Respect it, skip it, log the reason |
| Illegal or harmful content appears | Rule 4: stop, delete, tell the teacher |
| One person is absent | Contract and reference code mean anyone can take over a file; daily stand-up shows who is blocked |
| AI invents a library or function | Use the prompt in Section 13, run `pytest`, check names against Section 5 |
| Laptop fails at the demo | `demo.db`, backup video and screenshots |

## 12. Final checklist

- [ ] Teacher approval saved
- [ ] `python -m st run-all` works from a clean clone with the README only
- [ ] 4 sources plus seed list, at least 300 documents, at least 40 leads
- [ ] Every stored address passes the v3 checksum test
- [ ] Dashboard with 3 pages and masked addresses by default
- [ ] 100 leads labelled, evaluation table and baseline in the report
- [ ] `pytest` and `ruff` pass; no secrets or database files in git
- [ ] Docker setup tested by someone other than its author
- [ ] Report, slides, `demo.db`, backup video and screenshots ready
- [ ] Two full rehearsals done, with timing under 12 minutes

## 13. Using AI safely on your tasks

Paste this before your task, plus Sections 5, 6 and your part of Section 7:

```
You are a senior Python engineer. Build exactly the TASK below.
Project: a surface-web-only class project that finds .onion address strings on public pages about terrorism in India, scores them, and shows them in a dashboard. It never connects to Tor or any .onion site and never logs in anywhere.
Stack: Python 3.11, SQLite, requests, beautifulsoup4, lxml, trafilatura, typer, streamlit, pandas, pytest, ruff.
Rules: use the schema and function signatures I give you exactly; reuse the reference code I give you unchanged; use only the listed libraries; do not invent library functions or API endpoints (say 'verify in docs' if unsure); no live network in tests; add type hints and docstrings; handle errors without crashing a whole run; store at most 300 characters of context; never put real onion addresses in tests.
Output: complete files with paths, then pytest tests, then run steps. No placeholders or '...'.
TASK: <paste one task from the plan, for example: 'Implement fetch.py: fetch_pending(limit) as specified in Section 7'>
```

After the AI answers: run `pytest` and `ruff`, check that table, column and function names match Section 5, read every library it added, and ask the AI to explain any code you do not understand before you commit it.
