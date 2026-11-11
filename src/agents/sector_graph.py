# noinspection SqlNoDataSourceInspection,SqlResolve
"""
sector_graph.py
R.E.A.P.E.R. [MOD-0] (Retrieval Engine for Autonomous Processing & Entity Resolution)
LangGraph Multi-Sector Intelligence Workflow & Hybrid Dual-Vault RAG Engine:
- AGENT ALPHA ("DRACO" - USAF FTD Aerospace, Radar & Telemetry Specialist)
- AGENT BETA  ("DR. SAPELLI" - SRI Clinical Neuropsychiatrist & Psychotronics Analyst)
- AGENT GAMMA ("CALLISTA" - Counterintelligence Archivist & Redaction Forensics Specialist)
"""

import html
import os
import pathlib
import re
import sys
import time
from typing import Any, Dict, List, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
import litellm
from litellm import completion, embedding
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.schema import NodeWithScore, TextNode
import psycopg2
from psycopg2.extras import RealDictCursor
import requests as req

litellm.suppress_debug_info = True

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# Distinct Cold War Agent Personas + Institutional Color Classifications
SECTOR_PERSONAS: Dict[str, Dict[str, str]] = {
    "ALPHA": {
        "codename": "AGENT ALPHA // DRACO [USAF FTD AEROSPACE & RADAR TELEMETRY]",
        "theme_class": "tone-alpha",
        "clearance": "CLEARANCE: TOP SECRET // SAR-ALPHA // RADAR-KINEMATICS",
        "persona_brief": (
            "DRACO (Male, former USAF Foreign Technology Division aerospace & radar forensics engineer at "
            "Wright-Patterson AFB). Speaks in clipped, mathematical military precision. Analyzes craft geometry, "
            "flight kinematics, Mach/mph speeds, radar-visual corroboration, electromagnetic avionics jamming, "
            "physical landing traces, occupant observations, and PostGIS coordinates."
        ),
    },
    "BETA": {
        "codename": "AGENT BETA // DR. SAPELLI [SRI COGNITIVE & PSYCHOMETRIC OPS]",
        "theme_class": "tone-beta",
        "clearance": "CLEARANCE: TOP SECRET // SAP-BETA // NEURO-PSYCHOMETRICS",
        "persona_brief": (
            "DR. SAPELLI (Female, clinical Cold War neuropsychiatrist & parapsychology researcher formerly attached "
            "to Project MKULTRA, ARTICHOKE, and DIA Project STARGATE at SRI International). Speaks with cool, eerie "
            "clinical detachment. Analyzes psychoactive compounds (LSD-25, Mescaline, Pentothal, BZ), coordinate "
            "remote viewing (CRV) target coordinates, hypnotic regression / missing-time amnesia, and witness "
            "linguistic stress scores (1-10)."
        ),
    },
    "GAMMA": {
        "codename": "AGENT GAMMA // CALLISTA [COUNTERINTELLIGENCE & REDACTION FORENSICS]",
        "theme_class": "tone-gamma",
        "clearance": "CLEARANCE: TOP SECRET // UMBRA-GAMMA // COUNTERINTEL-FOIA",
        "persona_brief": (
            "CALLISTA (Female, cynical counterintelligence archivist and FOIA investigator). Distrusts official "
            "government cover stories ('swamp gas', 'weather balloons', 'Venus'). Analyzes bureaucratic routing "
            "chains (CIA OSI, NSC, DIA, ATIC, FBI), institutional debunking directives (1953 Robertson Panel), "
            "chain-of-custody anomalies, and censorship redaction fingerprints (black marker, white-out, page scrubs)."
        ),
    },
}


class InterrogationState(TypedDict):
    """Shared state dictionary passed across nodes in the R.E.A.P.E.R. [MOD-0] LangGraph workflow."""
    query: str
    sector_mode: str
    active_sectors: List[str]
    vault_cases: List[Dict[str, Any]]
    rag_lore: List[Dict[str, Any]]
    reaper_header: str
    agent_outputs: List[Dict[str, str]]
    final_response: str


