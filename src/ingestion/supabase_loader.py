"""
supabase_loader.py
Streams in-memory BlackBudgetCemeterySchema objects, generates 768-dim pgvector embeddings,
constructs PostGIS geography points, and executes atomic upserts into Supabase via Port 6543.
"""

import os
import pathlib
import sys
from typing import List, Optional

from dotenv import load_dotenv
from litellm import embedding
import psycopg2
from psycopg2.extras import Json

# Anchor project root so 'src.*' imports work in both PyCharm CLI and Airflow containers
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.schemas import BlackBudgetCemeterySchema
from src.parsing.vision_extractor import extract_document_intelligence

# Load SUPABASE_POOLER_URL and OLLAMA_BASE_URL from .env
load_dotenv(PROJECT_ROOT / ".env")


def get_supabase_connection():
    """
    Opens a PostgreSQL connection to Supabase via Supavisor Transaction Pooler (Port 6543).
    Why: Port 6543 handles high-concurrency stateless ingestion and agent queries efficiently.
    """
    pooler_url = os.getenv("SUPABASE_POOLER_URL")
    if not pooler_url:
        raise ValueError("Missing SUPABASE_POOLER_URL in .env file.")
    return psycopg2.connect(pooler_url)


def generate_text_embedding(text: str, ollama_base_url: str) -> List[float]:
    """
    Generates a 768-dimension semantic vector using local 'nomic-embed-text' (274 MB).
    Why: Matches our Supabase VECTOR(768) HNSW index with zero cloud API cost.
    """
    print("[*] Generating 768-dimension pgvector embedding via nomic-embed-text...")
    resp = embedding(
        model="ollama/nomic-embed-text",
        input=[text],
        api_base=ollama_base_url,
    )
    # noinspection PyUnresolvedReferences
    return resp.data[0]["embedding"]


def register_manifest_entry(cursor, nara_id: str, source_archive: str, source_path: str) -> None:
    """
    Idempotently registers the target document in raw.ingestion_manifest before extraction.
    Why: Enables automated incremental discovery and tracks pipeline failure lineage.
    """
    cursor.execute(
        """
        INSERT INTO raw.ingestion_manifest (nara_id, source_archive, source_path_or_url, ingestion_status)
        VALUES (%s, %s, %s, 'PENDING')
        ON CONFLICT (nara_id) DO UPDATE
        SET ingestion_status = 'PENDING',
            error_log = NULL;
        """,
        (nara_id, source_archive, source_path),
    )


def upsert_forensic_record(
    cursor,
    record: BlackBudgetCemeterySchema,
    vector_768: Optional[List[float]],
) -> None:
    """
    Atomically upserts the validated Pydantic contract, JSONB sectors, pgvector embedding,
    and PostGIS GEOGRAPHY(POINT, 4326) coordinate into raw.forensic_intelligence.
    """
    lat = record.sector_alpha.latitude
    lon = record.sector_alpha.longitude

    cursor.execute(
        """
        INSERT INTO raw.forensic_intelligence (
            nara_id, document_title, pristine_transcript,
            craft_type, historical_era, redaction_fingerprint,
            linguistic_stress_score, latitude, longitude,
            sector_alpha, sector_beta, sector_gamma,
            geom, embedding, ingested_at
        )
        VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            CASE
                WHEN %s IS NOT NULL AND %s IS NOT NULL
                THEN ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
            END,
            %s::vector,
            NOW()
        )
        ON CONFLICT (nara_id) DO UPDATE SET
            document_title = EXCLUDED.document_title,
            pristine_transcript = EXCLUDED.pristine_transcript,
            craft_type = EXCLUDED.craft_type,
            historical_era = EXCLUDED.historical_era,
            redaction_fingerprint = EXCLUDED.redaction_fingerprint,
            linguistic_stress_score = EXCLUDED.linguistic_stress_score,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            sector_alpha = EXCLUDED.sector_alpha,
            sector_beta = EXCLUDED.sector_beta,
            sector_gamma = EXCLUDED.sector_gamma,
            geom = EXCLUDED.geom,
            embedding = EXCLUDED.embedding,
            ingested_at = NOW();
        """,
        (
            record.nara_id,
            record.document_title,
            record.pristine_transcript,
            record.sector_alpha.craft_type,
            record.sector_gamma.historical_era,
            record.sector_gamma.redaction_fingerprint,
            record.sector_beta.linguistic_stress_score,
            lat,
            lon,
            Json(record.sector_alpha.model_dump()),
            Json(record.sector_beta.model_dump()),
            Json(record.sector_gamma.model_dump()),
            lon,
            lat,
            lon,
            lat,  # Note: PostGIS ST_MakePoint takes (longitude, latitude) in X, Y order!
            vector_768,
        ),
    )

    # Mark manifest status as COMPLETED once the forensic row is safely stored
    cursor.execute(
        """
        UPDATE raw.ingestion_manifest
        SET ingestion_status = 'COMPLETED',
            processed_at = NOW()
        WHERE nara_id = %s;
        """,
        (record.nara_id,),
    )


