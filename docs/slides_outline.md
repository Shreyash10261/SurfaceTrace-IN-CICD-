# SurfaceTrace-IN: Slide Deck Outline

**Duration:** 10 to 12 minutes (12 slides)
**Speakers:** Shivang (Slides 5-6), Devanshi (Slides 7-8), Shreyash (Slides 1-4, 9-12)

---

### Slide 1: Title & Team
- **Title:** SurfaceTrace-IN: Discovering Surface-Web Footprints of Darknet Sites Linked to Terrorism in India
- **Team:** Shreyash (Platform & Evaluation), Shivang (Collection), Devanshi (Extraction & Dashboard)

### Slide 2: Problem Statement & Motivation
- Need for OSINT-driven threat intelligence without darknet infiltration.
- Tracking surface-web disclosures of extremist hidden services.

### Slide 3: Scope & Ethical Hard Rules
- Surface web only — strictly **zero** Tor / .onion traffic.
- Data minimisation: URL, title, cleaned text, 300-char context.
- Safety protocol: CSAM blocklist, rate limits, supervisor approval.

### Slide 4: System Architecture
- 6-stage decoupled pipeline interacting exclusively via SQLite (WAL mode).
- Query/Seed -> Collectors -> Fetcher -> Extractor -> Scorer -> Review/Eval.

### Slide 5: Collection Layer (Shivang)
- 5 distinct surface collectors: Seed URLs, Web Search, Ahmia clearnet, GitHub REST API, RSS feeds.
- Seed list guarantee: 20+ verified research & security pages.

### Slide 6: Fetching & Data Cleaning (Shivang)
- Rate limiting (1 req/s/domain), robots.txt enforcement.
- Trafilatura text extraction, body size limit (2 MB), blocklist filtering.

### Slide 7: Onion Address Extraction & v3 Validation (Devanshi)
- Regex pattern matching with defang normalization (`[.]` -> `.`).
- Cryptographic Tor v3 checksum validation (SHA3-256 over pubkey + version).
- 300-character symmetric context extraction (±150 chars).

### Slide 8: Contextual Scoring & Review Dashboard (Devanshi)
- Explainable scoring formula: Context keywords (max 50) + Doc recurrence (max 25) + Source diversity (max 25).
- Streamlit Review UI with masked address protection (`abcdefgh...`).

### Slide 9: Evaluation Methodology (Shreyash)
- 100 hand-labelled leads (Relevant, Irrelevant, Escalate).
- 20-lead shared test set for inter-annotator agreement.
- 50/50 split: Set A (tuning) vs. Set B (validation).

### Slide 10: Results & Baseline Comparison (Shreyash)
- Precision per band: High (>=60), Medium (30-59), Low (<30).
- Comparison against baseline frequency ranking (document count only).

### Slide 11: Limitations & Future Work (Shreyash)
- Dependence on surface-web mentions and search indexing.
- Future work: multilingual Hindi/Urdu text classification, approved liveness verification.

### Slide 12: Conclusion & Q&A
- Summary of findings, repo link, and acknowledgments.

