# setup.py
from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError
from models import metadata  # import all table definitions

# Connect to default 'postgres' database
default_engine = create_engine(
    "postgresql+psycopg2://postgres:root@localhost/postgres",
    isolation_level="AUTOCOMMIT"
)

# Create database if missing
try:
    default_engine.execute("CREATE DATABASE agridb")
    print("Database 'agridb' created successfully!")
except ProgrammingError as e:
    if "already exists" in str(e):
        print("Database 'agridb' already exists. Skipping creation.")
    else:
        raise

# Connect to the newly created agridb
engine = create_engine("postgresql+psycopg2://postgres:root@localhost/agridb")

# Create all tables if missing
metadata.create_all(engine)
print("All tables created (if missing) using SQLAlchemy Core!")
