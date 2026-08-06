FROM apache/airflow:2.9.1

USER root

# Install system dependencies for OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt