import logging
import os
import gzip
import shutil
import hashlib
import tempfile

import numpy as np
import requests
import rasterio
from rasterio.mask import mask
import fiona

from ...domain.models import CountryConfig
from ...domain.ports import GeoClipperPort

logger = logging.getLogger(__name__)

CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks para descarga


class RasterioClipper(GeoClipperPort):
    """
    1. Descarga el archivo .tif.gz desde la URL
    2. Descomprime el .gz
    3. Corta el GeoTIFF global usando el shapefile del país
    4. Guarda el resultado como GeoTIFF comprimido (LZW)
    """

    def clip(self, url: str, output_path: str, country_config: CountryConfig) -> str:
        """
        Descarga desde url, corta por shapefile del país,
        guarda en output_path. Retorna el checksum MD5 del output.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            gz_path = os.path.join(tmp_dir, "raw.tif.gz")
            tif_raw_path = os.path.join(tmp_dir, "raw.tif")

            logger.info(f"  Descargando: {url}")
            self._download(url, gz_path)

            # Descomprimir si es .gz
            if url.endswith(".gz"):
                logger.info("  Descomprimiendo...")
                with gzip.open(gz_path, "rb") as f_in:
                    with open(tif_raw_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy(gz_path, tif_raw_path)

            # Leer shapefile y obtener geometrías del país
            logger.info(f"  Cortando por shapefile: {country_config.shapefile_path}")
            shapes = self._load_shapes(country_config.shapefile_path)

            # Cortar el raster
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            self._clip_raster(tif_raw_path, output_path, shapes)

        if not self._validate_nodata(output_path):
            raise ValueError(
                f"El archivo recortado tiene más del 95% de valores NoData: {output_path}. "
                "Verificar que el shapefile coincide con la cobertura del raster."
            )

        checksum = self._md5(output_path)
        logger.info(f"  Guardado en: {output_path} (md5: {checksum[:8]}...)")
        return checksum

    def _download(self, url: str, dest_path: str):
        """Descarga con streaming para archivos grandes."""
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)

    def _load_shapes(self, shapefile_path: str) -> list:
        """Carga las geometrías del shapefile."""
        with fiona.open(shapefile_path, "r") as shp:
            return [feature["geometry"] for feature in shp]

    def _clip_raster(self, input_path: str, output_path: str, shapes: list):
        """Corta el raster usando las geometrías y guarda con compresión LZW."""
        with rasterio.open(input_path) as src:
            out_image, out_transform = mask(src, shapes, crop=True)
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "compress": "lzw",
                "tiled": True,
                "blockxsize": 256,
                "blockysize": 256,
            })
            with rasterio.open(output_path, "w", **out_meta) as dest:
                dest.write(out_image)

    def _validate_nodata(self, path: str, max_nodata_pct: float = 0.95) -> bool:
        """Retorna False si el archivo tiene más del max_nodata_pct de valores NoData."""
        with rasterio.open(path) as src:
            data = src.read(1)
            nodata = src.nodata
            if nodata is not None:
                nodata_pct = np.sum(data == nodata) / data.size
                if nodata_pct > max_nodata_pct:
                    return False
        return True

    def _md5(self, path: str) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
