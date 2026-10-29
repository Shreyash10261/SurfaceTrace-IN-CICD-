# SurfaceTrace-IN: Lead Labelling Guide

## 1. Purpose
This guide defines how team members (Shreyash, Shivang, Devanshi) annotate discovered `.onion` leads in the review dashboard.
We review **only the public surface-web context**, never opening or connecting to any `.onion` hidden service.

## 2. Label Definitions

### Relevant
- The surface page context clearly connects the `.onion` address to **terrorism, extremism, or radicalisation involving India**.
- Examples:
  - An investigative report naming the hidden service as used by Lashkar-e-Taiba, Jaish-e-Mohammed, or ISIS-K.
  - A research paper documenting dark-web propaganda distribution channels targeting Indian youth.
  - A public discussion detailing extremist recruitment links associated with Kashmir or Khalistan separatist terrorism.

### Irrelevant
- The address appears on the surface web, but the surrounding context is unrelated to terrorism in India.
- Examples:
  - General dark web directories, market link lists, or privacy tool roundups.
  - News articles discussing cybercrime, standard malware, or financial fraud unrelated to terror networks in India.
  - Fiction, web series, video game references, or humorous posts.

### Escalate
- The context indicates immediate harmful, dangerous, or strictly illegal content (such as CSAM, active attack planning, or human trafficking).
- **Action**: Stop processing, do not share, delete the database row, and report immediately to the course supervisor/teacher.

## 3. Protocol
1. Each member reviews their assigned subset (~33-34 leads).
2. A shared set of 20 leads is independently labelled by all three members to calculate inter-annotator agreement.
3. Labelled leads are partitioned 50/50:
   - **Set A (Tuning)**: Used to tune keyword weights in `config/keywords.yml`.
   - **Set B (Evaluation)**: Held-out test set evaluated with `evaluate.py`.

