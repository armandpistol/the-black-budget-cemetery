# THE BLACK-BUDGET CEMETERY

An open-source, multimodal AI and geospatial intelligence platform that ingests, 
extracts, and interrogates declassified U.S. government records on Cold War-era 
anomalous phenomena.

> **Architecture Note:** This repository is actively pivoting from a v1.0 Enterprise BI stack (Snowflake/Tableau/Tesseract — preserved under git tag `v1.0-snowflake-poc`) to a v2.0 production-grade, open-source AI engineering stack.

## Intelligence Sectors & Programs in Scope
- **Sector Alpha (Material & Spatial):** Project Mogul, Sign, Grudge, Twinkle, and Blue Book (USAF, 1947–1969), Project Moon Dust / Operation Blue Fly (USAF FTD / Army Intelligence) — curated high-value anomalous aerial incident files.
- **Sector Beta (Cognitive & Psychological):** Project MKUltra, MKDelta, MKNaomi, MKOFTEN, Artichoke, Bluebird (CIA) & Project Grill Flame, Sun Streak, Often / Chickwit, Scanate, Stargate (DIA/CIA).
- **Sector Gamma (Administrative & Systemic Deception):** Redaction forensics, bureaucratic routing, and FOIA chain-of-custody analysis.

## Source Archives
- National Archives Catalog & Bulk Exports
- FBI Vault
- AARO FOIA Reading Room

## v2.0 Tech Stack
| Layer | Technology |
|-------|----------|
| Language | Python 3.11 |
| Multimodal Vision & Extraction | Qwen 2.5-VL (Ollama + LiteLLM) |
| Orchestration | Apache Airflow (Docker) |
| Storage & Vector/Geo Node | Supabase (PostgreSQL + pgvector + PostGIS) |
| Transformation | dbt Core |
| Agentic Workflow & LLM | LangGraph + Llama 3.1 (Groq) |
| Presentation UI | Gradio Tech-Noir Terminal |
| Version Control & Deployment | Dual-Remote Git (GitHub + Hugging Face Spaces -> `armandpistol.dev`) |

## v2.0 Pipeline Architecture
```text
Declassified Sources (NARA, FBI Vault & AARO)
                       │
                       ▼ 
        ┌──────────────────────────────┐
        │   Qwen 2.5-VL (via Ollama)   │
        │  + LiteLLM / Pydantic v2     │
        └──────────────┬───────────────┘
                       │ 
                       ▼
        ┌──────────────────────────────┐
        │   Supabase (PostgreSQL)      │
        │  RAW + pgvector + PostGIS    │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │    dbt Core (dbt-postgres)   │
        │   Staging Views & Marts      │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  LangGraph Multi-Sector      │
        │  Agents + Llama 3.1 (Groq)   │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   Gradio Tech-Noir Terminal  │
        │      (armandpistol.dev)      │
        └──────────────────────────────┘
```

## Project Status
**v1.0 Legacy BI Proof-of-Concept (Completed — Tag: v1.0-snowflake-poc)**
- [x] Dockerized Airflow orchestration + Tesseract OCR extraction
- [x] Snowflake RAW/STAGING/MARTS schemas + dbt-snowflake models
- [x] Live Tableau geospatial incident dashboard

**v2.0 AI Platform Pivot (Active Sprint)**
- [x] Pydantic v2 Multimodal Forensic Schema (BlackBudgetCemeterySchema)
- [ ] Automated multi-source ingestion & manifest tracking (NARA, FBI Vault, AARO)
- [x] In-memory multimodal extraction pipeline (Qwen 2.5-VL via Ollama + LiteLLM)
- [x] Supabase storage node deployment (PostgreSQL + pgvector + PostGIS)
- [x] dbt Core (dbt-postgres) staging & forensic mart transformations
- [ ] LangGraph 3-Sector agentic workflow & Gradio Tech-Noir UI deployment

## Author
Armand Pistol - former Law
Enforcement Officer, transitioning into AI Engineering.