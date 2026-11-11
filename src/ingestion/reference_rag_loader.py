# noinspection SqlNoDataSourceInspection,SqlResolve
"""
reference_rag_loader.py
LlamaIndex Sentence-Window & Hierarchical RAG Chunker for the Private Deep-Reference Vault.
Uses llama_index.core (Document, SentenceWindowNodeParser, SentenceSplitter) to index focal passages
into 768-dim vectors while preserving expanded surrounding context windows in Supabase metadata JSONB.
"""

import os
import pathlib
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv
import litellm
from litellm import embedding
from llama_index.core.node_parser import SentenceSplitter, SentenceWindowNodeParser
from llama_index.core.schema import Document
import pdfplumber
import psycopg2
from psycopg2.extras import Json

litellm.suppress_debug_info = True

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

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


def generate_chunk_embedding(text: str) -> List[float]:
    """Generates a 768-dimension semantic vector via nomic-embed-text (tries .env URL then localhost:11434)."""
    primary_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
    for url in [primary_url, "http://localhost:11434"]:
        try:
            # noinspection PyUnresolvedReferences
            resp = embedding(
                model="ollama/nomic-embed-text",
                input=[text],
                api_base=url,
                timeout=10,
            )
            return resp.data[0]["embedding"]
        except Exception:
            continue
    raise RuntimeError("Ollama nomic-embed-text endpoint unreachable on both configured port and 11434.")


def parse_with_llamaindex_sentence_window(
    raw_text: str,
    doc_metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    LlamaIndex Path 1 (Sentence-Window & Semantic Node Parser):
    Converts raw book/paper text into a LlamaIndex Document, parses it into sentence-window nodes
    (or semantic 300-token chunks with window context for long books), and returns structured dicts
    containing both the focal text (for sharp embedding) and the expanded surrounding 'window' metadata!
    """
    llama_doc = Document(text=raw_text, metadata=doc_metadata)

    # For concise monographs/abstracts, use SentenceWindowNodeParser(window_size=2)
    # For full-length books/papers, group into 280-token sentence-aligned nodes with 45-token overlap
    if len(raw_text.split()) <= 450:
        window_parser = SentenceWindowNodeParser.from_defaults(
            window_size=3,
            window_metadata_key="window",
            original_text_metadata_key="original_text",
        )
        nodes = window_parser.get_nodes_from_documents([llama_doc])
        # Consolidate into a unified monograph node carrying full sentence-window metadata
        full_window = " ".join(n.get_content() for n in nodes)
        return [
            {
                "focal_text": raw_text.strip(),
                "metadata": {
                    **doc_metadata,
                    "rag_engine": "llamaindex_sentence_window",
                    "window": full_window,
                    "original_text": nodes[0].get_content() if nodes else raw_text.strip(),
                },
            }
        ]

    splitter = SentenceSplitter(chunk_size=300, chunk_overlap=50)
    nodes = splitter.get_nodes_from_documents([llama_doc])
    parsed_chunks: List[Dict[str, Any]] = []

    for idx, node in enumerate(nodes):
        focal = node.get_content().strip()
        if len(focal) < 40:
            continue
        # Build an expanded +/- 1 node context window for LlamaIndex MetadataReplacementPostProcessor
        prev_text = nodes[idx - 1].get_content().strip() if idx > 0 else ""
        next_text = nodes[idx + 1].get_content().strip() if idx < len(nodes) - 1 else ""
        expanded_window = " ".join(part for part in (prev_text, focal, next_text) if part)

        parsed_chunks.append(
            {
                "focal_text": focal,
                "metadata": {
                    **doc_metadata,
                    "rag_engine": "llamaindex_sentence_window",
                    "chunk_idx": idx,
                    "total_nodes": len(nodes),
                    "window": expanded_window[:1800],
                    "original_text": focal,
                },
            }
        )
    return parsed_chunks


def extract_text_from_private_file(file_path: pathlib.Path) -> str:
    """Extracts raw text from digital .pdf e-books/papers or .txt/.md files."""
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
    """Idempotently upserts a LlamaIndex node and its expanded 'window' JSONB metadata into Supabase."""
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
    Indexes foundational monographs + any PDF/TXT/MD files in data/raw/private_library/
    using LlamaIndex Sentence-Window node parsing.
    """
    conn = get_supabase_connection()
    cursor = conn.cursor()
    total_chunks = 0

    try:
        cursor.execute(
            "SELECT source_title, chunk_index, metadata->>'rag_engine' FROM raw.reference_knowledge_chunks;"
        )
        # Skip chunks that have already been upgraded to LlamaIndex sentence-window metadata
        existing_keys = {
            (row[0], row[1]) for row in cursor.fetchall() if row[2] == "llamaindex_sentence_window"
        }
        print(f"[*] LlamaIndex RAG Radar: {len(existing_keys)} sentence-window nodes already in Vault.")

        # Phase 1: Index foundational sector monographs with LlamaIndex Sentence-Window metadata
        for item in FOUNDATIONAL_MONOGRAPHS:
            key = (item["source_title"], 0)
            if key in existing_keys:
                print(f"  [SKIP] '{item['source_title'][:50]}...' already LlamaIndex-indexed.")
                continue

            nodes_data = parse_with_llamaindex_sentence_window(
                raw_text=item["text"],
                doc_metadata={"seed_monograph": True, "sector": item["sector_domain"]},
            )
            node_item = nodes_data[0]
            print(f"[*] LlamaIndex Sentence-Window Embedding [{item['sector_domain']}]: {item['source_title']}...")
            vec = generate_chunk_embedding(node_item["focal_text"])
            upsert_reference_chunk(
                cursor=cursor,
                source_title=item["source_title"],
                author=item["author"],
                publication_year=item["publication_year"],
                document_category=item["document_category"],
                sector_domain=item["sector_domain"],
                chunk_index=0,
                chunk_text=node_item["focal_text"],
                metadata=node_item["metadata"],
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

                parent_folder = file_path.parent.name.upper()
                sector = parent_folder if parent_folder in ("ALPHA", "BETA", "GAMMA") else "ALL"
                title = file_path.stem.replace("_", " ").replace("-", " ").title()

                raw_text = extract_text_from_private_file(file_path)
                nodes_data = parse_with_llamaindex_sentence_window(
                    raw_text=raw_text,
                    doc_metadata={"filename": file_path.name, "sector": sector},
                )
                print(f"[*] LlamaIndex parsing '{title}' ({len(nodes_data)} window nodes, Sector {sector})...")

                for idx, node_item in enumerate(nodes_data):
                    if (title, idx) in existing_keys:
                        continue
                    vec = generate_chunk_embedding(node_item["focal_text"])
                    upsert_reference_chunk(
                        cursor=cursor,
                        source_title=title,
                        author="Private Archival Library",
                        publication_year=0,
                        document_category="EBOOK_OR_PAPER",
                        sector_domain=sector,
                        chunk_index=idx,
                        chunk_text=node_item["focal_text"],
                        metadata=node_item["metadata"],
                        vec_768=vec,
                    )
                    total_chunks += 1
                conn.commit()

        print(f"\n[+] LlamaIndex Private RAG sync complete. Newly indexed/upgraded window nodes: {total_chunks}")
        return total_chunks
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    ingest_reference_library()