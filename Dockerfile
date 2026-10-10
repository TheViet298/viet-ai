# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Production ----
FROM python:3.11-slim

WORKDIR /app

# Copy installed system-wide packages from builder
COPY --from=builder /usr/local /usr/local

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code
COPY . .

# Setup entrypoint and permissions
RUN chmod +x /app/scripts/docker-entrypoint.sh \
    && mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