def ingest_single_document(source_path: str, nara_id: str, source_archive: str = "NARA-595466") -> None:
    """End-to-end in-memory pipeline: Manifest -> Vision LLM -> Embedding -> Supabase PostGIS/pgvector."""
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
    conn = get_supabase_connection()
    cursor = conn.cursor()

    try:
        print(f"[*] Registering {nara_id} in Supabase raw.ingestion_manifest...")
        register_manifest_entry(cursor, nara_id, source_archive, str(source_path))
        conn.commit()

        # Step 1: Extract structured Pydantic v2 intelligence in RAM
        record = extract_document_intelligence(
            source=str(source_path),
            nara_id=nara_id,
            ollama_base_url=ollama_url,
        )

        # Step 2: Generate 768-dim vector embedding from the extracted transcript
        vec = generate_text_embedding(record.pristine_transcript, ollama_base_url=ollama_url)

        # Step 3: Upsert into raw.forensic_intelligence with PostGIS point & pgvector
        print(f"[*] Upserting {nara_id} into Supabase raw.forensic_intelligence (Port 6543)...")
        upsert_forensic_record(cursor, record, vec)
        conn.commit()
        print(f"[+] SUCCESS: {nara_id} ('{record.document_title}') locked into Supabase Vault!")

    except Exception as exc:
        conn.rollback()
        cursor.execute(
            """
            UPDATE raw.ingestion_manifest
            SET ingestion_status = 'FAILED', error_log = %s
            WHERE nara_id = %s;
            """,
            (str(exc), nara_id),
        )
        conn.commit()
        print(f"[!] FAILED ingesting {nara_id}: {exc}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Batch ingest all authentic NARA .jpg and .pdf records in data/raw/nara_595466/
    batch_dir = PROJECT_ROOT / "data" / "raw" / "nara_595466"
    target_files = sorted(
        [
            f for f in batch_dir.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".pdf")
        ]
    )

    print(f"[*] Found {len(target_files)} archival documents in {batch_dir.name}. Starting batch run...\n")
    for idx, file_path in enumerate(target_files, start=1):
        # Construct a clean, deterministic NARA primary key from the archive series and filename
        clean_stem = file_path.stem.replace("_", "-").upper()
        record_id = f"NARA-595466-{clean_stem}"

        print(f"=== [{idx}/{len(target_files)}] Processing {file_path.name} ({record_id}) ===")
        try:
            ingest_single_document(
                source_path=str(file_path),
                nara_id=record_id,
                source_archive="NARA-595466",
            )
        except Exception as e:
            # Continue batch execution even if an individual archival file is corrupted
            print(f"[!] Skipping {file_path.name} due to error: {e}")
        print()