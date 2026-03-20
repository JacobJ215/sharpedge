FROM python:3.12-slim

WORKDIR /app

# Install system deps (httpx needs these for async SSL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy trading_swarm package (install deps via pyproject.toml)
COPY packages/trading_swarm/pyproject.toml ./
COPY packages/trading_swarm/src/ ./src/
RUN pip install --no-cache-dir -e .

# Copy sharpedge_feeds src and add to Python path
# Install without workspace deps (weather/espn clients degrade gracefully)
COPY packages/data_feeds/src/ /deps/feeds/
ENV PYTHONPATH=/deps/feeds

# Model files volume mount point
RUN mkdir -p /data/models/pm

# Non-root user
RUN useradd -m -u 1000 swarm
USER swarm

ENV PYTHONUNBUFFERED=1 \
    TRADING_MODE=paper \
    MODEL_DIR=/data/models/pm \
    PAPER_BANKROLL=10000 \
    LIVE_BANKROLL=2000

CMD ["python", "-m", "sharpedge_trading.daemon"]
