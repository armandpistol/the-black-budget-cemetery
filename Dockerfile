FROM apache/airflow:2.9.1

USER root

# Install poppler-utils for in-memory pdf2image slicing (Tesseract OCR removed in v2.0)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install v2.0 Python dependencies (LiteLLM, Pydantic v2, psycopg2-binary, dbt-postgres)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt