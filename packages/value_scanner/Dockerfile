FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip install --no-cache-dir \
    "httpx>=0.27" \
    "redis>=5.0" \
    "pydantic>=2.0" \
    "supabase>=2.0" \
    "numpy>=2.0" \
    "scipy>=1.14" \
    "scikit-learn>=1.5" \
    "matplotlib>=3.8"

# Copy the packages the scanner needs
COPY packages/shared/src/       /app/packages/shared/src/
COPY packages/database/src/     /app/packages/database/src/
COPY packages/models/src/       /app/packages/models/src/
COPY packages/analytics/src/    /app/packages/analytics/src/
COPY packages/odds_client/src/  /app/packages/odds_client/src/

# Copy the runner script
COPY scripts/run_scanners.py    /app/run_scanners.py

ENV PYTHONPATH=/app/packages/shared/src:/app/packages/database/src:/app/packages/models/src:/app/packages/analytics/src:/app/packages/odds_client/src
ENV PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 scanner
USER scanner

CMD ["python", "/app/run_scanners.py"]
