"""
vision_extractor.py
Amphibious in-memory multimodal extraction engine using Qwen 2.5-VL (via Ollama + LiteLLM).
Enforces the BlackBudgetCemeterySchema Pydantic v2 contract with zero temporary disk I/O.
"""

import base64
import io
import json
import os
import pathlib
import sys
from typing import List

import requests
from litellm import completion
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image

# Anchor project root into sys.path so 'from src.models...' resolves in both CLI and Airflow
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.schemas import BlackBudgetCemeterySchema


def pil_image_to_base64(image: Image.Image, max_dim: int = 1024) -> str:
    """
    Downscales image in RAM to max_dim and serializes to Base64 JPEG.
    Why: Capping at 1024px prevents Qwen 2.5-VL visual patch explosion and Mac RAM swap thrashing.
    """
    rgb_image = image.convert("RGB")
    # Preserve aspect ratio while capping max width/height to speed up vision prefill by ~65%
    rgb_image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    rgb_image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def load_pages_into_ram(source: str, dpi: int = 150, max_pages: int = 1) -> List[Image.Image]:
    """
    Amphibious loader: accepts a local file path (.pdf, .jpg, .png) OR an HTTP/HTTPS URL
    and returns a list of PIL.Image objects in memory.
    """
    if source.startswith(("http://", "https://")):
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        resp = requests.get(source, headers=headers, timeout=30)
        resp.raise_for_status()

        if source.lower().endswith(".pdf") or b"%PDF" in resp.content[:10]:
            return convert_from_bytes(resp.content, dpi=dpi, first_page=1, last_page=max_pages)
        return [Image.open(io.BytesIO(resp.content))]

    if not os.path.exists(source):
        raise FileNotFoundError(f"Archive target not found at path: {source}")

    if source.lower().endswith(".pdf"):
        return convert_from_path(source, dpi=dpi, first_page=1, last_page=max_pages)
    return [Image.open(source)]


def extract_document_intelligence(
    source: str,
    nara_id: str = "NARA-595466-09204",
    dpi: int = 150,
    max_pages: int = 1,
    ollama_base_url: str = "http://localhost:11435",
) -> BlackBudgetCemeterySchema:
    """
    Streams document pages into Qwen 2.5-VL (3B) and returns a validated BlackBudgetCemeterySchema object.
    Uses a flat JSON template to prevent 3B models from getting lost in nested Pydantic $defs references.
    """
    print(f"[*] Loading '{os.path.basename(source)}' into RAM (max_pages={max_pages})...")
    pages = load_pages_into_ram(source, dpi=dpi, max_pages=max_pages)

    # Every string field uses explicit <...> options so the 3B model knows nothing is frozen
    json_template = """{
      "nara_id": "%s",
      "document_title": "<extract exact headline or subject title>",
      "pristine_transcript": "<transcribe EVERY paragraph from top to bottom of the page in full detail>",
      "sector_alpha": {
        "craft_type": "<disc | sphere | triangle | cylinder | tic-tac | v-shape | bright light | jellyfish | egg | unknown>",
        "occupant_type": "<extract pilot, radar controller, witness role, or entity description, else unknown>",
        "telemetry_matrix": {"speed_mph": "<extracted speed>", "total_sighting_duration": "<total duration of sighting>"},
        "latitude": null,
        "longitude": null
      },
      "sector_beta": {
        "cognitive_target_coordinates": null,
        "psychoactive_compounds": [],
        "linguistic_stress_score": 5
      },
      "sector_gamma": {
        "bureaucratic_routing": ["<official government or military agencies only, e.g. USAF, CAA, CIA, FBI>"],
        "redaction_fingerprint": "<solid black marker | whited out text | page scrub | none>",
        "historical_era": "<Wartime (1940-1945) | Cold War (1947-1991) | Modern (1992-Present)>"
      }
    }""" % nara_id

    content_payload = [
        {
            "type": "text",
            "text": (
                f"You are an elite forensic archival intelligence extractor.\n"
                f"Analyze this declassified record and return ONLY a valid JSON object matching this template:\n"
                f"{json_template}\n\n"
                f"Strict Rules:\n"
                f"1. COMPLETE TRANSCRIPTION: You MUST transcribe EVERY paragraph from top to bottom into 'pristine_transcript' without cutting off early.\n"
                f"2. Replace all '<...>' placeholders with real facts from the image.\n"
                f"3. DATE MATCHING: Check the year in the text (e.g., 1952) and pick the matching 'historical_era' range (1947-1991 is 'Cold War (1947-1991)').\n"
                f"4. DYNAMIC SCORING: Change 'linguistic_stress_score' from 5 to an integer between 1 (calm report) and 10 (high urgency/alarm) based on witness tone.\n"
                f"5. GEOSPATIAL: Replace null in 'latitude' and 'longitude' with the approximate decimal coordinates of the city/airport named in the text."
            ),
        }
    ]

    for idx, page_img in enumerate(pages, start=1):
        print(f"  -> Downscaling (768px) & encoding page {idx}/{len(pages)} into Base64 RAM buffer...")
        b64_img = pil_image_to_base64(page_img, max_dim=768)
        content_payload.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
            }
        )

    print("[*] Dispatching optimized payload to Qwen 2.5-VL (7B) via LiteLLM...")
    response = completion(
        model="ollama_chat/qwen2.5vl:7b",
        messages=[{"role": "user", "content": content_payload}],
        api_base=ollama_base_url,
        response_format={"type": "json_object"},
        num_ctx=4096,
        max_tokens=1024,
        temperature=0.0,
        timeout=300,
    )

    raw_json_str = response.choices[0].message.content


    # Enforce strict Pydantic v2 contract validation on the returned JSON string
    return BlackBudgetCemeterySchema.model_validate_json(raw_json_str)


if __name__ == "__main__":
    # Test against the authentic NARA Blue Book scan unpacked from 595466.zip
    nara_sample = PROJECT_ROOT / "data" / "raw" / "nara_595466" / "09204_2004_001_a.jpg"

    extracted_record = extract_document_intelligence(str(nara_sample), nara_id="NARA-595466-09204-001")
    print("\n[+] VALIDATED PYDANTIC v2 CONTRACT OUTPUT:")
    print(extracted_record.model_dump_json(indent=2))