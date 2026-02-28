import os


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


class Config:
    DATABASE_URL = _normalize_database_url(
        os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:root@localhost/agridb")
    )

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
