import logging
import os
import gzip
import shutil
import hashlib
import tempfile
import time

import numpy as np
import rasterio
from rasterio.mask import mask
import fiona

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from ...domain.models import CountryConfig
from ...domain.ports import GeoClipperPort

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT_SECONDS = 300  # 5 minutos para archivos grandes


class RasterioClipper(GeoClipperPort):
    """
    1. Descarga el archivo .tif.gz usando Chrome headless (mismo DNS que el navegador)
    2. Descomprime el .gz
    3. Corta el GeoTIFF global usando el shapefile del país
    4. Guarda el resultado como GeoTIFF comprimido (LZW)
    """

    def clip(self, url: str, output_path: str, country_config: CountryConfig) -> str:
        """
        Descarga desde url via Selenium, corta por shapefile del país,
        guarda en output_path. Retorna el checksum MD5 del output.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename = url.split("/")[-1]
            gz_path = os.path.join(tmp_dir, filename)
            tif_raw_path = os.path.join(tmp_dir, "raw.tif")

            logger.info(f"  Descargando via Chrome: {url}")
            self._download_with_selenium(url, filename, tmp_dir)

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

    def _download_with_selenium(self, url: str, filename: str, download_dir: str):
        """
        Usa Chrome headless + CDP para descargar el archivo al directorio indicado.
        CDP (Browser.setDownloadBehavior) es necesario en modo headless — las prefs
        de perfil no son suficientes para activar descargas en --headless=new.
        """
        abs_download_dir = os.path.abspath(download_dir)

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-setuid-sandbox")

        driver = webdriver.Chrome(options=options)
        try:
            # Activar descargas via CDP — imprescindible en headless
            driver.execute_cdp_cmd(
                "Browser.setDownloadBehavior",
                {
                    "behavior": "allow",
                    "downloadPath": abs_download_dir,
                    "eventsEnabled": True,
                },
            )

            logger.info(f"  Chrome navegando a: {url}")
            driver.get(url)

            # Esperar a que el archivo aparezca y no tenga extensión .crdownload
            expected = os.path.join(abs_download_dir, filename)
            elapsed = 0
            while elapsed < DOWNLOAD_TIMEOUT_SECONDS:
                crdownload = expected + ".crdownload"
                if os.path.exists(expected) and not os.path.exists(crdownload):
                    size_mb = os.path.getsize(expected) / (1024 * 1024)
                    logger.info(f"  Descarga completada: {filename} ({size_mb:.1f} MB)")
                    return
                time.sleep(2)
                elapsed += 2
                if elapsed % 20 == 0:
                    logger.info(f"  Esperando descarga... {elapsed}s/{DOWNLOAD_TIMEOUT_SECONDS}s")

            raise TimeoutError(
                f"Descarga no completada en {DOWNLOAD_TIMEOUT_SECONDS}s: {url}"
            )
        finally:
            driver.quit()

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
