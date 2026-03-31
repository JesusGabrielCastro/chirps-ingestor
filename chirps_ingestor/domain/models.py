from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class Temporality(str, Enum):
    DAILY   = "daily"
    PENTAD  = "pentad"
    DEKAD   = "dekad"
    MONTHLY = "monthly"


class DataStatus(str, Enum):
    REAL   = "real"
    PRELIM = "prelim"


@dataclass(frozen=True)
class CHIRPSFileInfo:
    """Representa un archivo CHIRPS detectado en el servidor de UCSB."""
    filename: str              # nombre original: chirps-v2.0.2024.01.tif.gz
    url: str                   # URL completa de descarga
    temporality: Temporality
    year: int
    month: int
    day: Optional[int]         # solo para daily
    period_num: Optional[int]  # pentad (1-6) o dekad (1-3)
    status: DataStatus
    file_date: date            # fecha a la que corresponde el dato


@dataclass
class ProcessedFile:
    """Representa un archivo ya procesado y almacenado en MinIO."""
    chirps_file: CHIRPSFileInfo
    country: str               # "colombia", "mexico", "peru"
    minio_path: str            # path completo en MinIO
    processed_at: str          # ISO datetime
    file_size_bytes: int
    checksum_md5: str


@dataclass
class IngestBatch:
    """Un lote de máximo 6 archivos para procesar."""
    files: list[CHIRPSFileInfo]
    country: str
    batch_number: int
    total_batches: int


@dataclass
class CountryConfig:
    """Configuración de un país para el proceso de ingesta."""
    name: str                  # "colombia"
    code: str                  # "CO"
    shapefile_path: str        # "shapefiles/colombia/colombia.shp"
    bbox: tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)
    temporalities: list[Temporality]         # qué temporalidades se procesan
    start_year: int            # desde qué año descargar histórico
