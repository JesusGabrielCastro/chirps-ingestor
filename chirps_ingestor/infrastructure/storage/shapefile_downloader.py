import logging
import os
from dataclasses import replace as dc_replace

from minio import Minio

from ...countries.base_country import BaseCountry

logger = logging.getLogger(__name__)

# Extensiones de archivos auxiliares del shapefile
SHAPEFILE_EXTENSIONS = [".shp", ".dbf", ".shx", ".prj", ".cpg"]


def download_shapefile(
    minio_client: Minio,
    bucket: str,
    country: BaseCountry,
    local_base_dir: str = "tmp/shapefiles",
) -> BaseCountry:
    """
    Descarga el shapefile del país desde MinIO al directorio local.
    Retorna una copia del país con shapefile_path apuntando al archivo local.

    El shapefile en MinIO se busca en:
        shapefiles/{country_name}/{filename}
    donde {filename} se deduce del shapefile_path configurado en el país.

    Ejemplo:
        config.shapefile_path = "shapefiles/colombia/gadm41_COL_0.shp"
        → descarga de MinIO: shapefiles/colombia/gadm41_COL_0.*
        → guarda en: tmp/shapefiles/colombia/gadm41_COL_0.*
        → retorna config con shapefile_path = "tmp/shapefiles/colombia/gadm41_COL_0.shp"
    """
    config = country.config
    original_path = config.shapefile_path          # ej: shapefiles/colombia/gadm41_COL_0.shp
    shp_filename = os.path.basename(original_path) # ej: gadm41_COL_0.shp
    shp_stem = os.path.splitext(shp_filename)[0]   # ej: gadm41_COL_0
    minio_folder = os.path.dirname(original_path).replace("\\", "/")  # ej: shapefiles/colombia
    local_dir = os.path.join(local_base_dir, config.name)             # ej: tmp/shapefiles/colombia

    os.makedirs(local_dir, exist_ok=True)

    for ext in SHAPEFILE_EXTENSIONS:
        remote_path = f"{minio_folder}/{shp_stem}{ext}"
        local_path  = os.path.join(local_dir, f"{shp_stem}{ext}")

        if os.path.exists(local_path):
            logger.debug(f"  Shapefile ya existe localmente: {local_path}")
            continue

        try:
            minio_client.fget_object(bucket, remote_path, local_path)
            logger.info(f"  Shapefile descargado: {remote_path} → {local_path}")
        except Exception as e:
            if ext == ".shp":
                raise RuntimeError(
                    f"No se pudo descargar el shapefile principal de MinIO: {remote_path} — {e}"
                )
            # Los sidecars opcionales (.cpg) pueden no existir
            logger.debug(f"  Sidecar no encontrado (ignorado): {remote_path}")

    local_shp_path = os.path.join(local_dir, shp_filename)

    # Crear una clase anónima que hereda el comportamiento pero usa el path local
    class _PatchedCountry:
        config = dc_replace(country.config, shapefile_path=local_shp_path)

        def get_minio_path(self, *args, **kwargs):
            return country.get_minio_path(*args, **kwargs)

    return _PatchedCountry()
