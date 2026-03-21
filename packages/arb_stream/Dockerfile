FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps directly (no workspace resolver needed in container)
RUN pip install --no-cache-dir \
    "httpx>=0.27" \
    "websockets>=12.0" \
    "pydantic>=2.0" \
    "cryptography>=42.0" \
    "numpy>=2.0" \
    "scipy>=1.14" \
    "scikit-learn>=1.5" \
    "matplotlib>=3.8"

# Copy the packages the arb stream needs
COPY packages/shared/src/       /app/packages/shared/src/
COPY packages/models/src/       /app/packages/models/src/
COPY packages/analytics/src/    /app/packages/analytics/src/
COPY packages/data_feeds/src/   /app/packages/data_feeds/src/

# Copy the runner script
COPY scripts/run_arb_stream.py  /app/run_arb_stream.py

# Keys volume mount point
RUN mkdir -p /app/keys

ENV PYTHONPATH=/app/packages/shared/src:/app/packages/models/src:/app/packages/analytics/src:/app/packages/data_feeds/src
ENV PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 arbstream
USER arbstream

CMD ["python", "/app/run_arb_stream.py"]
