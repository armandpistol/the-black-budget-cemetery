"""
cold_war_pipeline_dag.py
THE BLACK-BUDGET CEMETERY // v2.0 Master Orchestration DAG
Coordinates incremental Multimodal Vision Ingestion (Qwen 2.5-VL -> Supabase pgvector/PostGIS)
followed by dbt Core (dbt-postgres) staging/mart transformations and automated schema tests.
"""

from datetime import datetime, timedelta
import sys

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Ensure /opt/airflow is on sys.path so 'from src.ingestion...' resolves cleanly
if "/opt/airflow" not in sys.path:
    sys.path.insert(0, "/opt/airflow")

from src.ingestion.archive_fetcher import run_multi_sector_discovery
from src.ingestion.reference_rag_loader import ingest_reference_library
from src.ingestion.supabase_loader import run_incremental_batch

default_args = {
    "owner": "armandpistol",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="black_budget_cemetery_v2_pipeline",
    default_args=default_args,
    description="Tri-Modal (Qwen 2.5-VL + Whisper + OpenCV) extraction -> Supabase pgvector/PostGIS -> dbt Core",
    schedule_interval="@weekly",  # Automated weekly radar sweep for newly staged declassifications
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["black-budget-cemetery", "tri-modal", "supabase", "qwen-vl", "whisper", "dbt-postgres"],
) as dag:

    # Task 0: Sweep NARA & Multi-Sector FOIA feeds for newly released files
    discover_task = PythonOperator(
        task_id="discover_multi_sector_archives",
        python_callable=run_multi_sector_discovery,
    )

    # Task 1A: Incremental Manifest Check + Tri-Modal Extraction + Supabase Upsert
    ingest_task = PythonOperator(
        task_id="incremental_supabase_ingest",
        python_callable=run_incremental_batch,
    )

    # Task 1B: Chunk & Embed any new Private Library E-Books/Papers into raw.reference_knowledge_chunks
    rag_library_task = PythonOperator(
        task_id="sync_private_rag_library",
        python_callable=ingest_reference_library,
    )

    # Task 2: Execute dbt-postgres Staging Views & Mart Table transformations
    dbt_run_task = BashOperator(
        task_id="dbt_run_transformations",
        bash_command="cd /opt/airflow/cold_war_dbt && dbt run",
    )

    # Task 3: Enforce automated dbt data quality tests
    dbt_test_task = BashOperator(
        task_id="dbt_test_quality_gate",
        bash_command="cd /opt/airflow/cold_war_dbt && dbt test",
    )

    # Full pipeline lineage
    discover_task >> [ingest_task, rag_library_task] >> dbt_run_task >> dbt_test_task