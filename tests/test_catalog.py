"""
Tests para la lógica del catálogo usando InMemoryCatalog.
No requiere MongoDB.
"""
from datetime import date

import pytest

from chirps_ingestor.domain.models import (
    CHIRPSFileInfo,
    ProcessedFile,
    Temporality,
    DataStatus,
)
from chirps_ingestor.domain.ports import CatalogPort


# ---------------------------------------------------------------------------
# InMemoryCatalog — implementación en memoria para tests
# ---------------------------------------------------------------------------

class InMemoryCatalog(CatalogPort):

    def __init__(self):
        # {(filename, country): {"status": ..., "minio_path": ...}}
        self._store: dict[tuple[str, str], dict] = {}

    def get_processed_entries(self, country: str, temporality: str) -> dict[str, str]:
        return {
            k[0]: v["status"]
            for k, v in self._store.items()
            if k[1] == country and v.get("temporality") == temporality
        }

    def register_file(self, processed: ProcessedFile) -> None:
        key = (processed.chirps_file.filename, processed.country)
        self._store[key] = {
            "status": processed.chirps_file.status.value,
            "minio_path": processed.minio_path,
            "temporality": processed.chirps_file.temporality.value,
        }

    def mark_upgraded_to_real(self, filename: str, country: str, new_minio_path: str) -> None:
        key = (filename, country)
        if key in self._store:
            self._store[key]["status"] = "real"
            self._store[key]["minio_path"] = new_minio_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_chirps_file(
    filename: str,
    status: DataStatus,
    temporality: Temporality = Temporality.MONTHLY,
    year: int = 2024,
    month: int = 1,
) -> CHIRPSFileInfo:
    return CHIRPSFileInfo(
        filename=filename,
        url=f"https://example.com/{filename}",
        temporality=temporality,
        year=year,
        month=month,
        day=None,
        period_num=None,
        status=status,
        file_date=date(year, month, 1),
    )


def make_processed(chirps_file: CHIRPSFileInfo, country: str = "colombia") -> ProcessedFile:
    return ProcessedFile(
        chirps_file=chirps_file,
        country=country,
        minio_path=f"precipitacion/monthly/{country}/{chirps_file.status.value}/{chirps_file.year}/{chirps_file.month:02d}/month.tif",
        processed_at="2024-01-01T00:00:00",
        file_size_bytes=1024,
        checksum_md5="abc123",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInMemoryCatalog:

    def test_register_and_retrieve(self):
        catalog = InMemoryCatalog()
        chirps = make_chirps_file("chirps-v2.0.2024.01.tif.gz", DataStatus.REAL)
        processed = make_processed(chirps)
        catalog.register_file(processed)

        entries = catalog.get_processed_entries("colombia", "monthly")
        assert "chirps-v2.0.2024.01.tif.gz" in entries
        assert entries["chirps-v2.0.2024.01.tif.gz"] == "real"

    def test_register_prelim(self):
        catalog = InMemoryCatalog()
        chirps = make_chirps_file("chirps-v2.0.2025.02.tif.gz", DataStatus.PRELIM)
        processed = make_processed(chirps)
        catalog.register_file(processed)

        entries = catalog.get_processed_entries("colombia", "monthly")
        assert entries["chirps-v2.0.2025.02.tif.gz"] == "prelim"

    def test_upgrade_prelim_to_real(self):
        catalog = InMemoryCatalog()
        chirps = make_chirps_file("chirps-v2.0.2025.02.tif.gz", DataStatus.PRELIM)
        catalog.register_file(make_processed(chirps))

        new_path = "precipitacion/monthly/colombia/real/2025/02/month.tif"
        catalog.mark_upgraded_to_real("chirps-v2.0.2025.02.tif.gz", "colombia", new_path)

        entries = catalog.get_processed_entries("colombia", "monthly")
        assert entries["chirps-v2.0.2025.02.tif.gz"] == "real"

    def test_no_cross_country_contamination(self):
        catalog = InMemoryCatalog()
        chirps_co = make_chirps_file("chirps-v2.0.2024.01.tif.gz", DataStatus.REAL)
        chirps_mx = make_chirps_file("chirps-v2.0.2024.01.tif.gz", DataStatus.REAL)

        catalog.register_file(make_processed(chirps_co, country="colombia"))
        catalog.register_file(make_processed(chirps_mx, country="mexico"))

        entries_co = catalog.get_processed_entries("colombia", "monthly")
        entries_mx = catalog.get_processed_entries("mexico", "monthly")
        assert "chirps-v2.0.2024.01.tif.gz" in entries_co
        assert "chirps-v2.0.2024.01.tif.gz" in entries_mx

    def test_empty_catalog(self):
        catalog = InMemoryCatalog()
        entries = catalog.get_processed_entries("colombia", "monthly")
        assert entries == {}
