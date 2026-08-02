"""
snowflake_loader.py
Loads parsed OCR output into Snowflake RAW schema.
"""

import json
import os
import pathlib
from dotenv import load_dotenv
import snowflake.connector

# Load credentials from .env file
load_dotenv()


def get_connection():
    """Create and return a Snowflake connection using .env credentials."""
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        role=os.getenv("SNOWFLAKE_ROLE")
    )


def insert_program(cursor, program_name, lead_agency, start_year, end_year, description):
    """Insert a program record if it doesn't already exist. Returns program_id."""
    cursor.execute("""
        SELECT program_id FROM programs
        WHERE program_name = %s
    """, (program_name,))
    row = cursor.fetchone()
    if row:
        print(f"  Program '{program_name}' already exists (id={row[0]})")
        return row[0]

    cursor.execute("""
        INSERT INTO programs (program_name, lead_agency, start_year, end_year, description)
        VALUES (%s, %s, %s, %s, %s)
    """, (program_name, lead_agency, start_year, end_year, description))

    cursor.execute("SELECT MAX(program_id) FROM programs")
    program_id = cursor.fetchone()[0]
    print(f"  Inserted program '{program_name}' (id={program_id})")
    return program_id


def insert_document(cursor, program_id, json_data):
    """Insert a document record from OCR JSON output."""
    cursor.execute("""
        SELECT document_id FROM documents
        WHERE source_file = %s
    """, (json_data["source_file"],))
    row = cursor.fetchone()
    if row:
        print(f"  Document '{json_data['source_file']}' already exists (id={row[0]})")
        return row[0]

    metadata = json.dumps({
        "incident_id": 17,
        "incident_number": "17",
        "program": "Blue Book",
        "nara_microfilm": "T1206",
        "nara_roll": 1,
        "source_url": "https://digitalcollections.uwyo.edu/ahcpublic/UFO/NARA_Arnold_ah12722.pdf"
    })

    cursor.execute("""
        INSERT INTO documents (
            program_id, source_file, source_agency,
            document_type, raw_text, page_count, metadata
        )
        SELECT %s, %s, %s, %s, %s, %s, PARSE_JSON(%s)
    """, (
        program_id,
        json_data["source_file"],
        "USAF",
        "case_file",
        json_data["full_text"],
        json_data["page_count"],
        metadata
    ))

    cursor.execute("SELECT MAX(document_id) FROM documents")
    document_id = cursor.fetchone()[0]
    print(f"  Inserted document '{json_data['source_file']}' (id={document_id})")
    return document_id


if __name__ == "__main__":
    json_path = pathlib.Path(__file__).parents[2] / \
        "data" / "processed" / "blue_book_incident_17_kenneth_arnold.json"

    print(f"Loading {json_path.name}...")
    with open(json_path, "r", encoding="utf-8") as f:
        ocr_data = json.load(f)

    print("Connecting to Snowflake...")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("Inserting program...")
        program_id = insert_program(
            cursor,
            program_name="Blue Book",
            lead_agency="USAF",
            start_year=1947,
            end_year=1969,
            description="USAF investigation of UFO reports. Successor to Projects Sign and Grudge."
        )

        print("Inserting document...")
        document_id = insert_document(cursor, program_id, ocr_data)

        conn.commit()
        print(f"\n✓ Successfully loaded data into Snowflake.")
        print(f"  program_id={program_id}, document_id={document_id}")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error: {e}")
        raise

    finally:
        cursor.close()
        conn.close()
        print("  Connection closed.")