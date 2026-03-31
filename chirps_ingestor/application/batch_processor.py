import logging
import os
import tempfile
import time
from datetime import datetime

from ..domain.models import CHIRPSFileInfo, ProcessedFile
from ..domain.ports import GeoClipperPort, StoragePort, CatalogPort
from ..countries.base_country import BaseCountry
from ..config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 6


class BatchProcessor:
    """
    Procesa archivos en lotes de máximo BATCH_SIZE (6).
    Por cada archivo:
      1. Descarga y corta el GeoTIFF por shapefile del país
      2. Sube a MinIO
      3. Registra en catálogo
      4. Limpia archivos temporales
      5. Pausa RATE_LIMIT_SECONDS para no saturar UCSB
    """

    def __init__(
        self,
        clipper: GeoClipperPort,
        storage: StoragePort,
        catalog: CatalogPort,
        batch_size: int = BATCH_SIZE,
    ):
        self._clipper = clipper
        self._storage = storage
        self._catalog = catalog
        self._batch_size = batch_size

    def process_all(self, files: list[CHIRPSFileInfo], country: BaseCountry):
        """
        Divide la lista en lotes y procesa uno por uno.
        Si un archivo falla, registra el error y continúa con el siguiente.
        """
        total = len(files)
        batches = [files[i:i + self._batch_size] for i in range(0, total, self._batch_size)]
        total_batches = len(batches)

        logger.info(
            f"  {total} archivos → {total_batches} lotes de {self._batch_size} "
            f"(país: {country.config.name})"
        )

        for batch_num, batch in enumerate(batches, start=1):
            logger.info(f"\n  Lote {batch_num}/{total_batches}")
            for chirps_file in batch:
                self._process_single(chirps_file, country)

    def process_upgrades(self, files: list[CHIRPSFileInfo], country: BaseCountry):
        """
        Procesa archivos que estaban como prelim y ahora tienen versión real.
        Actualiza el path en MinIO de prelim/ a real/ y actualiza el catálogo.
        """
        logger.info(f"  Procesando {len(files)} upgrades prelim→real")
        batches = [files[i:i + self._batch_size] for i in range(0, len(files), self._batch_size)]
        for batch_num, batch in enumerate(batches, start=1):
            logger.info(f"  Lote upgrade {batch_num}/{len(batches)}")
            for chirps_file in batch:
                self._process_upgrade(chirps_file, country)

    def _process_single(self, chirps_file: CHIRPSFileInfo, country: BaseCountry):
        """Procesa un único archivo: descarga → clip → subida → registro."""
        logger.info(f"    Procesando: {chirps_file.filename}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            clipped_path = os.path.join(tmp_dir, "clipped.tif")

            try:
                # 1. Descargar y cortar por shapefile del país
                checksum = self._clipper.clip(
                    url=chirps_file.url,
                    output_path=clipped_path,
                    country_config=country.config,
                )

                # 2. Construir el path de destino en MinIO
                minio_path = country.get_minio_path(
                    temporality=chirps_file.temporality.value,
                    status=chirps_file.status.value,
                    year=chirps_file.year,
                    month=chirps_file.month,
                    day=chirps_file.day,
                    period_num=chirps_file.period_num,
                )

                # 3. Subir a MinIO
                file_size = self._storage.upload(clipped_path, minio_path)

                # 4. Registrar en catálogo
                processed = ProcessedFile(
                    chirps_file=chirps_file,
                    country=country.config.name,
                    minio_path=minio_path,
                    processed_at=datetime.utcnow().isoformat(),
                    file_size_bytes=file_size,
                    checksum_md5=checksum,
                )
                self._catalog.register_file(processed)

                # 5. Pausa para no saturar UCSB
                time.sleep(settings.RATE_LIMIT_SECONDS)

            except Exception as e:
                logger.error(f"    ERROR procesando {chirps_file.filename}: {e}")

    def _process_upgrade(self, chirps_file: CHIRPSFileInfo, country: BaseCountry):
        """Descarga la versión real, sube al path real/, actualiza catálogo."""
        logger.info(f"    Upgrade prelim→real: {chirps_file.filename}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            clipped_path = os.path.join(tmp_dir, "clipped.tif")
            try:
                checksum = self._clipper.clip(
                    url=chirps_file.url,
                    output_path=clipped_path,
                    country_config=country.config,
                )
                new_minio_path = country.get_minio_path(
                    temporality=chirps_file.temporality.value,
                    status="real",
                    year=chirps_file.year,
                    month=chirps_file.month,
                    day=chirps_file.day,
                    period_num=chirps_file.period_num,
                )
                self._storage.upload(clipped_path, new_minio_path)
                self._catalog.mark_upgraded_to_real(
                    filename=chirps_file.filename,
                    country=country.config.name,
                    new_minio_path=new_minio_path,
                )
                logger.info(f"    Upgrade completado: {new_minio_path}")
                time.sleep(settings.RATE_LIMIT_SECONDS)

            except Exception as e:
                logger.error(f"    ERROR en upgrade {chirps_file.filename}: {e}")
