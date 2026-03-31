#!/usr/bin/env python3
"""
Entry point principal del ingestor CHIRPS.

Uso:
    # Procesar todo (todos los países, todas las temporalidades)
    python scripts/run_ingest.py

    # Solo Colombia, solo mensual
    python scripts/run_ingest.py --countries colombia --temporalities monthly

    # Solo pentadal y dekadal para México y Perú
    python scripts/run_ingest.py --countries mexico peru --temporalities pentad dekad

    # Solo daily del año actual para Colombia
    python scripts/run_ingest.py --countries colombia --temporalities daily
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
from chirps_ingestor.infrastructure.catalog.mongo_catalog import MongoCatalog
from chirps_ingestor.application.ingest_orchestrator import IngestOrchestrator

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Ingestor CHIRPS")
    parser.add_argument(
        "--countries", nargs="+", default=None,
        help="Países a procesar (colombia mexico peru)"
    )
    parser.add_argument(
        "--temporalities", nargs="+", default=None,
        help="Temporalidades (daily pentad dekad monthly)"
    )
    args = parser.parse_args()

    catalog = MongoCatalog(settings.MONGODB_URL, settings.MONGODB_DB)
    clipper = RasterioClipper()
    storage = MinioStorage(
        endpoint=settings.MINIO_URL,
        access_key=settings.MINIO_USER,
        secret_key=settings.MINIO_PASSWORD,
        bucket=settings.MINIO_BUCKET,
        secure=settings.MINIO_SECURE,
    )

    orchestrator = IngestOrchestrator(
        scrapers={
            "daily":   DailyScraper(),
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

    orchestrator.run(
        countries=countries,
        temporalities=args.temporalities,
    )


if __name__ == "__main__":
    main()
