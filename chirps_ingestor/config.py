import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "chirps_catalog")

    MINIO_URL: str = os.getenv("MINIO_URL", "localhost:9000")
    MINIO_USER: str = os.getenv("MINIO_USER", "chirps_admin")
    MINIO_PASSWORD: str = os.getenv("MINIO_PASSWORD", "chirps_local_pass")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "chirps")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "6"))
    MAX_DOWNLOAD_RETRIES: int = int(os.getenv("MAX_DOWNLOAD_RETRIES", "3"))
    DOWNLOAD_TIMEOUT_SECONDS: int = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "180"))
    RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "2"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
