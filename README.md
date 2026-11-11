---
title: The Black-Budget Cemetery
emoji: 📡
colorFrom: red
colorTo: gray
sdk: gradio
app_file: app.py
short_description: Tri-Modal AI, Hybrid RAG & Multi-Agent Intelligence Matrix
pinned: true
---

# THE BLACK-BUDGET CEMETERY

An open-source, **Tri-Modal AI** and **Geospatial Intelligence Platform** that continuously discovers, extracts, embeds, reranks, and interrogates declassified U.S. government records (documents, microfilm scans, audio recordings, and motion video) on Cold War and modern anomalous phenomena.

> **Architecture Note:** This repository evolved from a v1.0 Enterprise BI proof-of-concept (Snowflake/Tableau/Tesseract — preserved under git tag `v1.0-snowflake-poc`) into a v2.0 production-grade, open-source AI & Advanced RAG engineering stack.

## Intelligence Sectors & Programs in Scope
- **Sector Alpha (Material & Spatial):** Project Mogul, Sign, Grudge, Twinkle, and Blue Book (USAF, 1947–1969), Project Moon Dust & Operation Blue Fly (USAF FTD / Army Intelligence) — radar-visual incidents, flight telemetry, and physical material recovery logs.
- **Sector Beta (Cognitive & Psychological):** Project MKUltra, MKDelta, MKNaomi, MKOFTEN, Artichoke, Bluebird (CIA) & Project Grill Flame, Sun Streak, Often / Chickwit, Scanate, Stargate (DIA/CIA) — psychoenergetic and psychometric research records.
- **Sector Gamma (Administrative & Systemic Deception):** Redaction forensics, bureaucratic routing stamps, and FOIA chain-of-custody analysis.

## Source Archives & Dual-Vault Knowledge Architecture
- **Primary Evidence Vault (`raw.forensic_intelligence`):** Automated continuous discovery across National Archives (NARA Catalog API v2 & Record Group 615 / 341), FBI Vault (`vault.fbi.gov`), CIA CREST, and AARO FOIA Reading Rooms regardless of historical release decade.
- **Private Deep-Reference RAG Vault (`raw.reference_knowledge_chunks`):** Isolated, gitignored semantic knowledge base utilizing **LlamaIndex** (`SentenceWindowNodeParser` & `MetadataReplacementPostProcessor`) to index peer-reviewed papers, technical monographs, and historical reference books with expanded context windows.

## v2.0 Tech Stack
| Layer                         | Technology                                                                                                                     |
|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| Language                      | Python 3.11                                                                                                                    |
| Tri-Modal Extraction Engine   | **Vision:** `Qwen 2.5-VL (7B)` (Ollama + LiteLLM) · **Audio:** `Whisper Large v3 Turbo` · **Video:** `OpenCV` Keyframe RAM Slicer |
| Data Contracts                | Pydantic v2 (`BlackBudgetCemeterySchema`)                                                                                      |
| Advanced RAG & Embeddings     | `LlamaIndex` (`SentenceWindowNodeParser`, `MetadataReplacementPostProcessor`, Hybrid Reranker) + `nomic-embed-text` (768-dim)   |
| Orchestration                 | Apache Airflow 2.9 (Docker Compose — Idempotent Incremental Manifest Radar)                                                    |
| Storage, Vector & Geo Node    | Supabase PostgreSQL (`pgvector` HNSW cosine indexes + `PostGIS` `GEOGRAPHY(POINT, 4326)`)                                      |
| Transformation & Quality Gate | dbt Core (`dbt-postgres`) — JSONB unpacking, SQL window coordinate healing & schema tests                                      |
| Agentic Workflow & LLMs       | `LangGraph` (`R.E.A.P.E.R. [MOD-0]` Multi-Sector Router: Draco, Dr. Sapelli, Callista) + Groq LPU                              |
| Deployment & Presentation     | Decoupled Multi-Remote Git (GitHub + Hugging Face Spaces) + `R.E.A.P.E.R. [MOD-0]` Terminal (`Gradio` -> `armandpistol.dev`)   |

## v2.0 Pipeline Architecture
```text
Declassified Feeds (NARA API / RG-615 / FBI Vault / CIA CREST: .pdf, .jpg, .mp3, .wav, .mp4)
                       │
                       ▼ (Idempotent Incremental Manifest Radar)
        ┌──────────────────────────────────────────┐
        │         Tri-Modal RAM Extractor          │
        │  Qwen 2.5-VL (7B) + Whisper + OpenCV     │
        │        + LiteLLM / Pydantic v2           │
        └──────────────┬───────────────────────────┘
                       │ Validated Contract + 768-dim Vector (nomic-embed-text)
                       ▼
        ┌──────────────────────────────────────────┐
        │          Supabase (PostgreSQL)           │
        │   Dual-Vault: Forensic Cases + RAG Lore  │
        │      (pgvector HNSW + PostGIS 4326)      │
        └──────────────┬───────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────────┐
        │          dbt Core (dbt-postgres)         │
        │   Staging Views, Window Coordinate       │
        │    Healing, Marts & Automated Tests      │
        └──────────────┬───────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────────┐
        │     LlamaIndex Hybrid Reranker &         │
        │     LangGraph 3-Sector Agents + Groq     │
        └──────────────┬───────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────────┐
        │  R.E.A.P.E.R. [MOD-0] Terminal (Gradio)  │
        │            (armandpistol.dev)            │
        └──────────────────────────────────────────┘
```

## Project Status
**v1.0 Legacy BI Proof-of-Concept (Completed — Tag: `v1.0-snowflake-poc`)**
- [x] Dockerized Airflow orchestration + Tesseract OCR extraction
- [x] Snowflake RAW/STAGING/MARTS schemas + `dbt-snowflake` models
- [x] Live Tableau geospatial incident dashboard

**v2.0 AI Platform Pivot (Completed)**
- [x] Pydantic v2 Multimodal Forensic Schema (`BlackBudgetCemeterySchema`)
- [x] Tri-Modal in-memory extraction pipeline (`Qwen 2.5-VL 7B`, `Whisper`, `OpenCV` + `LiteLLM`)
- [x] Supabase Dual-Vault storage node deployment (`PostgreSQL` + `pgvector` HNSW + `PostGIS`)
- [x] `dbt Core` (`dbt-postgres`) staging, window coordinate healing, marts & automated schema tests
- [x] Incremental Manifest Radar & Airflow v2.0 DAG orchestration (`ingest >> dbt run >> dbt test`)
- [x] Automated multi-source archival fetcher (NARA/FBI Vault/CREST) & `LlamaIndex` Sentence-Window RAG chunker
- [x] `LangGraph` + `LlamaIndex` hybrid-reranked 3-Sector agentic workflow & `R.E.A.P.E.R. [MOD-0]` UI (`Gradio`)

## Author
Built by Armand Pistol — Systems & AI Engineer, former Law Enforcement Officer (`armandpistol.dev`).