"""
Tests para los scrapers usando un MockScraper con datos HTML fijos.
No requiere Selenium ni conexión a UCSB.
"""
import re
from datetime import date

import pytest

from chirps_ingestor.domain.models import CHIRPSFileInfo, Temporality, DataStatus
from chirps_ingestor.domain.ports import FileListingPort
from chirps_ingestor.infrastructure.scraper.monthly_scraper import MONTHLY_PATTERN
from chirps_ingestor.infrastructure.scraper.pentad_scraper import PENTAD_PATTERN
from chirps_ingestor.infrastructure.scraper.dekad_scraper import DEKAD_PATTERN
from chirps_ingestor.infrastructure.scraper.daily_scraper import DAILY_PATTERN


# ---------------------------------------------------------------------------
# MockScraper para tests de integración del orquestador
# ---------------------------------------------------------------------------

class MockScraper(FileListingPort):
    """Devuelve una lista fija de archivos sin tocar la red."""

    def __init__(self, files: list[CHIRPSFileInfo]):
        self._files = files

    def get_available_files(
        self, temporality: str, year: int | None = None
    ) -> list[CHIRPSFileInfo]:
        return [f for f in self._files if f.temporality.value == temporality]


# ---------------------------------------------------------------------------
# Tests de patrones regex
# ---------------------------------------------------------------------------

class TestMonthlyPattern:

    def test_matches_gz(self):
        m = MONTHLY_PATTERN.match("chirps-v2.0.2024.01.tif.gz")
        assert m is not None
        assert m.group(1) == "2024"
        assert m.group(2) == "01"

    def test_matches_without_gz(self):
        m = MONTHLY_PATTERN.match("chirps-v2.0.1981.12.tif")
        assert m is not None
        assert m.group(1) == "1981"
        assert m.group(2) == "12"

    def test_no_match_daily(self):
        assert MONTHLY_PATTERN.match("chirps-v2.0.2024.01.15.tif.gz") is None

    def test_no_match_pentad(self):
        assert MONTHLY_PATTERN.match("chirps-v2.0.2024.01.3.tif.gz") is None


class TestPentadPattern:

    def test_matches_all_pentads(self):
        for p in range(1, 7):
            filename = f"chirps-v2.0.2025.06.{p}.tif.gz"
            m = PENTAD_PATTERN.match(filename)
            assert m is not None, f"No coincide: {filename}"
            assert int(m.group(3)) == p

    def test_no_match_pentad_7(self):
        assert PENTAD_PATTERN.match("chirps-v2.0.2025.06.7.tif.gz") is None

    def test_no_match_monthly(self):
        assert PENTAD_PATTERN.match("chirps-v2.0.2025.06.tif.gz") is None


class TestDekadPattern:

    def test_matches_all_dekads(self):
        for d in range(1, 4):
            filename = f"chirps-v2.0.1981.01.{d}.tif.gz"
            m = DEKAD_PATTERN.match(filename)
            assert m is not None, f"No coincide: {filename}"
            assert int(m.group(3)) == d

    def test_no_match_dekad_4(self):
        assert DEKAD_PATTERN.match("chirps-v2.0.1981.01.4.tif.gz") is None


class TestDailyPattern:

    def test_matches_daily(self):
        m = DAILY_PATTERN.match("chirps-v2.0.2025.01.15.tif.gz")
        assert m is not None
        assert m.group(1) == "2025"
        assert m.group(2) == "01"
        assert m.group(3) == "15"

    def test_matches_without_gz(self):
        m = DAILY_PATTERN.match("chirps-v2.0.2025.01.01.tif")
        assert m is not None

    def test_no_match_monthly(self):
        assert DAILY_PATTERN.match("chirps-v2.0.2025.01.tif.gz") is None