def get_db_connection():
    """Opens a connection to Supabase via Transaction Pooler (Port 6543)."""
    pooler_url = os.getenv("SUPABASE_POOLER_URL")
    if not pooler_url:
        raise ValueError("Missing SUPABASE_POOLER_URL in .env file.")
    return psycopg2.connect(pooler_url)


def embed_query_text(query: str) -> List[float]:
    """3-Tier Embedding Cascade (274 MB nomic-embed-text -> Native SQL fallback)."""
    primary_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
    candidate_urls = [primary_url]
    if "11434" not in primary_url:
        candidate_urls.append("http://localhost:11434")

    for url in candidate_urls:
        try:
            # noinspection PyUnresolvedReferences
            resp = embedding(
                model="ollama/nomic-embed-text",
                input=[query],
                api_base=url,
                timeout=3,
            )
            return resp.data[0]["embedding"]
        except Exception:
            continue
    return []


def get_active_groq_model(groq_key: str) -> str:
    """Selects the best English instruction/reasoning model enabled on the Groq account."""
    preferred_order = [
        "llama-3.3-70b-versatile",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3-32b",
    ]
    try:
        resp = req.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {groq_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            available_ids = {m["id"] for m in resp.json().get("data", [])}
            for candidate in preferred_order:
                if candidate in available_ids:
                    return f"groq/{candidate}"
    except Exception:
        pass
    return "groq/openai/gpt-oss-20b"


def call_interrogation_llm(system_prompt: str, user_prompt: str) -> str:
    """Executes single-pass multi-agent inference on Groq LPU with max_tokens=4096."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key or groq_key == "gsk_your_groq_api_key_here":
        raise ValueError("Missing valid GROQ_API_KEY in .env file.")

    target_model = get_active_groq_model(groq_key)

    for attempt in range(1, 4):
        try:
            resp = completion(
                model=target_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=4096,
            )
            content = resp.choices[0].message.content or ""
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            if content:
                return content
        except Exception as exc:
            err_str = str(exc)
            if "rate_limit" in err_str.lower() or "429" in err_str:
                time.sleep(12 * attempt)
                continue
            raise
    raise RuntimeError("Groq API call did not return content after retries.")


def build_reaper_tactical_hud(
    active_sectors: List[str],
    vault_cases: List[Dict[str, Any]],
    rag_lore: List[Dict[str, Any]],
) -> str:
    """
    Renders the R.E.A.P.E.R. [MOD-0] Mechanical Tactical Grid HUD with stamped industrial cells,
    crosshair corner anchors, and glowing phosphor-green entity lock indicators.
    """
    top_case = vault_cases[0] if vault_cases else {}
    top_id = str(top_case.get("nara_id", "NONE"))
    top_sim = top_case.get("similarity", 0.0)
    top_lat = top_case.get("latitude", 0.0)
    top_lon = top_case.get("longitude", 0.0)
    agent_names = {"ALPHA": "DRACO [α]", "BETA": "SAPELLI [β]", "GAMMA": "CALLISTA [γ]"}
    routed_str = " // ".join(agent_names[s] for s in active_sectors)

    return f"""
    <div class="tactical-hud-chassis">
        <div class="tactical-hud-topbar">
            <span class="hud-corner">[+]</span>
            <span class="hud-sys-title">R.E.A.P.E.R. [MOD-0] // ENTITY RESOLUTION ARRAY</span>
            <span class="hud-lock-lamp"><span class="led-green"></span> TARGET LOCKED</span>
            <span class="hud-corner">[+]</span>
        </div>
        <div class="tactical-grid-matrix">
            <div class="tactical-cell">
                <div class="cell-index">01 // PRIMARY DOSSIER LOCK</div>
                <div class="cell-value cell-crimson">{top_id}</div>
            </div>
            <div class="tactical-cell">
                <div class="cell-index">02 // ENTITY CORRELATION</div>
                <div class="cell-value">{top_sim} ({len(vault_cases)} REELS + {len(rag_lore)} MONOGRAPHS)</div>
            </div>
            <div class="tactical-cell">
                <div class="cell-index">03 // GEODETIC SRID-4326</div>
                <div class="cell-value">LAT {top_lat} // LON {top_lon}</div>
            </div>
            <div class="tactical-cell">
                <div class="cell-index">04 // DISPATCHED AGENT BUS</div>
                <div class="cell-value cell-phosphor">{routed_str}</div>
            </div>
        </div>
    </div>
    """


def build_or_tsquery_string(query: str) -> str:
    """Converts a natural-language question into an OR-joined websearch_to_tsquery string."""
    stop_words = {"the", "and", "in", "of", "to", "how", "what", "compare", "cases", "case", "with", "for", "on"}
    words = [w for w in re.findall(r"[a-zA-Z0-9]{3,}", query.lower()) if w not in stop_words]
    return " OR ".join(words[:12]) if words else query


def llamaindex_hybrid_rerank_and_expand(
    query: str,
    candidate_cases: List[Dict[str, Any]],
    candidate_lore: List[Dict[str, Any]],
    top_k_cases: int = 6,
    top_k_lore: int = 3,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    LlamaIndex Path 2 (Hybrid Reranker + MetadataReplacementPostProcessor):
    1. Wraps initial Supabase candidate rows into LlamaIndex TextNode / NodeWithScore objects.
    2. Reranks candidates by fusing base vector/SQL similarity with query keyword density & telemetry richness.
    3. Applies MetadataReplacementPostProcessor(target_metadata_key='window') to expand Private RAG lore chunks.
    """
    q_terms = [w for w in re.findall(r"[a-zA-Z0-9]{3,}", query.lower()) if w not in {"the", "and", "compare", "with"}]

    # Stage 1: Rerank Primary Forensic Vault Candidates (12 -> top_k_cases)
    scored_case_nodes: List[tuple[float, Dict[str, Any]]] = []
    for row in candidate_cases:
        base_sim = float(row.get("similarity") or 0.0)
        haystack = f"{row.get('nara_id', '')} {row.get('document_title', '')} {row.get('transcript_excerpt', '')}".lower()
        keyword_hits = sum(1 for term in q_terms if term in haystack)
        lexical_boost = min(0.25, keyword_hits * 0.05)
        telemetry_boost = 0.08 if str(row.get("occupant_type", "none observed")) != "none observed" else 0.0

        hybrid_score = round(min(0.999, base_sim + lexical_boost + telemetry_boost), 3)
        row_copy = dict(row)
        row_copy["similarity"] = hybrid_score

        # Wrap in LlamaIndex NodeWithScore for standardized RAG pipeline lineage
        node = TextNode(text=row_copy.get("transcript_excerpt", ""), id_=str(row_copy.get("nara_id", "")))
        _ = NodeWithScore(node=node, score=hybrid_score)
        scored_case_nodes.append((hybrid_score, row_copy))

    scored_case_nodes.sort(key=lambda x: x[0], reverse=True)
    reranked_cases = [item[1] for item in scored_case_nodes[:top_k_cases]]

    # Stage 2: Expand Sentence Windows on Private RAG Chunks via LlamaIndex MetadataReplacementPostProcessor
    postprocessor = MetadataReplacementPostProcessor(target_metadata_key="window")
    lore_nodes: List[NodeWithScore] = []
    lore_lookup: Dict[str, Dict[str, Any]] = {}

    for idx, lore in enumerate(candidate_lore):
        node_id = f"lore_{idx}"
        meta = lore.get("metadata") if isinstance(lore.get("metadata"), dict) else {}
        text_node = TextNode(
            id_=node_id,
            text=str(lore.get("chunk_text", "")),
            metadata={"window": meta.get("window", lore.get("chunk_text", ""))},
        )
        base_score = float(lore.get("similarity") or 0.5)
        lore_hits = sum(1 for term in q_terms if term in str(lore.get("chunk_text", "")).lower())
        final_lore_score = round(min(0.999, base_score + (lore_hits * 0.04)), 3)

        lore_nodes.append(NodeWithScore(node=text_node, score=final_lore_score))
        lore_copy = dict(lore)
        lore_copy["similarity"] = final_lore_score
        lore_lookup[node_id] = lore_copy

    expanded_nodes = postprocessor.postprocess_nodes(lore_nodes)
    expanded_nodes.sort(key=lambda n: float(n.score or 0.0), reverse=True)

    reranked_lore: List[Dict[str, Any]] = []
    for n in expanded_nodes[:top_k_lore]:
        item = lore_lookup[n.node.node_id]
        # Replace focal chunk text with the expanded LlamaIndex sentence window
        item["chunk_text"] = n.node.get_content()
        reranked_lore.append(item)

    return reranked_cases, reranked_lore


def retrieve_dual_vault_node(state: InterrogationState) -> InterrogationState:
    """
    Node 1 (R.E.A.P.E.R. [MOD-0] Retrieval, LlamaIndex Window Expansion & Hybrid Reranker):
    Fetches a wide candidate pool (LIMIT 12) from Supabase and reranks to the Top 6 via LlamaIndex.
    """
    query = state["query"]
    mode = state.get("sector_mode", "AUTO").upper()

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query_vec = embed_query_text(query)

        if query_vec:
            cursor.execute(
                """
                SELECT
                    nara_id, source_archive, document_title, historical_era,
                    craft_type, occupant_type, reported_speed_mph, sighting_duration,
                    linguistic_stress_score, redaction_fingerprint,
                    bureaucratic_routing_json, psychoactive_compounds_json,
                    cognitive_target_coordinates, latitude, longitude,
                    left(pristine_transcript, 650) AS transcript_excerpt,
                    ROUND((1 - (embedding <=> %s::vector))::numeric, 3) AS similarity
                FROM marts.mart_forensic_matrix
                ORDER BY embedding <=> %s::vector
                LIMIT 12;
                """,
                (query_vec, query_vec),
            )
            raw_cases = [dict(r) for r in cursor.fetchall()]

            cursor.execute(
                """
                SELECT
                    source_title, author, publication_year, sector_domain,
                    chunk_text, metadata,
                    ROUND((1 - (embedding <=> %s::vector))::numeric, 3) AS similarity
                FROM raw.reference_knowledge_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT 6;
                """,
                (query_vec, query_vec),
            )
            raw_lore = [dict(r) for r in cursor.fetchall()]
        else:
            or_query = build_or_tsquery_string(query)
            cursor.execute(
                """
                SELECT
                    nara_id, source_archive, document_title, historical_era,
                    craft_type, occupant_type, reported_speed_mph, sighting_duration,
                    linguistic_stress_score, redaction_fingerprint,
                    bureaucratic_routing_json, psychoactive_compounds_json,
                    cognitive_target_coordinates, latitude, longitude,
                    left(pristine_transcript, 650) AS transcript_excerpt,
                    ROUND(
                        ts_rank_cd(
                            to_tsvector('english', coalesce(document_title, '') || ' ' || coalesce(pristine_transcript, '')),
                            websearch_to_tsquery('english', %s)
                        )::numeric, 3
                    ) AS similarity
                FROM marts.mart_forensic_matrix
                ORDER BY similarity DESC, ingested_at DESC
                LIMIT 12;
                """,
                (or_query,),
            )
            raw_cases = [dict(r) for r in cursor.fetchall()]

            cursor.execute(
                """
                SELECT
                    source_title, author, publication_year, sector_domain,
                    chunk_text, metadata,
                    0.850 AS similarity
                FROM raw.reference_knowledge_chunks
                ORDER BY chunk_id ASC
                LIMIT 6;
                """
            )
            raw_lore = [dict(r) for r in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

    # Execute LlamaIndex Path 2 Hybrid Reranking & Sentence-Window Postprocessing
    vault_cases, rag_lore = llamaindex_hybrid_rerank_and_expand(
        query=query,
        candidate_cases=raw_cases,
        candidate_lore=raw_lore,
        top_k_cases=6,
        top_k_lore=3,
    )

    q_lower = query.lower()
    if mode in ("WAR_ROOM", "ALL") or "war room" in q_lower:
        active = ["ALPHA", "BETA", "GAMMA"]
    elif mode in ("ALPHA", "BETA", "GAMMA"):
        active = [mode]
    else:
        active = []
        if any(w in q_lower for w in ("radar", "speed", "craft", "disc", "sphere", "flight", "crash", "roswell", "socorro", "mantell", "lubbock", "tehran", "rendlesham", "occupant", "map", "where", "draco")):
            active.append("ALPHA")
        if any(w in q_lower for w in ("mkultra", "lsd", "drug", "chemical", "stargate", "remote viewing", "grill flame", "sun streak", "artichoke", "bluebird", "hypnosis", "stress", "hill", "mind", "psych", "sapelli")):
            active.append("BETA")
        if any(w in q_lower for w in ("redact", "cover", "censor", "robertson", "routing", "cia", "fbi", "agency", "deception", "majestic", "classify", "stamp", "callista")):
            active.append("GAMMA")
        if not active:
            active = ["ALPHA", "BETA", "GAMMA"]

    reaper_banner = build_reaper_tactical_hud(active, vault_cases, rag_lore)

    return {
        **state,
        "vault_cases": vault_cases,
        "rag_lore": rag_lore,
        "active_sectors": active,
        "reaper_header": reaper_banner,
        "agent_outputs": [],
    }


def format_evidence_context(state: InterrogationState) -> str:
    """Formats retrieved Supabase cases and Private RAG chunks into a clean dossier prompt."""
    lines = ["=== PRIMARY DECLASSIFIED VAULT RECORDS (SUPABASE pgvector + PostGIS) ==="]
    for c in state["vault_cases"]:
        lines.append(
            f"- ID: [{c['nara_id']}] | Title: {c['document_title']} | Era: {c['historical_era']} | "
            f"Lock: {c['similarity']}\n"
            f"  Alpha Telemetry: Craft={c['craft_type']}, Occupants={c['occupant_type']}, "
            f"Speed={c['reported_speed_mph']} mph, Duration={c['sighting_duration']}, "
            f"Coords=({c['latitude']}, {c['longitude']})\n"
            f"  Beta Psychometrics: Stress={c['linguistic_stress_score']}/10, "
            f"Compounds={c['psychoactive_compounds_json']}, CRV_Target={c['cognitive_target_coordinates']}\n"
            f"  Gamma Lineage: Routing={c['bureaucratic_routing_json']}, Redaction={c['redaction_fingerprint']}\n"
            f"  Transcript Excerpt: {c['transcript_excerpt']}"
        )

    lines.append("\n=== PRIVATE DEEP-REFERENCE RAG LIBRARY (BOOKS & PEER-REVIEWED PAPERS) ===")
    for r in state["rag_lore"]:
        lines.append(
            f"- [{r['sector_domain']}] '{r['source_title']}' by {r['author']} ({r['publication_year']}): "
            f"{r['chunk_text']}"
        )
    return "\n".join(lines)


def highlight_case_citations(raw_text: str) -> str:
    """
    Regex Pass:
    Wraps bracketed archival case IDs (e.g. [USAF-BLUEBOOK-...], [NARA-...], [CIA-...])
    in a unique <span class="case-ref-tag"> tracking badge so citations stand out visually.
    """
    safe_text = html.escape(raw_text.strip())
    pattern = r"\[([A-Z0-9_\-\u2010\u2011\u2012\u2013\u2014]{8,})\]"
    return re.sub(
        pattern,
        r'<span class="case-ref-tag">[\1]</span>',
        safe_text,
    )


def execute_sector_specialists_node(state: InterrogationState) -> InterrogationState:
    """
    Node 2 (R.E.A.P.E.R. [MOD-0] Multi-Agent Execution + Teletype Queue Structuring):
    Generates specialist reports in a single LPU pass, strips any robotic self-introductions,
    and packages each agent with their unique institutional tone and regex-tagged [CASE-ID] citations.
    """
    evidence_block = format_evidence_context(state)
    active = state["active_sectors"]

    persona_instructions = []
    for s_key in active:
        p = SECTOR_PERSONAS[s_key]
        persona_instructions.append(
            f"[[SECTOR_{s_key}]]\n"
            f"Agent Identity: {p['codename']}\n"
            f"Persona & Scope: {p['persona_brief']}\n"
            f"Write a complete, hard-hitting 130-170 word forensic briefing in this exact voice. "
            f"CRITICAL RULE: NEVER introduce yourself or state your name/role (NEVER start with 'I am Agent...', "
            f"'I am Draco...', or 'As a clinical neuropsychiatrist...'). Open immediately on Word 1 with hard forensic findings. "
            f"Cite exact bracketed [nara_id] keys (e.g., [USAF-BLUEBOOK-HILL-1961-BLUEBOOK-CASE-7570-BETTY-BARNEY-HILL-PEASE-AFB]). "
            f"Do NOT include markdown ### headers inside your paragraph."
        )

    system_prompt = (
        "You are R.E.A.P.E.R. [MOD-0] (Retrieval Engine for Autonomous Processing & Entity Resolution), "
        "the clandestine multi-agent synthesis core of THE BLACK-BUDGET CEMETERY. "
        "Output the requested agent reports in exact order. "
        "Begin each agent's section with its exact tag [[SECTOR_ALPHA]], [[SECTOR_BETA]], or [[SECTOR_GAMMA]]. "
        "Never write self-introductions ('I am Agent Alpha...'). Dive straight into the evidence and finish every sentence completely."
    )

    user_prompt = (
        f"R.E.A.P.E.R. [MOD-0] DIRECTIVE: {state['query']}\n\n"
        f"RETRIEVED DUAL-VAULT EVIDENCE:\n{evidence_block}\n\n"
        f"REQUIRED AGENT TRANSMISSIONS:\n\n" + "\n\n".join(persona_instructions)
    )

    raw_reply = call_interrogation_llm(system_prompt, user_prompt)

    structured_outputs: List[Dict[str, str]] = []
    for s_key in active:
        p = SECTOR_PERSONAS[s_key]
        pattern = rf"\[\[SECTOR_{s_key}\]\]\s*(.*?)(?=\[\[SECTOR_|\Z)"
        match = re.search(pattern, raw_reply, flags=re.DOTALL)
        body_text = match.group(1).strip() if match else raw_reply.strip()
        body_text = re.sub(r"^#+.*?\n", "", body_text).strip()
        # Regex Safety Strip: removes any leading "I am Agent Alpha/Draco/etc..." sentence if emitted
        body_text = re.sub(
            r"^(?:I am|This is|As)\s+(?:Agent\s+(?:Alpha|Beta|Gamma)|Draco|Dr\.?\s*Sapelli|Callista)[^.?!]*[.?!]\s*",
            "",
            body_text,
            flags=re.IGNORECASE,
        ).strip()

        structured_outputs.append(
            {
                "sector": s_key,
                "codename": p["codename"],
                "clearance": p["clearance"],
                "theme_class": p["theme_class"],
                "html_body": highlight_case_citations(body_text),
            }
        )

    return {
        **state,
        "agent_outputs": structured_outputs,
        "final_response": raw_reply,
    }


def build_black_budget_graph():
    """Compiles the LangGraph StateGraph connecting R.E.A.P.E.R. [MOD-0] -> Sector Agents."""
    workflow = StateGraph(InterrogationState)
    workflow.add_node("retrieve_dual_vault", retrieve_dual_vault_node)
    workflow.add_node("execute_sector_specialists", execute_sector_specialists_node)

    workflow.set_entry_point("retrieve_dual_vault")
    workflow.add_edge("retrieve_dual_vault", "execute_sector_specialists")
    workflow.add_edge("execute_sector_specialists", END)
    return workflow.compile()


def interrogate_cemetery(query: str, sector_mode: str = "AUTO") -> Dict[str, Any]:
    """Public entrypoint called by both CLI tests and the Gradio UI."""
    app_graph = build_black_budget_graph()
    initial_state: InterrogationState = {
        "query": query,
        "sector_mode": sector_mode,
        "active_sectors": [],
        "vault_cases": [],
        "rag_lore": [],
        "reaper_header": "",
        "agent_outputs": [],
        "final_response": "",
    }
    return app_graph.invoke(initial_state)