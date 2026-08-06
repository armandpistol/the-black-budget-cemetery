"""
cold_war_pipeline_dag.py
Orchestrates the full ingestion pipeline for declassified government documents.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Make src/ importable inside Airflow containers
sys.path.insert(0, '/opt/airflow')

from src.parsing.ocr_extractor import extract_text_from_pdf
from src.ingestion.snowflake_loader import get_connection, insert_program, insert_document

import json
import pathlib

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def run_ocr_extraction(**context):
    """Task 1: Extract text from PDF via OCR and save to JSON."""
    pdf_path = '/opt/airflow/data/raw/blue_book_incident_17_kenneth_arnold.pdf'
    output_dir = pathlib.Path('/opt/airflow/data/processed')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'blue_book_incident_17_kenneth_arnold.json'

    print(f"Running OCR on {pdf_path}...")
    result = extract_text_from_pdf(pdf_path)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✓ OCR complete. {result['page_count']} pages extracted.")
    # Pass the output path to the next task via XCom
    context['ti'].xcom_push(key='json_path', value=str(output_path))


def run_snowflake_load(**context):
    """Task 2: Load OCR JSON into Snowflake."""
    json_path = context['ti'].xcom_pull(
        task_ids='ocr_extraction', key='json_path'
    )

    print(f"Loading {json_path} into Snowflake...")
    with open(json_path, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        program_id = insert_program(
            cursor,
            program_name='Blue Book',
            lead_agency='USAF',
            start_year=1947,
            end_year=1969,
            description='USAF investigation of UFO reports.'
        )
        document_id = insert_document(cursor, program_id, ocr_data)
        conn.commit()
        print(f"✓ Loaded: program_id={program_id}, document_id={document_id}")

    except Exception as e:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


with DAG(
    dag_id='cold_war_anomalies_pipeline',
    default_args=default_args,
    description='Ingests declassified government documents into Snowflake',
    schedule_interval=None,  # Manual trigger only for now
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['cold-war', 'snowflake', 'ocr'],
) as dag:

    ocr_task = PythonOperator(
        task_id='ocr_extraction',
        python_callable=run_ocr_extraction,
    )

    load_task = PythonOperator(
        task_id='snowflake_load',
        python_callable=run_snowflake_load,
    )

    # Define task order: OCR must complete before loading
    ocr_task >> load_task