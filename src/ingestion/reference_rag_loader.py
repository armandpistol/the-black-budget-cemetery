# noinspection SqlNoDataSourceInspection,SqlResolve
"""
reference_rag_loader.py
Private Deep-Reference RAG Chunker & Vector Loader.
Slices e-books, peer-reviewed papers (.pdf, .txt, .md), and foundational monographs into
overlapping semantic passages, generates 768-dim embeddings via nomic-embed-text,
and upserts them into Supabase raw.reference_knowledge_chunks.
"""

import os
import pathlib
import sys
from typing import Dict, List, Any

from dotenv import load_dotenv
from litellm import embedding
import pdfplumber
import psycopg2
from psycopg2.extras import Json

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# Built-in foundational academic & historical reference passages so the RAG vault works out of the box
FOUNDATIONAL_MONOGRAPHS: List[Dict[str, Any]] = [
    {
        "source_title": "The Report on Unidentified Flying Objects (USAF Project Blue Book Monograph)",
        "author": "Capt. Edward J. Ruppelt (Former Head of Project Blue Book)",
        "publication_year": 1956,
        "document_category": "TECHNICAL_MONOGRAPH",
        "sector_domain": "ALPHA",
        "text": (
            "During the July 1952 Washington D.C. National Airport and Andrews Air Force Base radar-visual "
            "sightings, CAA Senior Controller Harry G. Barnes and his radar crew tracked seven unidentified "
            "targets moving at speeds between 100 and 130 mph before accelerating beyond 500 mph across restricted "
            "White House and Capitol airspace. Simultaneous visual confirmations by commercial airline pilots "
            "including Capt. C.S. Pierman (Capitol Airlines Flight 807) and USAF F-94 interceptor pilots Lt. William "
            "Patterson and Lt. John McHugo demonstrated correlated radar-visual returns that could not be fully "
            "explained by standard temperature inversions alone, despite official USAF press conference attributions."
        ),
    },
    {
        "source_title": "A Perceptual Channel for Information Transfer Over Kilometer Distances (IEEE Proceedings)",
        "author": "Harold E. Puthoff & Russell Targ (Stanford Research Institute - Project Stargate)",
        "publication_year": 1976,
        "document_category": "PEER_REVIEWED_PAPER",
        "sector_domain": "BETA",
        "text": (
            "Peer-reviewed laboratory investigations conducted at Stanford Research Institute (SRI) under DIA/CIA "
            "sponsorship (Projects Scanate, Grill Flame, and Stargate) evaluated coordinate remote viewing (CRV) "
            "protocols. Subjects were provided geographic target coordinates or encrypted target references under "
            "double-blind electromagnetic shielding conditions. Statistical evaluation of descriptor matrices and "
            "blind-judging ranks indicated information transfer above chance expectation, leading to operational "
            "deployments by Defense Intelligence Agency (DIA) and U.S. Army INSCOM units at Fort Meade."
        ),
    },
    {
        "source_title": "Project MKULTRA, The CIA's Program of Research in Behavioral Modification (Senate Hearing)",
        "author": "U.S. Senate Select Committee on Intelligence (Church Committee)",
        "publication_year": 1977,
        "document_category": "TECHNICAL_MONOGRAPH",
        "sector_domain": "GAMMA",
        "text": (
            "In January 1973, CIA Director Richard Helms and Technical Services Division (TSD) chief Sidney Gottlieb "
            "ordered the systematic destruction of primary Project MKULTRA, Artichoke, and Bluebird operational files. "
            "In 1977, FOIA requests uncovered approximately 8,000 pages of surviving financial and administrative "
            "routing records that had been misfiled in a budget archive, exposing 149 subprojects across universities, "
            "hospitals, and safe houses involving LSD-25, mescaline, scopolamine, and electro-cognitive conditioning. "
            "Forensic analysis of surviving MKULTRA documents relies on cross-referencing unredacted financial subproject "
            "ledgers against heavily redacted operational memoranda."
        ),
    },
]


def get_supabase_connection():
    """Opens a PostgreSQL connection to Supabase via Transaction Pooler (Port 6543)."""
    pooler_url = os.getenv("SUPABASE_POOLER_URL")
    if not pooler_url:
        raise ValueError("Missing SUPABASE_POOLER_URL in .env file.")
    return psycopg2.connect(pooler_url)


def generate_chunk_embedding(text: str, ollama_base_url: str) -> List[float]:
    """Generates a 768-dimension semantic vector via nomic-embed-text."""
    # noinspection PyUnresolvedReferences
    resp = embedding(
        model="ollama/nomic-embed-text",
        input=[text],
        api_base=ollama_base_url,
    )
    return resp.data[0]["embedding"]


def sliding_window_chunk_text(text: str, chunk_words: int = 350, overlap_words: int = 50) -> List[str]:
    """
    Splits long book/paper text into overlapping word passages.
    Why: 50-word sliding overlap prevents semantic thoughts from being severed at chunk boundaries.
    """
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_words:
        return [" ".join(words)]

    chunks: List[str] = []
    step = max(1, chunk_words - overlap_words)
    for start in range(0, len(words), step):
        passage = " ".join(words[start : start + chunk_words])
        if len(passage.strip()) > 40:
            chunks.append(passage)
        if start + chunk_words >= len(words):
            break
    return chunks


