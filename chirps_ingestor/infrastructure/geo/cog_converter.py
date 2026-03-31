import logging
import subprocess
import os

logger = logging.getLogger(__name__)


class CogConverter:
    """
    Convierte un GeoTIFF a Cloud-Optimized GeoTIFF (COG).
    Requiere gdal_translate disponible en el sistema.
    """

    def convert(self, input_path: str, output_path: str) -> None:
        """
        Convierte input_path a COG y guarda en output_path.
        Si gdal_translate no está disponible, copia el archivo tal cual.
        """
        try:
            self._gdal_translate(input_path, output_path)
            logger.info(f"  COG generado: {output_path}")
        except FileNotFoundError:
            logger.warning("gdal_translate no encontrado — copiando sin conversión COG")
            import shutil
            shutil.copy(input_path, output_path)

    def _gdal_translate(self, input_path: str, output_path: str) -> None:
        cmd = [
            "gdal_translate",
            "-of", "COG",
            "-co", "COMPRESS=LZW",
            "-co", "BLOCKSIZE=256",
            "-co", "RESAMPLING=NEAREST",
            input_path,
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"gdal_translate falló: {result.stderr}")
