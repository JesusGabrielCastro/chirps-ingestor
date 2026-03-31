import logging
import os
from minio import Minio
from minio.error import S3Error

from ...domain.ports import StoragePort

logger = logging.getLogger(__name__)


class MinioStorage(StoragePort):

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ):
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Crea el bucket si no existe."""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
            logger.info(f"Bucket '{self._bucket}' creado.")

    def upload(self, local_path: str, remote_path: str) -> int:
        """Sube el archivo al bucket y retorna el tamaño en bytes."""
        file_size = os.path.getsize(local_path)
        self._client.fput_object(
            self._bucket,
            remote_path,
            local_path,
            content_type="image/tiff",
        )
        logger.info(f"  Subido: {remote_path} ({file_size / 1024:.1f} KB)")
        return file_size

    def exists(self, remote_path: str) -> bool:
        """Verifica si un objeto ya existe en el bucket."""
        try:
            self._client.stat_object(self._bucket, remote_path)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise
