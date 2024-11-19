FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/* && pip install uv

COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt --system

COPY . .

RUN mkdir -p /app/data && \
    chown -R nobody:nogroup /app/data

USER nobody

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "run.py"]