def extract_text_from_private_file(file_path: pathlib.Path) -> str:
    """Extracts raw text from digital .pdf e-books/papers or .txt/.md files without OCR overhead."""
    if file_path.suffix.lower() == ".pdf":
        pages_text = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_str = page.extract_text() or ""
                if page_str.strip():
                    pages_text.append(page_str.strip())
        return "\n\n".join(pages_text)
    return file_path.read_text(encoding="utf-8", errors="ignore")


def upsert_reference_chunk(
    cursor,
    source_title: str,
    author: str,
    publication_year: int,
    document_category: str,
    sector_domain: str,
    chunk_index: int,
    chunk_text: str,
    metadata: Dict[str, Any],
    vec_768: List[float],
) -> None:
    """Idempotently upserts a single semantic passage and its 768-dim vector into Supabase."""
    cursor.execute(
        """
        INSERT INTO raw.reference_knowledge_chunks (
            source_title, author, publication_year, document_category,
            sector_domain, chunk_index, chunk_text, metadata, embedding
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
        ON CONFLICT (source_title, chunk_index) DO UPDATE SET
            chunk_text = EXCLUDED.chunk_text,
            metadata = EXCLUDED.metadata,
            embedding = EXCLUDED.embedding,
            ingested_at = NOW();
        """,
        (
            source_title,
            author,
            publication_year,
            document_category,
            sector_domain,
            chunk_index,
            chunk_text,
            Json(metadata),
            vec_768,
        ),
    )


def ingest_reference_library() -> int:
    """
    1. Loads foundational peer-reviewed/monograph seeds across Sectors Alpha, Beta, and Gamma.
    2. Scans data/raw/private_library/{alpha,beta,gamma} for any user-supplied PDF e-books or papers.
    """
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
    conn = get_supabase_connection()
    cursor = conn.cursor()
    total_chunks = 0

    try:
        # Check which (source_title, chunk_index) pairs are already in Supabase so we skip duplicates
        cursor.execute("SELECT source_title, chunk_index FROM raw.reference_knowledge_chunks;")
        existing_keys = {(row[0], row[1]) for row in cursor.fetchall()}
        print(f"[*] Private RAG Radar: {len(existing_keys)} reference chunks already in Vault.")

        # Phase 1: Ensure foundational sector monographs are indexed
        for item in FOUNDATIONAL_MONOGRAPHS:
            key = (item["source_title"], 0)
            if key in existing_keys:
                print(f"  [SKIP] '{item['source_title'][:50]}...' already indexed.")
                continue

            print(f"[*] Embedding [{item['sector_domain']}] reference: {item['source_title']}...")
            vec = generate_chunk_embedding(item["text"], ollama_base_url=ollama_url)
            upsert_reference_chunk(
                cursor=cursor,
                source_title=item["source_title"],
                author=item["author"],
                publication_year=item["publication_year"],
                document_category=item["document_category"],
                sector_domain=item["sector_domain"],
                chunk_index=0,
                chunk_text=item["text"],
                metadata={"seed_monograph": True},
                vec_768=vec,
            )
            conn.commit()
            total_chunks += 1

        # Phase 2: Scan data/raw/private_library/{alpha,beta,gamma} for private e-books & papers
        lib_root = PROJECT_ROOT / "data" / "raw" / "private_library"
        if lib_root.exists():
            for file_path in sorted(lib_root.rglob("*")):
                if not file_path.is_file() or file_path.suffix.lower() not in (".pdf", ".txt", ".md"):
                    continue

                # Determine sector from parent folder name (alpha, beta, gamma -> default ALL)
                parent_folder = file_path.parent.name.upper()
                sector = parent_folder if parent_folder in ("ALPHA", "BETA", "GAMMA") else "ALL"
                title = file_path.stem.replace("_", " ").replace("-", " ").title()

                raw_text = extract_text_from_private_file(file_path)
                chunks = sliding_window_chunk_text(raw_text, chunk_words=350, overlap_words=50)
                print(f"[*] Processing private book/paper '{title}' ({len(chunks)} chunks, Sector {sector})...")

                for idx, passage in enumerate(chunks):
                    if (title, idx) in existing_keys:
                        continue
                    vec = generate_chunk_embedding(passage, ollama_base_url=ollama_url)
                    upsert_reference_chunk(
                        cursor=cursor,
                        source_title=title,
                        author="Private Archival Library",
                        publication_year=0,
                        document_category="EBOOK_OR_PAPER",
                        sector_domain=sector,
                        chunk_index=idx,
                        chunk_text=passage,
                        metadata={"filename": file_path.name, "total_chunks": len(chunks)},
                        vec_768=vec,
                    )
                    total_chunks += 1
                conn.commit()

        print(f"\n[+] Private RAG Library sync complete. Newly indexed chunks: {total_chunks}")
        return total_chunks
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    ingest_reference_library()