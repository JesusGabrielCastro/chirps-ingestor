"""
Tests para la lógica de construcción de paths MinIO.
No requiere GDAL ni conexión a internet.
"""
import pytest

from chirps_ingestor.countries.colombia import Colombia
from chirps_ingestor.countries.mexico import Mexico
from chirps_ingestor.countries.peru import Peru


class TestMinioPathConstruction:

    def setup_method(self):
        self.colombia = Colombia()
        self.mexico   = Mexico()
        self.peru     = Peru()

    # ------------------------------------------------------------------
    # Colombia
    # ------------------------------------------------------------------

    def test_daily_real(self):
        path = self.colombia.get_minio_path("daily", "real", 2024, 1, day=15)
        assert path == "precipitacion/daily/colombia/real/2024/01/15.tif"

    def test_daily_prelim(self):
        path = self.colombia.get_minio_path("daily", "prelim", 2025, 3, day=28)
        assert path == "precipitacion/daily/colombia/prelim/2025/03/28.tif"

    def test_monthly_real(self):
        path = self.colombia.get_minio_path("monthly", "real", 2024, 1)
        assert path == "precipitacion/monthly/colombia/real/2024/01/month.tif"

    def test_monthly_prelim(self):
        path = self.colombia.get_minio_path("monthly", "prelim", 2025, 2)
        assert path == "precipitacion/monthly/colombia/prelim/2025/02/month.tif"

    def test_pentad(self):
        path = self.colombia.get_minio_path("pentad", "real", 2024, 6, period_num=4)
        assert path == "precipitacion/pentad/colombia/real/2024/06/4.tif"

    def test_dekad(self):
        path = self.colombia.get_minio_path("dekad", "real", 2024, 1, period_num=3)
        assert path == "precipitacion/dekad/colombia/real/2024/01/3.tif"

    # ------------------------------------------------------------------
    # México y Perú — verificar nombre de país en el path
    # ------------------------------------------------------------------

    def test_mexico_monthly(self):
        path = self.mexico.get_minio_path("monthly", "real", 2024, 5)
        assert "mexico" in path

    def test_peru_monthly(self):
        path = self.peru.get_minio_path("monthly", "real", 2024, 5)
        assert "peru" in path

    # ------------------------------------------------------------------
    # Casos borde
    # ------------------------------------------------------------------

    def test_invalid_temporality_raises(self):
        with pytest.raises(ValueError):
            self.colombia.get_minio_path("weekly", "real", 2024, 1)

    def test_daily_without_day_raises(self):
        with pytest.raises(ValueError):
            self.colombia.get_minio_path("daily", "real", 2024, 1)

    def test_pentad_without_period_num_raises(self):
        with pytest.raises(ValueError):
            self.colombia.get_minio_path("pentad", "real", 2024, 1)
