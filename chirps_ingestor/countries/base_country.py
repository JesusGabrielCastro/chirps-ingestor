from abc import ABC, abstractmethod
from ..domain.models import CountryConfig, Temporality


class BaseCountry(ABC):
    """Clase base con defaults. Cada país sobreescribe lo que necesite."""

    @property
    @abstractmethod
    def config(self) -> CountryConfig:
        ...

    def get_minio_path(
        self,
        temporality: str,
        status: str,
        year: int,
        month: int,
        day: int | None = None,
        period_num: int | None = None,
    ) -> str:
        """
        Construye el path en MinIO según las reglas definidas.
        precipitacion/{temporality}/{country_name}/{status}/{year}/{month}/{filename}.tif
        """
        base = f"precipitacion/{temporality}/{self.config.name}/{status}/{year}/{month:02d}"

        if temporality == "daily" and day is not None:
            return f"{base}/{day:02d}.tif"

        if temporality in ("pentad", "dekad") and period_num is not None:
            return f"{base}/{period_num}.tif"

        if temporality == "monthly":
            return f"{base}/month.tif"

        raise ValueError(f"No se pudo construir el path para temporality={temporality}")
