FROM python:3.12-slim

# Instalar dependencias del sistema + Google Chrome estable
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    ca-certificates \
    apt-transport-https \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
       | gpg --dearmor -o /etc/apt/trusted.gpg.d/google-chrome.gpg \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Selenium Manager descarga el chromedriver compatible automáticamente
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias Python
# rasterio y fiona traen GDAL bundled en sus wheels — no se necesita sistema GDAL
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Carpeta temporal para descargas y shapefiles
RUN mkdir -p tmp/shapefiles

CMD ["python", "scripts/run_ingest.py"]
