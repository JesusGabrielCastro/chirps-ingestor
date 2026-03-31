from abc import ABC, abstractmethod
from .models import CHIRPSFileInfo, ProcessedFile, CountryConfig


class FileListingPort(ABC):
    """
    Contrato para obtener la lista de archivos disponibles en UCSB.
    Implementado por: SeleniumScraper (producción), MockScraper (tests).
    """

    @abstractmethod
    def get_available_files(self, temporality: str, year: int | None = None) -> list[CHIRPSFileInfo]:
        """
        Retorna todos los archivos disponibles para una temporalidad.
        Para daily, year es obligatorio (la URL incluye el año en la ruta).
        Para las demás, year es opcional (todos los años en una sola página).
        """
        ...


class CatalogPort(ABC):
    """
    Contrato para consultar y registrar archivos procesados.
    Implementado por: MongoCatalog (producción), InMemoryCatalog (tests).
    """

    @abstractmethod
    def get_processed_entries(self, country: str, temporality: str) -> dict[str, str]:
        """
        Retorna un dict {filename: status} de archivos ya procesados
        para ese país y temporalidad.
        Ejemplo: {"chirps-v2.0.2024.01.tif.gz": "prelim", ...}
        El orchestrator usa el status para detectar upgrades prelim→real.
        """
        ...

    @abstractmethod
    def register_file(self, processed: ProcessedFile) -> None:
        """Registra un archivo recién procesado (insert o upsert)."""
        ...

    @abstractmethod
    def mark_upgraded_to_real(self, filename: str, country: str, new_minio_path: str) -> None:
        """
        Actualiza el registro cuando un archivo pasa de prelim a real:
        - Cambia status a 'real'
        - Actualiza el minio_path (de prelim/ a real/)
        """
        ...


class GeoClipperPort(ABC):
    """
    Contrato para cortar un GeoTIFF global por el shapefile de un país.
    Implementado por: RasterioClipper (producción), PassthroughClipper (tests).
    """

    @abstractmethod
    def clip(self, url: str, output_path: str, country_config: CountryConfig) -> str:
        """
        Descarga el archivo desde url, lo corta según el shapefile del país
        y guarda el resultado en output_path.
        Retorna el checksum MD5 del archivo resultante.
        """
        ...


class StoragePort(ABC):
    """
    Contrato para almacenar archivos en object storage.
    Implementado por: MinioStorage (producción), LocalFileStorage (tests).
    """

    @abstractmethod
    def upload(self, local_path: str, remote_path: str) -> int:
        """Sube el archivo y retorna el tamaño en bytes."""
        ...

    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        """Verifica si un archivo ya existe en el storage."""
        ...
