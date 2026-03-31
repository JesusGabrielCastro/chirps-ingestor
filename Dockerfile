FROM python:3.12-slim

# Instalar GDAL y dependencias de sistema
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_VERSION=3.6.0
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["python", "scripts/run_ingest.py"]
