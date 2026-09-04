FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# Render injecte $PORT (souvent 10000). start.sh écoute $PORT, pas 8000.
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-10000}/health" || exit 1'

RUN chmod +x start.sh
CMD ["./start.sh"]
