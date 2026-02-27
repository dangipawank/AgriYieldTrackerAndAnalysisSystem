import os

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:root@localhost/agridb")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
