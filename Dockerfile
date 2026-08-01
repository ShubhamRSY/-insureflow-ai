FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tesseract-ocr \
    poppler-utils \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY evaluations/ evaluations/
COPY examples/ examples/
COPY simulated_documents/ simulated_documents/
COPY cli.py .
COPY scripts/ scripts/
COPY ml_data/ ml_data/

ARG PIP_EXTRAS=claude,pgvector,ocr,ml,pdf
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e ".[${PIP_EXTRAS}]"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN python -c "from insureflow.ml.training import train_all_models; train_all_models(allow_synthetic=False)"

EXPOSE 8000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["python3", "-m", "uvicorn", "insureflow.api:app", "--host", "0.0.0.0", "--port", "8000"]
