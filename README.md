# US Cold War Anomalies Pipeline

A data engineering portfolio project that ingests, parses, and surfaces
declassified U.S. government records on anomalous phenomena into a
queryable Snowflake data warehouse with a Tableau dashboard.

## Programs Covered
- **Project Mogul / Sign / Grudge / Twinkle / Blue Book** (USAF, 1947–1969) — UFO sighting investigations
- **Project Grill Flame / Sun Streak / Stargate** (DIA-CIA) — Remote viewing research
- **Project MKUltra / Artichoke / Bluebird** (CIA) — Consciousness research programs

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
Declassified PDFs → OCR (batch) → JSON → Snowflake RAW
                                              ↓
                                   event_extraction (Python)
                                              ↓
                                       Snowflake EVENTS
                                              ↓
                                          dbt Models
                                              ↓
                                           Tableau
```

## Project Status
🔄 **In Progress** — End-to-end pipeline complete. Currently building:
- [x] Project structure and environment setup
- [x] OCR extraction (pdf2image + Tesseract)
- [x] Snowflake schema (programs, documents, events tables)
- [x] Snowflake loader script
- [x] Airflow DAG orchestration
- [x] dbt transformation models
- [x] Events table population (geospatial data)
- [x] Tableau dashboard (live Snowflake connection, incident map)
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
Built by Armand - former Law
Enforcement Officer, transitioning into data engineering.