FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY cli.py .
COPY scripts/ scripts/

RUN pip install --no-cache-dir -e ".[claude,pgvector,eval,dev]"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
EXPOSE 8010

CMD ["sh", "-c", "uvicorn insureflow.api:app --host 0.0.0.0 --port 8000"]
