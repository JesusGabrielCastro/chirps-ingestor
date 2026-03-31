FROM python:3.12-slim

# Instalar GDAL del sistema (sin python3-gdal para evitar conflicto con pip)
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

COPY pyproject.toml .

# Instalar GDAL Python bindings usando la versión exacta del sistema
RUN pip install --no-cache-dir GDAL==$(gdal-config --version) \
    && pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["python", "scripts/run_ingest.py"]
