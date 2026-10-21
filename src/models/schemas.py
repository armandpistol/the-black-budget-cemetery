from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


# =====================================================================
# SECTOR SUB-SCHEMAS (The 11 Multimodal Primitives)
# =====================================================================

class SectorAlphaSchema(BaseModel):
    """Sector Alpha: Material & Spatial Anomalies."""
    craft_type: str = Field(
        description="Visual geometric profile of the anomaly (e.g., disc, cigar, sphere, luminous, unknown)."
    )
    occupant_type: str = Field(
        description="Biological, physical, or structural descriptions of entities or occupants if explicitly logged."
    )
    telemetry_matrix: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Time-series vectors extracted from logs including calculated speed, rate of climb, and G-forces."
    )
    latitude: Optional[float] = Field(
        default=None, description="Extracted numerical coordinate marker for PostGIS insertion."
    )
    longitude: Optional[float] = Field(
        default=None, description="Extracted numerical coordinate marker for PostGIS insertion."
    )


class SectorBetaSchema(BaseModel):
    """Sector Beta: Cognitive & Psychological Operations."""
    cognitive_target_coordinates: Optional[str] = Field(
        default=None, description="Handwritten or logged remote viewing session coordinates (Stargate format)."
    )
    psychoactive_compounds: List[str] = Field(
        default_factory=list, description="Chemical nomenclature, project subcodes, or dosages identified (MKUltra)."
    )
    linguistic_stress_score: int = Field(
        description="Psychometric load scaling from 1-10 evaluated from witness brevity codes and sentence patterns."
    )


class SectorGammaSchema(BaseModel):
    """Sector Gamma: Administrative & Systemic Deception (Includes legacy Sector Delta)."""
    bureaucratic_routing: List[str] = Field(
        default_factory=list, description="Chain of custody agency stamps, handling codes, and clearance modifications."
    )
    redaction_fingerprint: str = Field(
        description="Classification of censorship methods deployed (e.g., solid black marker, text removal, page scrub)."
    )
    historical_era: str = Field(
        description="Temporal sector alignment: Wartime (1940-1945), Cold War (1947-1991), Orbital (1958-1975), Modern."
    )


# =====================================================================
# CORES MASTER SCHEMA MAINFRAME
# =====================================================================

class BlackBudgetCemeterySchema(BaseModel):
    """
    The Unified Forensic Intelligence Matrix Contract.
    Enforces absolute structured extraction via Multimodal Vision (Qwen 2.5-VL)
    before parsing downstream models directly into Supabase pgvector/PostGIS nodes.
    """
    nara_id: str = Field(description="The unique archival identification key or document sequence reference.")
    document_title: str = Field(description="The formalized or military designated subject title of the record block.")
    pristine_transcript: str = Field(
        description="Error-corrected, layout-aware Markdown transcription of the visual archival microfilm page."
    )

    # Sector Domain Compartmentalization
    sector_alpha: SectorAlphaSchema = Field(description="Material and spatial telemetry parameters.")
    sector_beta: SectorBetaSchema = Field(description="Psychological, psychometric, and psychoenergetic metrics.")
    sector_gamma: SectorGammaSchema = Field(description="Systemic deception, lineage, and redaction archetypes.")

    @field_validator('pristine_transcript')
    @classmethod  # Must be explicit
    def verify_transcript_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Vision engine failed to extract document layout string.")
        return v