import os

class Config:
    # Database connection string: postgresql+psycopg2://username:password@host/databasename
    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://postgres:root@localhost/agridb"

    # Disable tracking modifications to save memory (not needed if using raw SQL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Secret key for Flask session, CSRF protection, etc.
    SECRET_KEY = os.urandom(24)
