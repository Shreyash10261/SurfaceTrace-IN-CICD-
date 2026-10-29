# SurfaceTrace-IN: Project Final Report

## Abstract
SurfaceTrace-IN investigates the feasibility and efficacy of discovering dark-web (.onion) hidden services associated with terrorism in India exclusively via surface-web reconnaissance. By systematically surveying search engines, public repositories, clearnet onion search indices, and research feeds, the pipeline discovers, verifies, and contextually scores hidden service footprints without initiating any dark-web connections.

## 1. Introduction and Motivation
*(Authored by Shreyash)*
- Threat intelligence context in the Indian subcontinent.
- The distinction between proactive darknet scraping and surface-web footprint detection.
- Core objectives: automated discovery, cryptographic validation, explainable scoring, and evaluation.

## 2. Background and Related Work
*(Authored by Shivang)*
- Open-Source Intelligence (OSINT) methodologies for counter-terrorism.
- The Tor v3 hidden service specification and surface indexing.
- Legal and ethical considerations under the Information Technology Act and university research guidelines.

## 3. System Design and Architecture
*(Authored by Shreyash)*
- Data-driven pipeline topology centered around SQLite in Write-Ahead Logging (WAL) mode.
- Database schema: `documents`, `onion_mentions`, `leads`, and `runs`.
- Interface contracts and decoupled stage execution.

## 4. Implementation
### 4.1 Collection Layer & Fetcher *(Shivang)*
- Seed list curation (`config/seed_urls.txt`).
- Surface collectors: Web Search, Ahmia clearnet parser, GitHub API, RSS monitor.
- Polite fetching: robots.txt cache, domain rate limiting, Trafilatura text parsing.

### 4.2 Extraction, Validation, and Scoring *(Devanshi)*
- Defang normalization and Tor v3 ed25519 checksum verification.
- Context window extraction (300 chars max).
- Rule-based keyword scoring (strong, medium, weak, negative) + recurrence + source diversity.

### 4.3 Review Dashboard *(Devanshi)*
- Streamlit application: Overview stats, Leads sorting, Lead detail view, annotation logging.
- Safety measures: default address masking (`abcdefgh...`) and zero clickable onion links.

## 5. Results and Evaluation
*(Authored by Shreyash & Devanshi)*
- Collection statistics: documents processed, sources distribution.
- Lead yield: total leads discovered, breakdown across High, Medium, and Low bands.
- Evaluation metrics: 100 hand-labelled sample (Set A tuning vs. Set B validation).
- Precision per band: High vs Medium vs Low.
- Inter-annotator agreement on 20 shared leads.
- Baseline comparison: Contextual scoring vs. raw document frequency ranking.

## 6. Ethics, Risks, and Limitations
*(Authored by Devanshi)*
- Strict adherence to zero-Tor-connection policy.
- Data minimisation and CSAM/harmful material handling protocol.
- Limitations of surface-web visibility and indexing delays.

## 7. Conclusion and Future Work
*(Authored by Shreyash)*
- Summary of research findings.
- Potential extensions: Multilingual NLP classifiers (Hindi/Urdu), supervised rankers, approved liveness probes.

## References
- The Tor Project: Tor Rendezvous Specification - Version 3.
- Ministry of Home Affairs (MHA), Government of India: Banned Organizations List.

## Appendix
- Database Schema Definition.
- Complete Seed List and Query Catalog.
- Scoring Lexicon Weights.
- Lead Labelling Guidelines.

