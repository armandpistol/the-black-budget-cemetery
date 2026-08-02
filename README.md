# US Cold War Anomalies Pipeline

A data engineering portfolio project that ingests, parses, and surfaces
declassified U.S. government records on anomalous phenomena into a
queryable Snowflake data warehouse with a Tableau dashboard.

## Programs Covered
- **Project Blue Book** (USAF, 1947–1969) — UFO sighting investigations
- **Project Stargate / Sun Streak / Grill Flame** (DIA-CIA) — Remote viewing research
- **MKUltra / Project Artichoke / Bluebird** (CIA) — Consciousness research programs

## Source Archives
- AARO FOIA Reading Room
- National Archives (NARA microfilm T1206)
- FBI Vault (vault.fbi.gov)

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| OCR | Tesseract 5.5 + pdf2image |
| Orchestration | Apache Airflow (Docker) |
| Processing | Apache Spark |
| Warehouse | Snowflake (AWS) |
| Transformation | dbt Core |
| Version Control | Git + GitHub |
| Visualization | Tableau |
| Containerization | Docker + Docker Compose |

## Pipeline Architecture
```
Declassified PDFs → OCR Extraction → JSON → Snowflake RAW
                                              ↓
                                         dbt Models
                                              ↓
                                      Tableau Dashboard
```

## Project Status
🔄 **In Progress** — Pipeline foundation complete. Currently building:
- [x] Project structure and environment setup
- [x] OCR extraction (pdf2image + Tesseract)
- [x] Snowflake schema (programs, documents, events tables)
- [x] Snowflake loader script
- [ ] Airflow DAG orchestration
- [ ] dbt transformation models
- [ ] Events table population (geospatial data)
- [ ] Tableau dashboard
- [ ] Full archive ingestion

## Setup
```bash
git clone https://github.com/armandpistol/us-cold-war-anomalies-pipeline.git
cd us-cold-war-anomalies-pipeline
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your Snowflake credentials
```

## Author
Built by Armand — former Law
Enforcement Officer, transitioning into data engineering.