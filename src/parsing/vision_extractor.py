"""
vision_extractor.py
Tri-Modal in-memory intelligence extraction engine:
- Documents & Microfilm (.pdf, .jpg, .png) -> Qwen 2.5-VL (7B)
- Archival Motion Video (.mp4, .mov)       -> OpenCV 3-Keyframe RAM Slicer -> Qwen 2.5-VL (7B)
- Declassified Audio Tapes (.mp3, .wav)    -> LiteLLM Whisper Transcription -> Qwen 2.5 (7B)
Enforces the BlackBudgetCemeterySchema Pydantic v2 contract with zero temporary disk bloat.
"""

import base64
import io
import os
import pathlib
import sys
import tempfile
from typing import List

import cv2
import requests
from litellm import completion, transcription
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image

# Anchor project root into sys.path so 'from src.models...' resolves in both CLI and Airflow
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.schemas import BlackBudgetCemeterySchema

IMAGE_DOC_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a")


def pil_image_to_base64(image: Image.Image, max_dim: int = 768) -> str:
    """
    Downscales a PIL Image in RAM to max_dim and serializes to Base64 JPEG.
    Why: Keeps vision token count compact for fast GPU prefill over SSH/LAN.
    """
    rgb_image = image.convert("RGB")
    rgb_image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    rgb_image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def extract_video_keyframes_to_ram(video_path: str, num_frames: int = 3) -> List[Image.Image]:
    """
    Samples `num_frames` evenly-spaced keyframes from an archival .mp4/.mov video into PIL Images.
    Why: Allows Qwen 2.5-VL to analyze gun-camera or radar-scope footage without frame-by-frame VRAM overload.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Failed to open video stream: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    step = max(1, total_frames // (num_frames + 1))
    keyframes: List[Image.Image] = []

    try:
        for i in range(1, num_frames + 1):
            target_idx = min(i * step, total_frames - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
            success, frame_bgr = cap.read()
            if success and frame_bgr is not None:
                # Convert OpenCV BGR array to standard RGB PIL Image in memory
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                keyframes.append(Image.fromarray(frame_rgb))
    finally:
        cap.release()

    if not keyframes:
        raise ValueError(f"No readable video frames extracted from: {video_path}")
    return keyframes


def load_visual_pages_into_ram(source: str, dpi: int = 150, max_pages: int = 1) -> List[Image.Image]:
    """
    Amphibious visual loader: accepts local or HTTP (.pdf, .jpg, .png, .mp4, .mov)
    and returns a list of PIL.Image objects in memory.
    """
    lower_src = source.lower()

    # Branch 1: Remote HTTP/HTTPS URL streaming
    if source.startswith(("http://", "https://")):
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        resp = requests.get(source, headers=headers, timeout=60)
        resp.raise_for_status()

        if lower_src.endswith(VIDEO_EXTENSIONS):
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp_vid:
                tmp_vid.write(resp.content)
                tmp_vid.flush()
                return extract_video_keyframes_to_ram(tmp_vid.name)
        if lower_src.endswith(".pdf") or b"%PDF" in resp.content[:10]:
            return convert_from_bytes(resp.content, dpi=dpi, first_page=1, last_page=max_pages)
        return [Image.open(io.BytesIO(resp.content))]

    # Branch 2: Local archive file (.pdf, .jpg, .png, .mp4)
    if not os.path.exists(source):
        raise FileNotFoundError(f"Archive target not found at path: {source}")

    if lower_src.endswith(VIDEO_EXTENSIONS):
        return extract_video_keyframes_to_ram(source)
    if lower_src.endswith(".pdf"):
        return convert_from_path(source, dpi=dpi, first_page=1, last_page=max_pages)
    return [Image.open(source)]


def transcribe_audio_file(source: str) -> str:
    """
    Transcribes declassified .mp3/.wav audio tapes using Whisper via LiteLLM (Groq LPU).
    Why: Converts raw pilot/radar-room voice recordings into text before structured Pydantic parsing.
    """
    print(f"[*] Transcribing archival audio recording '{os.path.basename(source)}' via Whisper...")
    with open(source, "rb") as audio_file:
        resp = transcription(
            model="groq/whisper-large-v3-turbo",
            file=audio_file,
        )
    return resp.text


def build_json_template(nara_id: str) -> str:
    """Returns the flat JSON template used to guide 7B structured extraction."""
    return """{
  "nara_id": "%s",
  "document_title": "<extract exact headline, case subject, or recording title>",
  "pristine_transcript": "<transcribe EVERY paragraph or spoken statement in full detail>",
  "sector_alpha": {
    "craft_type": "<disc | sphere | triangle | cylinder | tic-tac | v-shape | bright light | jellyfish | egg | unknown>",
    "occupant_type": "<biological or humanoid entities observed inside/near the anomaly, or 'none observed'>",
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
    "redaction_fingerprint": "<solid black marker | whited out text | page scrub | audio bleep | none>",
    "historical_era": "<Wartime (1940-1945) | Cold War (1947-1991) | Modern (1992-Present)>"
  }
}""" % nara_id


def extract_document_intelligence(
    source: str,
    nara_id: str = "NARA-595466-09204",
    dpi: int = 150,
    max_pages: int = 1,
    ollama_base_url: str = "http://localhost:11435",
) -> BlackBudgetCemeterySchema:
    """
    Tri-Modal router: streams Documents (.pdf/.jpg), Video Keyframes (.mp4), or Audio Tapes (.mp3/.wav)
    into Qwen 2.5-VL (7B) / Whisper and returns a validated BlackBudgetCemeterySchema object.
    """
    json_template = build_json_template(nara_id)
    strict_rules = (
        "Strict Rules:\n"
        "1. COMPLETE TRANSCRIPTION: You MUST include the full text/transcript in 'pristine_transcript' without cutting off early.\n"
        "2. Replace all '<...>' placeholders with real facts from the source.\n"
        "3. DATE MATCHING: Check the year in the record (e.g., 1952) and pick the matching 'historical_era' range (1947-1991 is 'Cold War (1947-1991)').\n"
        "4. DYNAMIC SCORING: Change 'linguistic_stress_score' from 5 to an integer between 1 (calm report) and 10 (high urgency/alarm) based on witness tone.\n"
        "5. GEOSPATIAL: Replace null in 'latitude' and 'longitude' with the approximate decimal coordinates of the city/airport/base named in the record.\n"
        "6. OCCUPANTS: For 'occupant_type', ONLY describe biological or humanoid entities inside/exiting the anomalous craft itself (use 'none observed' if only lights/craft were seen, NEVER the human pilot or witness)."
    )

    # Route A: Audio Recording (.mp3 / .wav) -> Whisper Transcription -> Qwen 7B Structuring
    if source.lower().endswith(AUDIO_EXTENSIONS):
        audio_transcript = transcribe_audio_file(source)
        content_payload = [
            {
                "type": "text",
                "text": (
                    f"You are an elite forensic archival intelligence extractor.\n"
                    f"Below is the verbatim Whisper transcription of a declassified audio recording (nara_id: {nara_id}):\n\n"
                    f"--- AUDIO TRANSCRIPT ---\n{audio_transcript}\n------------------------\n\n"
                    f"Return ONLY a valid JSON object matching this template:\n{json_template}\n\n{strict_rules}"
                ),
            }
        ]
    # Route B: Visual Document (.pdf / .jpg / .png) or Motion Video (.mp4 / .mov) -> Qwen 2.5-VL (7B)
    else:
        print(f"[*] Loading '{os.path.basename(source)}' into RAM (max_pages={max_pages})...")
        pages = load_visual_pages_into_ram(source, dpi=dpi, max_pages=max_pages)
        content_payload = [
            {
                "type": "text",
                "text": (
                    f"You are an elite forensic archival intelligence extractor.\n"
                    f"Analyze this declassified visual record and return ONLY a valid JSON object matching this template:\n"
                    f"{json_template}\n\n{strict_rules}"
                ),
            }
        ]
        for idx, page_img in enumerate(pages, start=1):
            print(f"  -> Downscaling (768px) & encoding frame {idx}/{len(pages)} into Base64 RAM buffer...")
            b64_img = pil_image_to_base64(page_img, max_dim=768)
            content_payload.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                }
            )

    print("[*] Dispatching tri-modal payload to Qwen 2.5-VL (7B) via LiteLLM...")
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
    return BlackBudgetCemeterySchema.model_validate_json(raw_json_str)


if __name__ == "__main__":
    nara_sample = PROJECT_ROOT / "data" / "raw" / "nara_595466" / "09204_2004_001_a.jpg"
    extracted_record = extract_document_intelligence(str(nara_sample), nara_id="NARA-595466-09204-001")
    print("\n[+] VALIDATED PYDANTIC v2 CONTRACT OUTPUT:")
    print(extracted_record.model_dump_json(indent=2))