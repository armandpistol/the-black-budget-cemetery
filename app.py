# noinspection SqlNoDataSourceInspection,SqlResolve
"""
app.py
THE BLACK-BUDGET CEMETERY // R.E.A.P.E.R. [MOD-0] (armandpistol.dev)
Retrieval Engine for Autonomous Processing & Entity Resolution
"""

import html
import json
import os
import pathlib
import sys
import time
from typing import List, Tuple

from dotenv import load_dotenv
import gradio as gr
import litellm
import pandas as pd
import plotly.express as px
import psycopg2

litellm.suppress_debug_info = True

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from src.agents.sector_graph import interrogate_cemetery

# =====================================================================
# CLANDESTINE BUNKER CSS (#0A0907 Burnt Bakelite + #D91B24 Threat Crimson)
# =====================================================================
TECH_NOIR_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Share+Tech+Mono&display=swap');

body, .gradio-container {
    background-color: #0A0907 !important;
    background-image: radial-gradient(circle at 50% 12%, #14110d 0%, #0A0907 80%) !important;
    color: #d6d1c7 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 15px !important;
}

/* Single Ghost-Like Horizontal Cathode Sweep Line passing slowly down the monitor */
.gradio-container::before {
    content: "";
    position: fixed;
    top: -15%;
    left: 0;
    width: 100%;
    height: 90px;
    background: linear-gradient(
        180deg,
        rgba(217, 27, 36, 0) 0%,
        rgba(217, 27, 36, 0.04) 45%,
        rgba(0, 255, 102, 0.07) 50%,
        rgba(217, 27, 36, 0) 100%
    );
    z-index: 9998;
    pointer-events: none;
    animation: crt-ghost-sweep 18s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
@keyframes crt-ghost-sweep {
    0%   { top: -15%; opacity: 0; }
    10%  { opacity: 1; }
    90%  { opacity: 1; }
    100% { top: 115%; opacity: 0; }
}

/* Centered Clandestine Bunker Main Header */
.crt-banner {
    background: linear-gradient(180deg, #120f0c 0%, #0A0907 100%);
    border: 1px solid #2b231d;
    border-top: 3px solid #D91B24;
    border-bottom: 2px solid #2b231d;
    padding: 20px 24px;
    margin-bottom: 14px;
    text-align: center;
    box-shadow: inset 0 0 45px rgba(0, 0, 0, 0.9), 0 4px 20px rgba(0, 0, 0, 0.6);
}
.crt-banner .classified-stamp {
    color: #D91B24;
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 3.5px;
    margin-bottom: 6px;
    text-shadow: 0 0 8px rgba(217, 27, 36, 0.45);
}
.crt-banner h1 {
    color: #ede8df !important;
    font-family: 'Black Ops One', system-ui, sans-serif !important;
    font-weight: 400 !important;
    letter-spacing: 5px;
    font-size: 2.35rem;
    margin: 4px 0 8px 0;
    text-shadow: 0 3px 12px rgba(0, 0, 0, 0.95), 0 0 20px rgba(217, 27, 36, 0.28);
}
.crt-banner p {
    color: #8c7f70 !important;
    margin: 0;
    font-size: 0.82rem;
    letter-spacing: 2px;
}

/* Left Column: Mechanical Tactical Grid Structure */
.tactical-hud-chassis {
    background-color: #0d0b09;
    border: 2px solid #28211b;
    box-shadow: inset 0 2px 10px rgba(0,0,0,0.95);
    margin-top: 8px;
    font-family: 'IBM Plex Mono', monospace;
}
.tactical-hud-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #16120e;
    border-bottom: 1px solid #28211b;
    padding: 6px 12px;
    font-size: 0.76rem;
    letter-spacing: 1.5px;
    color: #9c8f7f;
}
.hud-corner {
    color: #D91B24;
    font-weight: 700;
}
.hud-sys-title {
    color: #d6d1c7;
    font-weight: 600;
}
.hud-lock-lamp {
    color: #00FF66;
    font-weight: 600;
    text-shadow: 0 0 6px rgba(0, 255, 102, 0.5);
    display: flex;
    align-items: center;
    gap: 6px;
}
.led-green {
    width: 8px;
    height: 8px;
    background-color: #00FF66;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 8px #00FF66;
}
.led-standby {
    width: 8px;
    height: 8px;
    background-color: #D91B24;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 8px #D91B24;
}
.tactical-grid-matrix {
    display: grid;
    grid-template-columns: 1fr 1fr;
    background-color: #28211b;
    gap: 1px;
}
.tactical-cell {
    background-color: #0b0907;
    padding: 10px 14px;
}
.cell-index {
    font-size: 0.68rem;
    color: #6e6256;
    letter-spacing: 1.5px;
    margin-bottom: 4px;
    font-weight: 600;
}
.cell-value {
    font-size: 0.78rem;
    line-height: 1.35;
    color: #e6e1d6;
    font-weight: 600;
    word-break: break-word;
    white-space: normal;
}
.cell-crimson {
    color: #ff4750 !important;
    text-shadow: 0 0 6px rgba(217, 27, 36, 0.35);
}
.cell-phosphor {
    color: #00FF66 !important;
    text-shadow: 0 0 6px rgba(0, 255, 102, 0.35);
}

/* Right Column: Heavy Hardware Flip-Switch Agent Routing */
.hardware-switch-bank label.svelte-1f354aw,
.hardware-switch-bank label {
    background: linear-gradient(180deg, #14110e 0%, #0c0a08 100%) !important;
    border: 1px solid #2b231c !important;
    border-left: 4px solid #4a1216 !important;
    border-radius: 2px !important;
    padding: 9px 14px !important;
    margin-bottom: 6px !important;
    color: #8c7f70 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.8px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 2px 4px rgba(0,0,0,0.8) !important;
    transition: all 0.18s cubic-bezier(0.2, 0.85, 0.3, 1.1) !important;
    cursor: pointer !important;
}
.hardware-switch-bank label:hover {
    border-color: #5c4b3b !important;
    color: #d6d1c7 !important;
}
/* Flip-Switch Engaged State: Unlit Red/Amber -> Glowing Phosphor Green (#00FF66) */
.hardware-switch-bank label.selected,
.hardware-switch-bank label:has(input:checked) {
    background: linear-gradient(90deg, rgba(0, 255, 102, 0.10) 0%, #0f1410 100%) !important;
    border: 1px solid #00FF66 !important;
    border-left: 6px solid #00FF66 !important;
    color: #00FF66 !important;
    text-shadow: 0 0 8px rgba(0, 255, 102, 0.45) !important;
    box-shadow: 0 0 14px rgba(0, 255, 102, 0.18), inset 0 0 10px rgba(0, 255, 102, 0.08) !important;
    transform: translateX(4px) !important;
}
.hardware-switch-bank input[type="radio"] {
    accent-color: #00FF66 !important;
}

/* Spring-Loaded Mechanical Console Execute Button (#D91B24 Threat Crimson) */
button.primary {
    background: linear-gradient(180deg, #9e141b 0%, #6e0b10 100%) !important;
    color: #ffffff !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border: 2px solid #D91B24 !important;
    border-radius: 3px !important;
    padding: 13px 18px !important;
    box-shadow:
        0 6px 0 #380407,
        0 10px 20px rgba(0, 0, 0, 0.9),
        inset 0 1px 1px rgba(255, 180, 180, 0.35),
        0 0 18px rgba(217, 27, 36, 0.35) !important;
    transition: transform 0.06s ease, box-shadow 0.06s ease, background 0.15s ease !important;
}
button.primary:hover {
    background: linear-gradient(180deg, #D91B24 0%, #8f1016 100%) !important;
    box-shadow:
        0 6px 0 #380407,
        0 10px 24px rgba(217, 27, 36, 0.55),
        inset 0 1px 2px rgba(255, 220, 220, 0.5) !important;
}
button.primary:active {
    transform: translateY(4px) !important;
    box-shadow:
        0 2px 0 #380407,
        0 3px 8px rgba(0, 0, 0, 0.95),
        inset 0 2px 6px rgba(0, 0, 0, 0.7) !important;
}

button.secondary {
    background-color: #110e0b !important;
    color: #9c8f7f !important;
    border: 1px solid #2b231d !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.82rem !important;
}
button.secondary:hover {
    border-color: #D91B24 !important;
    color: #ff5c64 !important;
}

textarea, input, select {
    background-color: #0e0c09 !important;
    color: #ede8df !important;
    border: 1px solid #2b231d !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 14.5px !important;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.85) !important;
}
textarea:focus {
    border-color: #D91B24 !important;
    box-shadow: 0 0 10px rgba(217, 27, 36, 0.25), inset 0 2px 8px rgba(0,0,0,0.85) !important;
}

/* Asynchronous Teletype Console & High-Voltage Radioactive Phosphor Stream */
.teletype-console-housing {
    background-color: #080705;
    border: 2px solid #261f19;
    border-top: 2px solid #D91B24;
    padding: 18px 22px;
    min-height: 260px;
    box-shadow: inset 0 0 35px rgba(0, 0, 0, 0.95);
    font-family: 'IBM Plex Mono', monospace;
}
.agent-transmission-block {
    background-color: #0d0b09;
    border: 1px solid #241e18;
    padding: 16px 20px;
    margin-bottom: 18px;
}
.agent-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    margin-bottom: 12px;
    border-bottom: 1px solid #241e18;
    font-weight: 700;
    font-size: 0.98rem;
    letter-spacing: 1.4px;
}
.agent-clearance-tag {
    font-size: 0.72rem;
    letter-spacing: 1.5px;
    padding: 2px 8px;
    border: 1px solid currentColor;
    opacity: 0.85;
}

/* Distinct Institutional Agent Header Tones */
.tone-alpha .agent-header-bar {
    color: #00F0FF;
    border-bottom-color: rgba(0, 240, 255, 0.35);
    text-shadow: 0 0 8px rgba(0, 240, 255, 0.45);
}
.tone-alpha { border-left: 4px solid #00F0FF; }

.tone-beta .agent-header-bar {
    color: #FF00FF;
    border-bottom-color: rgba(255, 0, 255, 0.35);
    text-shadow: 0 0 8px rgba(255, 0, 255, 0.45);
}
.tone-beta { border-left: 4px solid #FF00FF; }

.tone-gamma .agent-header-bar {
    color: #9D43FA;
    border-bottom-color: rgba(157, 67, 250, 0.4);
    text-shadow: 0 0 8px rgba(157, 67, 250, 0.5);
}
.tone-gamma { border-left: 4px solid #9D43FA; }

/* Radioactive Phosphor Text & Blinking High-Voltage Cursor */
.agent-stream-body {
    font-size: 15.5px;
    line-height: 1.75;
    color: #d8e6df;
    text-shadow: 0 0 4px rgba(0, 255, 102, 0.14);
    white-space: pre-wrap;
}
.typing-active {
    color: #e4fff0;
    text-shadow: 0 0 7px rgba(0, 255, 102, 0.38);
}
.rad-cursor {
    display: inline-block;
    color: #00FF66;
    font-weight: 700;
    margin-left: 3px;
    text-shadow: 0 0 10px #00FF66, 0 0 20px #00FF66;
    animation: rad-blink 0.55s steps(2, start) infinite;
}
@keyframes rad-blink {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0; }
}

/* Regex-Wrapped [CASE-ID] Tracking Stamp */
.case-ref-tag {
    display: inline-block;
    background-color: rgba(217, 27, 36, 0.15);
    border: 1px solid #D91B24;
    color: #ff6b72;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.85em;
    font-weight: 600;
    padding: 0px 6px;
    margin: 0 2px;
    border-radius: 2px;
    letter-spacing: 0.6px;
    text-shadow: 0 0 6px rgba(217, 27, 36, 0.4);
}
"""

# =====================================================================
# VANILLA JS ASYNCHRONOUS TELETYPE EVENT QUEUE (R.E.A.P.E.R. [MOD-0])
# =====================================================================
TELETYPE_ENGINE_HEAD = """
<script>
(function() {
    document.documentElement.classList.add("dark");
        if (document.body) document.body.classList.add("dark");
    window._reaperLastRunId = "";
    window._reaperQueueToken = 0;

    function tokenizeHtmlPreservingBadges(htmlStr) {
        // Splits text character-by-character while keeping <span class="case-ref-tag">...</span> badges atomic
        const regex = /(<span class="case-ref-tag">.*?<\\/span>)/g;
        const parts = htmlStr.split(regex);
        const tokens = [];
        for (const part of parts) {
            if (part.startsWith('<span class="case-ref-tag">')) {
                tokens.push(part);
            } else {
                // Single-character mechanical strike for authentic, readable teletype pacing
                for (let i = 0; i < part.length; i += 1) {
                    tokens.push(part[i]);
                }
            }
        }
        return tokens;
    }

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function runSequentialTeletypeQueue(agents, queueToken) {
        const screen = document.getElementById("reaper-teletype-screen");
        if (!screen) return;
        screen.innerHTML = "";

        for (let idx = 0; idx < agents.length; idx++) {
            if (window._reaperQueueToken !== queueToken) return;
            const agent = agents[idx];

            const block = document.createElement("div");
            block.className = "agent-transmission-block " + (agent.theme_class || "tone-alpha");

            const header = document.createElement("div");
            header.className = "agent-header-bar";
            header.innerHTML = `
                <span>📡 ${agent.codename}</span>
                <span class="agent-clearance-tag">${agent.clearance || "CLASSIFIED"}</span>
            `;

            const body = document.createElement("div");
            body.className = "agent-stream-body typing-active";

            const contentSpan = document.createElement("span");
            const cursorSpan = document.createElement("span");
            cursorSpan.className = "rad-cursor";
            cursorSpan.textContent = "█";

            body.appendChild(contentSpan);
            body.appendChild(cursorSpan);
            block.appendChild(header);
            block.appendChild(body);
            screen.appendChild(block);

            const tokens = tokenizeHtmlPreservingBadges(agent.html_body || "");
            let accumulated = "";

            for (let t = 0; t < tokens.length; t++) {
                if (window._reaperQueueToken !== queueToken) return;
                accumulated += tokens[t];
                contentSpan.innerHTML = accumulated;

                if (t % 25 === 0) {
                    block.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }
                // 24ms per character (~40 chars/sec) for deliberate Cold War teletype readability
                await sleep(24);
            }

            body.classList.remove("typing-active");
            if (idx < agents.length - 1) {
                cursorSpan.remove();
                // 650ms mechanical relay pause before the next agent channel opens
                await sleep(650);
            }
        }
    }

    setInterval(() => {
        document.body.classList.add("dark");
        const payloadEl = document.getElementById("reaper-teletype-payload");
        if (!payloadEl) return;
        const runId = payloadEl.getAttribute("data-run-id");
        if (runId && runId !== window._reaperLastRunId) {
            window._reaperLastRunId = runId;
            window._reaperQueueToken += 1;
            const currentToken = window._reaperQueueToken;
            try {
                const rawJson = payloadEl.getAttribute("data-agents") || "[]";
                const agents = JSON.parse(rawJson);
                if (agents.length > 0) {
                    runSequentialTeletypeQueue(agents, currentToken);
                }
            } catch (e) {
                console.error("R.E.A.P.E.R. [MOD-0] Teletype Queue Error:", e);
            }
        }
    }, 120);
})();
</script>
"""

STANDBY_HUD_HTML = """
<div class="tactical-hud-chassis">
    <div class="tactical-hud-topbar">
        <span class="hud-corner">[+]</span>
        <span class="hud-sys-title">R.E.A.P.E.R. [MOD-0] // ENTITY RESOLUTION ARRAY</span>
        <span style="color: #D91B24; font-weight: 700; display:flex; align-items:center; gap:6px;">
            <span class="led-standby"></span> STANDBY
        </span>
        <span class="hud-corner">[+]</span>
    </div>
    <div class="tactical-grid-matrix">
        <div class="tactical-cell">
            <div class="cell-index">01 // PRIMARY DOSSIER LOCK</div>
            <div class="cell-value cell-crimson">AWAITING DIRECTIVE</div>
        </div>
        <div class="tactical-cell">
            <div class="cell-index">02 // ENTITY CORRELATION</div>
            <div class="cell-value">33 REELS + 3 MONOGRAPHS ARMED</div>
        </div>
        <div class="tactical-cell">
            <div class="cell-index">03 // GEODETIC SRID-4326</div>
            <div class="cell-value">GLOBAL RADAR STANDBY</div>
        </div>
        <div class="tactical-cell">
            <div class="cell-index">04 // DISPATCHED AGENT BUS</div>
            <div class="cell-value cell-phosphor">DRACO [α] // SAPELLI [β] // CALLISTA [γ]</div>
        </div>
    </div>
</div>
"""

STANDBY_CONSOLE_HTML = """
<div class="teletype-console-housing">
    <div id="reaper-teletype-screen">
        <div style="color: #8c7f70; font-size: 0.92rem; letter-spacing: 1px;">
            [R.E.A.P.E.R. [MOD-0] TELETYPE QUEUE ARMED] :: SELECT A CLASSIFIED DIRECTIVE PRESET OR ENTER COMMAND ABOVE AND DEPRESS THE CRIMSON SWITCH...
            <span class="rad-cursor">█</span>
        </div>
    </div>
</div>
"""

SECTOR_ALPHA_LABEL = "AGENT ALPHA // DRACO (AEROSPACE & RADAR)"
SECTOR_BETA_LABEL = "AGENT BETA // DR. SAPELLI (COGNITIVE & PSYCHOTRONICS)"
SECTOR_GAMMA_LABEL = "AGENT GAMMA // CALLISTA (COUNTERINTEL & FORENSICS)"

SECTOR_ORDER = [SECTOR_ALPHA_LABEL, SECTOR_BETA_LABEL, SECTOR_GAMMA_LABEL]
SECTOR_COLOR_MAP = {
    SECTOR_ALPHA_LABEL: "#00F0FF",
    SECTOR_BETA_LABEL: "#FF00FF",
    SECTOR_GAMMA_LABEL: "#9D43FA",
}

def classify_record_sector(row: pd.Series) -> str:
    """Maps raw archive codes into the 3 exact Agent Channel Routing labels."""
    archive = str(row.get("source_archive", "")).upper()
    title = str(row.get("document_title", "")).upper()
    if any(k in archive or k in title for k in ("MKULTRA", "STARGATE", "SCANATE", "SUNSTREAK", "BLUEBIRD", "ARTICHOKE", "MKDELTA", "HILL")):
        return SECTOR_BETA_LABEL
    if any(k in archive or k in title for k in ("ROBERTSON", "MAJESTIC", "68875395", "595175", "493468579")):
        return SECTOR_GAMMA_LABEL
    return SECTOR_ALPHA_LABEL


def fetch_vault_dataframe(deduplicate_pages: bool = True) -> pd.DataFrame:
    """Queries marts.mart_forensic_matrix and replaces NULL/NaN with clean 'N/A' strings."""
    pooler_url = os.getenv("SUPABASE_POOLER_URL")
    conn = psycopg2.connect(pooler_url)
    try:
        query = """
            SELECT
                nara_id,
                source_archive,
                document_title,
                historical_era,
                craft_type,
                occupant_type,
                reported_speed_mph,
                sighting_duration,
                linguistic_stress_score,
                redaction_fingerprint,
                bureaucratic_routing_json::text AS bureaucratic_routing,
                psychoactive_compounds_json::text AS psychoactive_compounds,
                cognitive_target_coordinates,
                latitude,
                longitude,
                record_granularity,
                pristine_transcript
            FROM marts.mart_forensic_matrix
            ORDER BY ingested_at DESC;
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            df["intelligence_sector"] = df.apply(classify_record_sector, axis=1)
            df = df.fillna("N/A")
            if deduplicate_pages:
                df = df[~df["nara_id"].str.contains(r"NARA-595466-092(?:04|57)-200(?:4|5)-00[234]-A", regex=True)]
        return df
    finally:
        conn.close()


def build_postgis_radar_map() -> Tuple[object, str]:
    """
    Renders a full-width, wall-to-wall 3-Sector PostGIS radar map on Burnt Bakelite (#0A0907),
    painting inland lakes dark (#080705) and ordering the legend strictly ALPHA -> BETA -> GAMMA.
    """
    df = fetch_vault_dataframe(deduplicate_pages=True)
    if df.empty:
        return None, "NO TELEMETRY RECORDS IN VAULT"

    fig = px.scatter_geo(
        df,
        lat="latitude",
        lon="longitude",
        hover_name="document_title",
        hover_data={
            "nara_id": True,
            "intelligence_sector": True,
            "craft_type": True,
            "occupant_type": True,
            "linguistic_stress_score": True,
            "redaction_fingerprint": True,
            "latitude": ":.4f",
            "longitude": ":.4f",
        },
        color="intelligence_sector",
        category_orders={"intelligence_sector": SECTOR_ORDER},
        color_discrete_map=SECTOR_COLOR_MAP,
        size="linguistic_stress_score",
        size_max=18,
        projection="equirectangular",
        title="POSTGIS SRID-4326 // GLOBAL 3-SECTOR ANOMALY & BLACK-BUDGET RADAR",
    )

    fig.update_geos(
        bgcolor="#0A0907",
        showland=True,
        landcolor="#15120e",
        showocean=True,
        oceancolor="#080705",
        # Paint Great Lakes & inland water bodies dark obsidian instead of default white
        showlakes=True,
        lakecolor="#080705",
        showrivers=False,
        showcountries=True,
        countrycolor="#2b231d",
        showsubunits=True,
        subunitcolor="#1f1914",
        showcoastlines=True,
        coastlinecolor="#3a2f25",
        framecolor="#2b231d",
        # Trim empty polar ice caps so the map stretches wall-to-wall across wide monitors
        lataxis_range=[-42, 72],
        lonaxis_range=[-155, 110],
    )
    fig.update_layout(
        paper_bgcolor="#0A0907",
        plot_bgcolor="#0A0907",
        font=dict(family="IBM Plex Mono, monospace", color="#d6d1c7", size=12),
        margin=dict(l=0, r=0, t=42, b=0),
        height=700,
        legend=dict(
            title="INTELLIGENCE SECTOR:",
            bgcolor="rgba(13, 11, 9, 0.94)",
            bordercolor="#28211b",
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=0.02,
            xanchor="center",
            x=0.5,
        ),
    )

    kpi_html = f"""
    <div class="tactical-hud-chassis">
        <div class="tactical-grid-matrix">
            <div class="tactical-cell">
                <div class="cell-index">VERIFIED CASES PLOTTED</div>
                <div class="cell-value cell-phosphor">{len(df)} DECLASSIFIED SITES LOCKED</div>
            </div>
            <div class="tactical-cell">
                <div class="cell-index">CHANNEL DISTRIBUTION (DRACO / SAPELLI / CALLISTA)</div>
                <div class="cell-value">{(df['intelligence_sector'] == SECTOR_ALPHA_LABEL).sum()} ALPHA // {(df['intelligence_sector'] == SECTOR_BETA_LABEL).sum()} BETA // {(df['intelligence_sector'] == SECTOR_GAMMA_LABEL).sum()} GAMMA</div>
            </div>
        </div>
    </div>
    """
    return fig, kpi_html


def get_dossier_choices() -> List[str]:
    """Returns formatted 'NARA_ID :: Title' strings for the Tab 3 Dossier Selector."""
    df = fetch_vault_dataframe(deduplicate_pages=True)
    if df.empty:
        return []
    return [f"{row['nara_id']} :: {row['document_title']}" for _, row in df.iterrows()]


def inspect_case_dossier(selection: str) -> Tuple[str, str, object]:
    """
    Renders for Tab 3:
    1. Tactical Grid Dossier Header
    2. Color-Coded 3-Agent Telemetry Cards (Draco #00F0FF, Sapelli #FF00FF, Callista #9D43FA) + Phosphor Transcript
    3. Dynamic 5-Axis Clandestine Threat Radar Scope (Scatterpolar)
    """
    import plotly.graph_objects as go
    from src.agents.sector_graph import highlight_case_citations

    df = fetch_vault_dataframe(deduplicate_pages=True)
    if df.empty:
        return "", "No records found.", None

    selected_id = selection.split(" :: ")[0] if selection else df.iloc[0]["nara_id"]
    match = df[df["nara_id"] == selected_id]
    row = match.iloc[0] if not match.empty else df.iloc[0]

    sector_str = str(row["intelligence_sector"])
    sector_color = SECTOR_COLOR_MAP.get(sector_str, "#9D43FA")

    dossier_header_html = f"""
    <div class="tactical-hud-chassis">
        <div class="tactical-hud-topbar">
            <span class="hud-corner">[+]</span>
            <span class="hud-sys-title">R.E.A.P.E.R. [MOD-0] // CLASSIFIED DOSSIER INSPECTOR</span>
            <span class="hud-lock-lamp"><span class="led-green"></span> DECLASSIFIED VAULT RECORD</span>
            <span class="hud-corner">[+]</span>
        </div>
        <div class="tactical-grid-matrix">
            <div class="tactical-cell">
                <div class="cell-index">01 // RECORD ID</div>
                <div class="cell-value cell-crimson">{row['nara_id']}</div>
            </div>
            <div class="tactical-cell">
                <div class="cell-index">02 // ASSIGNED AGENT CHANNEL</div>
                <div class="cell-value" style="color: {sector_color};">{sector_str}</div>
            </div>
            <div class="tactical-cell">
                <div class="cell-index">03 // SUBJECT TITLE</div>
                <div class="cell-value">{row['document_title']}</div>
            </div>
            <div class="tactical-cell">
                <div class="cell-index">04 // ERA &amp; GEODETIC COORDS</div>
                <div class="cell-value cell-phosphor">{row['historical_era']} // ({row['latitude']:.4f}, {row['longitude']:.4f})</div>
            </div>
        </div>
    </div>
    """

    safe_transcript = highlight_case_citations(str(row["pristine_transcript"]))

    # Color-Coded Institutional Telemetry Cards + Recessed Phosphor Microfilm Transcript Viewer
    dossier_body_html = f"""
    <div style="margin-top: 10px;">
        <div class="agent-transmission-block tone-alpha" style="margin-bottom: 10px; padding: 12px 16px;">
            <div class="agent-header-bar" style="margin-bottom: 8px; font-size: 0.86rem;">
                <span>📡 AGENT ALPHA // DRACO — AEROSPACE &amp; RADAR</span>
                <span class="agent-clearance-tag">SAR-ALPHA</span>
            </div>
            <div class="tactical-grid-matrix" style="border: 1px solid rgba(0, 240, 255, 0.25);">
                <div class="tactical-cell"><div class="cell-index">CRAFT PROFILE</div><div class="cell-value" style="color:#00F0FF;">{row['craft_type']}</div></div>
                <div class="tactical-cell"><div class="cell-index">OCCUPANTS / ENTITIES</div><div class="cell-value">{row['occupant_type']}</div></div>
                <div class="tactical-cell"><div class="cell-index">REPORTED SPEED (MPH)</div><div class="cell-value">{row['reported_speed_mph']}</div></div>
                <div class="tactical-cell"><div class="cell-index">OBSERVATION DURATION</div><div class="cell-value">{row['sighting_duration']}</div></div>
            </div>
        </div>

        <div class="agent-transmission-block tone-beta" style="margin-bottom: 10px; padding: 12px 16px;">
            <div class="agent-header-bar" style="margin-bottom: 8px; font-size: 0.86rem;">
                <span>📡 AGENT BETA // DR. SAPELLI — COGNITIVE &amp; PSYCHOTRONICS</span>
                <span class="agent-clearance-tag">SAP-BETA</span>
            </div>
            <div class="tactical-grid-matrix" style="border: 1px solid rgba(255, 0, 255, 0.25);">
                <div class="tactical-cell"><div class="cell-index">WITNESS STRESS SCORE</div><div class="cell-value" style="color:#FF00FF;">{row['linguistic_stress_score']} / 10</div></div>
                <div class="tactical-cell"><div class="cell-index">CRV TARGET COORDS</div><div class="cell-value">{row['cognitive_target_coordinates']}</div></div>
                <div class="tactical-cell" style="grid-column: span 2;"><div class="cell-index">PSYCHOACTIVE / BIO-COMPOUNDS LOGGED</div><div class="cell-value">{row['psychoactive_compounds']}</div></div>
            </div>
        </div>

        <div class="agent-transmission-block tone-gamma" style="margin-bottom: 14px; padding: 12px 16px;">
            <div class="agent-header-bar" style="margin-bottom: 8px; font-size: 0.86rem;">
                <span>📡 AGENT GAMMA // CALLISTA — COUNTERINTEL &amp; FORENSICS</span>
                <span class="agent-clearance-tag">UMBRA-GAMMA</span>
            </div>
            <div class="tactical-grid-matrix" style="border: 1px solid rgba(157, 67, 250, 0.3);">
                <div class="tactical-cell"><div class="cell-index">CENSORSHIP FINGERPRINT</div><div class="cell-value" style="color:#9D43FA;">{row['redaction_fingerprint']}</div></div>
                <div class="tactical-cell"><div class="cell-index">RECORD GRANULARITY</div><div class="cell-value">{row['record_granularity']}</div></div>
                <div class="tactical-cell" style="grid-column: span 2;"><div class="cell-index">BUREAUCRATIC ROUTING CHAIN</div><div class="cell-value">{row['bureaucratic_routing']}</div></div>
            </div>
        </div>

        <div class="teletype-console-housing" style="min-height: 180px;">
            <div class="agent-header-bar" style="color: #00FF66; border-bottom-color: #1f3826; margin-bottom: 10px;">
                <span>📄 PRISTINE ARCHIVAL TRANSCRIPT // QWEN 2.5-VL OPTICAL EXTRACTION</span>
                <span class="agent-clearance-tag" style="color: #00FF66;">VERIFIED OCR</span>
            </div>
            <div class="agent-stream-body">{safe_transcript}</div>
        </div>
    </div>
    """

    # Compute 5-Axis Clandestine Threat Signature (0-10 scale) for the selected dossier
    stress_val = float(row["linguistic_stress_score"]) if str(row["linguistic_stress_score"]).isdigit() else 5.0
    redaction_str = str(row["redaction_fingerprint"]).lower()
    redaction_val = 9.0 if any(w in redaction_str for w in ("black", "scrub", "marker")) else (6.5 if "white" in redaction_str else 2.5)
    routing_count = str(row["bureaucratic_routing"]).count(",") + 1 if row["bureaucratic_routing"] != "[]" else 1
    routing_val = min(10.0, routing_count * 2.8)
    kinematic_val = 9.0 if str(row["reported_speed_mph"]) not in ("N/A", "unknown", "") else (7.0 if str(row["craft_type"]) not in ("radar / administrative memo", "unknown") else 3.0)
    entity_val = 9.5 if (str(row["occupant_type"]) != "none observed" or str(row["psychoactive_compounds"]) != "[]" or str(row["cognitive_target_coordinates"]) != "N/A") else 3.0

    categories = [
        "PSYCHOMETRIC<br>STRESS",
        "REDACTION<br>SEVERITY",
        "ROUTING<br>DEPTH",
        "KINEMATIC<br>ANOMALY",
        "ENTITY /<br>BIO-OPS INDEX",
        "PSYCHOMETRIC<br>STRESS",
    ]
    case_scores = [stress_val, redaction_val, routing_val, kinematic_val, entity_val, stress_val]
    vault_baseline = [4.8, 5.2, 5.5, 5.8, 4.5, 4.8]

    fill_rgba = (
        "rgba(0, 240, 255, 0.22)"
        if sector_color == "#00F0FF"
        else ("rgba(255, 0, 255, 0.20)" if sector_color == "#FF00FF" else "rgba(157, 67, 250, 0.24)")
    )

    radar_fig = go.Figure()
    radar_fig.add_trace(
        go.Scatterpolar(
            r=vault_baseline,
            theta=categories,
            fill="toself",
            name="VAULT BASELINE MEAN",
            line=dict(color="#6e6256", dash="dot", width=1.5),
            fillcolor="rgba(110, 98, 86, 0.12)",
        )
    )
    radar_fig.add_trace(
        go.Scatterpolar(
            r=case_scores,
            theta=categories,
            fill="toself",
            name="SELECTED DOSSIER SIGNATURE",
            line=dict(color=sector_color, width=2.5),
            fillcolor=fill_rgba,
        )
    )

    radar_fig.update_layout(
        title="R.E.A.P.E.R. [MOD-0] // 5-AXIS CLANDESTINE THREAT SIGNATURE",
        paper_bgcolor="#0A0907",
        plot_bgcolor="#0A0907",
        font=dict(family="IBM Plex Mono, monospace", color="#d6d1c7", size=11),
        height=540,
        margin=dict(l=90, r=90, t=55, b=45),
        polar=dict(
            bgcolor="#0d0b09",
            radialaxis=dict(visible=True, range=[0, 10], gridcolor="#28211b", linecolor="#28211b", tickfont=dict(size=9, color="#8c7f70")),
            angularaxis=dict(gridcolor="#28211b", linecolor="#D91B24"),
        ),
        legend=dict(
            bgcolor="rgba(13, 11, 9, 0.92)",
            bordercolor="#28211b",
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
        ),
    )
    return dossier_header_html, dossier_body_html, radar_fig


def run_reaper_interrogation(query: str, sector_mode_label: str) -> Tuple[str, str, pd.DataFrame]:
    """
    Executes the LangGraph R.E.A.P.E.R. [MOD-0] workflow and packages the structured
    agent array into the Vanilla JS Asynchronous Teletype Queue container.
    """
    if not query or not query.strip():
        return STANDBY_HUD_HTML, STANDBY_CONSOLE_HTML, pd.DataFrame()

    mode_map = {
        "WAR_ROOM // ALL 3 AGENTS (DRACO + DR. SAPELLI + CALLISTA)": "WAR_ROOM",
        "AUTO-DISPATCH // R.E.A.P.E.R. [MOD-0] SMART ROUTER": "AUTO",
        "AGENT ALPHA ONLY // DRACO (AEROSPACE & RADAR)": "ALPHA",
        "AGENT BETA ONLY // DR. SAPELLI (COGNITIVE & PSYCHOTRONICS)": "BETA",
        "AGENT GAMMA ONLY // CALLISTA (COUNTERINTEL & FORENSICS)": "GAMMA",
    }
    mode_code = mode_map.get(sector_mode_label, "WAR_ROOM")

    state_out = interrogate_cemetery(query.strip(), sector_mode=mode_code)
    matched_df = pd.DataFrame(state_out.get("vault_cases", []))
    if not matched_df.empty:
        cols = [
            "nara_id",
            "document_title",
            "similarity",
            "craft_type",
            "occupant_type",
            "linguistic_stress_score",
            "redaction_fingerprint",
        ]
        matched_df = matched_df[[c for c in cols if c in matched_df.columns]]

    run_id = str(time.time())
    escaped_json = html.escape(json.dumps(state_out.get("agent_outputs", [])), quote=True)

    teletype_stage_html = f"""
    <div id="reaper-teletype-payload" data-run-id="{run_id}" data-agents="{escaped_json}" style="display:none;"></div>
    <div class="teletype-console-housing">
        <div id="reaper-teletype-screen"></div>
    </div>
    """

    return state_out["reaper_header"], teletype_stage_html, matched_df


with gr.Blocks(
    css=TECH_NOIR_CSS,
    head=TELETYPE_ENGINE_HEAD,
    js="() => { document.body.classList.add('dark'); document.documentElement.classList.add('dark'); }",
    title="THE BLACK-BUDGET CEMETERY // R.E.A.P.E.R. [MOD-0]",
) as demo:
    gr.HTML(
        """
        <div class="crt-banner">
            <div class="classified-stamp">TOP SECRET // UMBRA-NOFORN // CLANDESTINE ARCHIVAL ARRAY</div>
            <h1>THE BLACK-BUDGET CEMETERY</h1>
            <p>R.E.A.P.E.R. [MOD-0] // RETRIEVAL ENGINE FOR AUTONOMOUS PROCESSING &amp; ENTITY RESOLUTION</p>
        </div>
        """
    )

    with gr.Tabs():
        # TAB 1: R.E.A.P.E.R. [MOD-0] WAR-ROOM INTERROGATION CONSOLE
        with gr.TabItem("📡 R.E.A.P.E.R. [MOD-0] // WAR-ROOM INTERROGATION"):
            with gr.Row():
                # Left Column: Command Directive + Mechanical Tactical Grid HUD
                with gr.Column(scale=3):
                    query_box = gr.Textbox(
                        label="R.E.A.P.E.R. [MOD-0] COMMAND DIRECTIVE",
                        placeholder="Enter forensic directive (e.g., 'Compare radar & occupant evidence in Betty & Barney Hill vs Socorro...')",
                        lines=3,
                    )
                    tactical_hud_display = gr.HTML(value=STANDBY_HUD_HTML)

                # Right Column: Hardware Flip-Switch Bank + Spring-Loaded Crimson Execute Switch
                with gr.Column(scale=2):
                    sector_selector = gr.Radio(
                        choices=[
                            "WAR_ROOM // ALL 3 AGENTS (DRACO + DR. SAPELLI + CALLISTA)",
                            "AUTO-DISPATCH // R.E.A.P.E.R. [MOD-0] SMART ROUTER",
                            "AGENT ALPHA ONLY // DRACO (AEROSPACE & RADAR)",
                            "AGENT BETA ONLY // DR. SAPELLI (COGNITIVE & PSYCHOTRONICS)",
                            "AGENT GAMMA ONLY // CALLISTA (COUNTERINTEL & FORENSICS)",
                        ],
                        value="WAR_ROOM // ALL 3 AGENTS (DRACO + DR. SAPELLI + CALLISTA)",
                        label="AGENT CHANNEL ROUTING (HARDWARE BUS)",
                        elem_classes=["hardware-switch-bank"],
                    )
                    fire_btn = gr.Button("💀 EXECUTE R.E.A.P.E.R. [MOD-0] SEQUENCE", variant="primary")

            gr.Markdown("#### 📂 CLASSIFIED QUICK-DIRECTIVE PRESETS:")
            with gr.Row():
                p1 = gr.Button("🛸 1961 Hill vs. 1964 Socorro CE-III Occupants & Radar", variant="secondary", size="sm")
                p2 = gr.Button("🧠 CIA MKUltra, Artichoke & Fort Detrick Neurotoxins", variant="secondary", size="sm")
                p3 = gr.Button("👁️ DIA Stargate Semipalatinsk & Sun Streak CRV Coordinates", variant="secondary", size="sm")
                p4 = gr.Button("✈️ 1976 Tehran F-4 Jamming & 1952 Washington D.C. Radar", variant="secondary", size="sm")
                p5 = gr.Button("⬛ 1953 CIA Robertson Panel & FBI Majestic-12 Cover-Ups", variant="secondary", size="sm")

            teletype_console_output = gr.HTML(value=STANDBY_CONSOLE_HTML)

            with gr.Accordion("🔍 LOCKED SUPABASE VAULT REELS (TOP PGVECTOR / SQL MATCHES)", open=False):
                matched_table = gr.Dataframe(interactive=False)

            p1.click(
                lambda: "Compare the radar and occupant evidence in the 1961 Betty & Barney Hill and 1964 Socorro cases, the psychological stress protocols, and how the CIA Robertson Panel shaped official cover-ups.",
                outputs=query_box,
            )
            p2.click(
                lambda: "Analyze the psychoactive compounds, neurotoxins, and interrogation techniques logged across CIA Projects MKULTRA, BLUEBIRD, ARTICHOKE, MKDELTA, MKNAOMI, and MKOFTEN.",
                outputs=query_box,
            )
            p3.click(
                lambda: "Examine the coordinate remote viewing (CRV) target coordinates, SRI International protocols, and bureaucratic lineage from Project SCANATE to GRILL FLAME, SUN STREAK, and STARGATE.",
                outputs=query_box,
            )
            p4.click(
                lambda: "Compare the avionics/weapons jamming in the 1976 Tehran F-4 Phantom intercept with the 1952 Washington D.C. National Airport radar-visual sightings and 1965 Project Moon Dust recovery.",
                outputs=query_box,
            )
            p5.click(
                lambda: "Expose the bureaucratic routing chains and black-marker redaction fingerprints across the 1953 CIA Robertson Panel, FBI Roswell teletype, and Majestic-12 counterintelligence files.",
                outputs=query_box,
            )

            fire_btn.click(
                fn=run_reaper_interrogation,
                inputs=[query_box, sector_selector],
                outputs=[tactical_hud_display, teletype_console_output, matched_table],
            )

        # TAB 2: INTERACTIVE POSTGIS GLOBAL ANOMALY RADAR MAP
        with gr.TabItem("🗺️ POSTGIS SRID-4326 // 3-SECTOR GLOBAL RADAR"):
            refresh_map_btn = gr.Button("🔄 REFRESH LIVE SUPABASE POSTGIS RADAR", variant="secondary")
            kpi_banner = gr.HTML()
            radar_plot = gr.Plot()

            refresh_map_btn.click(fn=build_postgis_radar_map, outputs=[radar_plot, kpi_banner])
            demo.load(fn=build_postgis_radar_map, outputs=[radar_plot, kpi_banner])

        # TAB 3: INTERACTIVE CLASSIFIED CASE DOSSIER INSPECTOR & SECTOR ANALYTICS
        with gr.TabItem("📂 CLASSIFIED EVIDENCE LOCKER // DOSSIER INSPECTOR"):
            initial_choices = get_dossier_choices()
            default_choice = initial_choices[0] if initial_choices else None
            dossier_dropdown = gr.Dropdown(
                choices=initial_choices,
                value=default_choice,
                label="SELECT DECLASSIFIED CASE REEL FROM SUPABASE VAULT",
            )
            dossier_header_box = gr.HTML()
            with gr.Row():
                with gr.Column(scale=3):
                    dossier_viewer = gr.HTML()
                with gr.Column(scale=2):
                    sector_chart = gr.Plot()

            dossier_dropdown.change(
                fn=inspect_case_dossier,
                inputs=dossier_dropdown,
                outputs=[dossier_header_box, dossier_viewer, sector_chart],
            )
            demo.load(
                fn=inspect_case_dossier,
                inputs=dossier_dropdown,
                outputs=[dossier_header_box, dossier_viewer, sector_chart],
            )


if __name__ == "__main__":
    import inspect

    DARK_MODE_JS = "() => { document.body.classList.add('dark'); document.documentElement.classList.add('dark'); }"
    launch_params = inspect.signature(demo.launch).parameters

    if "css" in launch_params:
        # Gradio 6.0+ (Hugging Face Spaces Cloud Container)
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            css=TECH_NOIR_CSS,
            head=TELETYPE_ENGINE_HEAD,
            js=DARK_MODE_JS,
        )
    else:
        # Gradio 4.x / 5.x (Local Workstation)
        demo.launch(server_name="0.0.0.0", server_port=7860)