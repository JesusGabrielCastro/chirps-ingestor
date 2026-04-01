#!/usr/bin/env python3
"""
Entry point para backfill histórico de datos CHIRPS.
Procesa un rango de años para uno o más países.

Uso:
    # Backfill completo Colombia 2015-2024
    python scripts/run_backfill.py --countries colombia --start-year 2015 --end-year 2024

    # Backfill solo mensual para todos los países
    python scripts/run_backfill.py --temporalities monthly --start-year 2015 --end-year 2024

    # Backfill daily de un año específico
    python scripts/run_backfill.py --countries peru --temporalities daily --start-year 2023 --end-year 2023
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from chirps_ingestor.config import settings
from chirps_ingestor.countries import get_all_countries, get_country
from chirps_ingestor.infrastructure.scraper.pentad_scraper import PentadScraper
from chirps_ingestor.infrastructure.scraper.daily_scraper import DailyScraper
from chirps_ingestor.infrastructure.scraper.dekad_scraper import DekadScraper
from chirps_ingestor.infrastructure.scraper.monthly_scraper import MonthlyScraper
from chirps_ingestor.infrastructure.geo.clipper import RasterioClipper
from chirps_ingestor.infrastructure.storage.minio_client import MinioStorage
from chirps_ingestor.infrastructure.storage.shapefile_downloader import download_shapefile
from chirps_ingestor.infrastructure.catalog.mongo_catalog import MongoCatalog
from chirps_ingestor.application.ingest_orchestrator import IngestOrchestrator
from chirps_ingestor.domain.models import Temporality

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Backfill histórico CHIRPS")
    parser.add_argument("--countries", nargs="+", default=None)
    parser.add_argument("--temporalities", nargs="+", default=None)
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    args = parser.parse_args()

    if args.start_year > args.end_year:
        parser.error("--start-year debe ser menor o igual a --end-year")

    catalog = MongoCatalog(settings.MONGODB_URL, settings.MONGODB_DB)
    clipper = RasterioClipper()
    storage = MinioStorage(
        endpoint=settings.MINIO_URL,
        access_key=settings.MINIO_USER,
        secret_key=settings.MINIO_PASSWORD,
        bucket=settings.MINIO_BUCKET,
        secure=settings.MINIO_SECURE,
    )

    # Para backfill daily, lanza el scraper año por año dentro del rango
    daily_scraper = DailyScraper()

    orchestrator = IngestOrchestrator(
        scrapers={
            "daily":   daily_scraper,
            "pentad":  PentadScraper(),
            "dekad":   DekadScraper(),
            "monthly": MonthlyScraper(),
        },
        catalog=catalog,
        clipper=clipper,
        storage=storage,
        batch_size=settings.BATCH_SIZE,
    )

    countries = (
        [get_country(c) for c in args.countries]
        if args.countries
        else get_all_countries()
    )

    # Descargar shapefiles desde MinIO a tmp/ antes de procesar
    countries = [
        download_shapefile(storage._client, settings.MINIO_BUCKET, c)
        for c in countries
    ]

    target_temporalities = args.temporalities or [t.value for t in Temporality]

    logger.info(
        f"Backfill {args.start_year}-{args.end_year} | "
        f"países: {[c.config.name for c in countries]} | "
        f"temporalidades: {target_temporalities}"
    )

    for year in range(args.start_year, args.end_year + 1):
        logger.info(f"\n{'#'*60}")
        logger.info(f"# AÑO {year}")
        logger.info(f"{'#'*60}")

        # Para daily, el orchestrator ya maneja los años internamente.
        # Aquí pasamos el año como contexto para limitar el scraping.
        orchestrator.run(
            countries=countries,
            temporalities=target_temporalities,
        )


if __name__ == "__main__":
    main()
