#!/usr/bin/env python3
"""
Prueba de extremo a extremo para el archivo mensual enero 1981 (real) de Colombia.

Pasos:
  1. Descarga el shapefile desde MinIO → tmp/shapefiles/colombia/gadm41_COL_0.shp
  2. Descarga chirps-v2.0.1981.01.tif.gz desde UCSB
  3. Descomprime y corta por el shapefile de Colombia
  4. Sube el resultado a MinIO en precipitacion/monthly/colombia/real/1981/01/month.tif
  5. Registra en MongoDB

No requiere Selenium — la URL del archivo es conocida.

Uso:
    python scripts/test_monthly_1981_01.py
"""

import logging
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from chirps_ingestor.config import settings
from chirps_ingestor.domain.models import CHIRPSFileInfo, Temporality, DataStatus
from chirps_ingestor.countries.colombia import Colombia
from chirps_ingestor.infrastructure.geo.clipper import RasterioClipper
from chirps_ingestor.infrastructure.storage.minio_client import MinioStorage
from chirps_ingestor.infrastructure.catalog.mongo_catalog import MongoCatalog
from chirps_ingestor.application.batch_processor import BatchProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes del archivo a procesar
# ---------------------------------------------------------------------------
CHIRPS_FILENAME = "chirps-v2.0.1981.01.tif.gz"
CHIRPS_URL      = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/chirps-v2.0.1981.01.tif.gz"
SHAPEFILE_MINIO_PATH = "shapefiles/colombia/gadm41_COL_0.shp"

# Archivos auxiliares del shapefile (misma carpeta en MinIO)
SHAPEFILE_SIDECARS = [
    "shapefiles/colombia/gadm41_COL_0.dbf",
    "shapefiles/colombia/gadm41_COL_0.shx",
    "shapefiles/colombia/gadm41_COL_0.prj",
]


def download_shapefile_from_minio(storage: MinioStorage, local_dir: str) -> str:
    """
    Descarga el shapefile y sus sidecars desde MinIO al directorio local.
    Retorna el path local del .shp.
    """
    os.makedirs(local_dir, exist_ok=True)

    shp_local = os.path.join(local_dir, "gadm41_COL_0.shp")

    all_files = [SHAPEFILE_MINIO_PATH] + SHAPEFILE_SIDECARS

    for remote_path in all_files:
        filename = remote_path.split("/")[-1]
        local_path = os.path.join(local_dir, filename)
        if not os.path.exists(local_path):
            logger.info(f"  Descargando shapefile desde MinIO: {remote_path}")
            storage._client.fget_object(settings.MINIO_BUCKET, remote_path, local_path)
        else:
            logger.info(f"  Shapefile ya existe localmente: {local_path}")

    return shp_local


def main():
    logger.info("=" * 60)
    logger.info("TEST: monthly Colombia real — enero 1981")
    logger.info("=" * 60)

    # ---------------------------------------------------------------------------
    # 1. Inicializar dependencias
    # ---------------------------------------------------------------------------
    storage = MinioStorage(
        endpoint=settings.MINIO_URL,
        access_key=settings.MINIO_USER,
        secret_key=settings.MINIO_PASSWORD,
        bucket=settings.MINIO_BUCKET,
        secure=settings.MINIO_SECURE,
    )
    catalog = MongoCatalog(settings.MONGODB_URL, settings.MONGODB_DB)
    clipper = RasterioClipper()
    country = Colombia()

    # ---------------------------------------------------------------------------
    # 2. Descargar shapefile desde MinIO a carpeta local tmp/
    # ---------------------------------------------------------------------------
    local_shp_dir = "tmp/shapefiles/colombia"
    shp_local_path = download_shapefile_from_minio(storage, local_shp_dir)
    logger.info(f"Shapefile listo en: {shp_local_path}")

    # Sobrescribir temporalmente el shapefile_path del config con el path local
    from dataclasses import replace as dc_replace
    local_config = dc_replace(country.config, shapefile_path=shp_local_path)

    class _ColombiaWithLocalShp:
        config = local_config
        def get_minio_path(self, *args, **kwargs):
            return country.get_minio_path(*args, **kwargs)

    country_patched = _ColombiaWithLocalShp()

    # ---------------------------------------------------------------------------
    # 3. Construir el CHIRPSFileInfo para enero 1981 mensual real
    # ---------------------------------------------------------------------------
    chirps_file = CHIRPSFileInfo(
        filename=CHIRPS_FILENAME,
        url=CHIRPS_URL,
        temporality=Temporality.MONTHLY,
        year=1981,
        month=1,
        day=None,
        period_num=None,
        status=DataStatus.REAL,
        file_date=date(1981, 1, 1),
    )

    logger.info(f"Archivo a procesar: {chirps_file.filename}")
    logger.info(f"URL: {chirps_file.url}")

    # ---------------------------------------------------------------------------
    # 4. Verificar si ya existe en MinIO
    # ---------------------------------------------------------------------------
    minio_path = country.get_minio_path("monthly", "real", 1981, 1)
    if storage.exists(minio_path):
        logger.warning(f"El archivo ya existe en MinIO: {minio_path}")
        logger.warning("Eliminarlo manualmente si deseas reprocesar.")
        return

    # ---------------------------------------------------------------------------
    # 5. Procesar: descargar → clip → subir → registrar
    # ---------------------------------------------------------------------------
    processor = BatchProcessor(
        clipper=clipper,
        storage=storage,
        catalog=catalog,
        batch_size=1,
    )
    processor.process_all([chirps_file], country_patched)

    # ---------------------------------------------------------------------------
    # 6. Verificar resultado
    # ---------------------------------------------------------------------------
    if storage.exists(minio_path):
        logger.info("=" * 60)
        logger.info(f"EXITO: archivo disponible en MinIO → {minio_path}")
        logger.info("=" * 60)
    else:
        logger.error("FALLO: el archivo no se encontró en MinIO tras el procesamiento.")
        sys.exit(1)


if __name__ == "__main__":
    main()
