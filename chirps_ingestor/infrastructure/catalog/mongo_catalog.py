import logging
from datetime import datetime

from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection

from ...domain.models import ProcessedFile
from ...domain.ports import CatalogPort

logger = logging.getLogger(__name__)


class MongoCatalog(CatalogPort):

    def __init__(self, mongo_url: str, db_name: str = "chirps_catalog"):
        client = MongoClient(mongo_url)
        db = client[db_name]
        self._col: Collection = db["processed_files"]
        self._ensure_indexes()

    def _ensure_indexes(self):
        self._col.create_index([
            ("country", ASCENDING),
            ("temporality", ASCENDING),
            ("filename", ASCENDING),
        ], unique=True)
        self._col.create_index([("year", ASCENDING), ("month", ASCENDING)])

    def get_processed_entries(self, country: str, temporality: str) -> dict[str, str]:
        """Retorna {filename: status} para que el orchestrator detecte upgrades."""
        docs = self._col.find(
            {"country": country, "temporality": temporality},
            {"filename": 1, "status": 1}
        )
        return {doc["filename"]: doc["status"] for doc in docs}

    def register_file(self, processed: ProcessedFile) -> None:
        doc = {
            "filename": processed.chirps_file.filename,
            "country": processed.country,
            "temporality": processed.chirps_file.temporality.value,
            "year": processed.chirps_file.year,
            "month": processed.chirps_file.month,
            "day": processed.chirps_file.day,
            "period_num": processed.chirps_file.period_num,
            "status": processed.chirps_file.status.value,
            "minio_path": processed.minio_path,
            "file_size_bytes": processed.file_size_bytes,
            "checksum_md5": processed.checksum_md5,
            "processed_at": datetime.utcnow(),
            "source_url": processed.chirps_file.url,
        }
        self._col.update_one(
            {"filename": processed.chirps_file.filename, "country": processed.country},
            {"$set": doc},
            upsert=True,
        )
        logger.info(
            f"  Registrado en catálogo: {processed.chirps_file.filename} [{processed.country}]"
        )

    def mark_upgraded_to_real(self, filename: str, country: str, new_minio_path: str) -> None:
        self._col.update_one(
            {"filename": filename, "country": country},
            {"$set": {
                "status": "real",
                "minio_path": new_minio_path,
                "upgraded_to_real_at": datetime.utcnow(),
            }}
        )
        logger.info(f"  Upgrade registrado: {filename} [{country}] → real")
