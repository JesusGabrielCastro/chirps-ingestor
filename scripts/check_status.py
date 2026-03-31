#!/usr/bin/env python3
"""
Muestra un resumen del estado de la ingesta:
cuántos archivos hay por país, temporalidad, status y año.

Uso:
    python scripts/check_status.py
    python scripts/check_status.py --country colombia
    python scripts/check_status.py --country colombia --temporality monthly
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from chirps_ingestor.config import settings
from chirps_ingestor.infrastructure.catalog.mongo_catalog import MongoCatalog
from chirps_ingestor.countries import get_all_countries, get_country


def main():
    parser = argparse.ArgumentParser(description="Estado de la ingesta CHIRPS")
    parser.add_argument("--country", default=None, help="Filtrar por país")
    parser.add_argument("--temporality", default=None, help="Filtrar por temporalidad")
    args = parser.parse_args()

    from pymongo import MongoClient
    client = MongoClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]
    col = db["processed_files"]

    query = {}
    if args.country:
        query["country"] = args.country
    if args.temporality:
        query["temporality"] = args.temporality

    docs = list(col.find(query, {"country": 1, "temporality": 1, "year": 1, "status": 1}))

    if not docs:
        print("No hay archivos registrados en el catálogo.")
        return

    # Agrupar por país / temporalidad / año / status
    counts: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
    for doc in docs:
        country = doc.get("country", "?")
        temp    = doc.get("temporality", "?")
        year    = doc.get("year", 0)
        status  = doc.get("status", "?")
        counts[country][temp][year][status] += 1

    print(f"\n{'País':<12} {'Temporalidad':<12} {'Año':<6} {'Real':>6} {'Prelim':>8} {'Total':>7}")
    print("-" * 55)

    for country in sorted(counts):
        for temp in sorted(counts[country]):
            for year in sorted(counts[country][temp]):
                real   = counts[country][temp][year].get("real", 0)
                prelim = counts[country][temp][year].get("prelim", 0)
                total  = real + prelim
                print(f"{country:<12} {temp:<12} {year:<6} {real:>6} {prelim:>8} {total:>7}")

    print("-" * 55)
    print(f"Total documentos: {len(docs)}")


if __name__ == "__main__":
    main()
