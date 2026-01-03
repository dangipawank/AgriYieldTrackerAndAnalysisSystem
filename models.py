from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, ForeignKey

# Connect to your database
engine = create_engine("postgresql+psycopg2://postgres:root@localhost/agridb")

# Metadata object keeps track of all tables
metadata = MetaData()

# ============================
# Mastersetup Schema Tables
# ============================

# Country Table
country = Table(
    "country", metadata,
    Column("countryid", Integer, primary_key=True),
    Column("countryname", String(100), nullable=False),
    schema="mastersetup"
)

# Province Table
province = Table(
    "province", metadata,
    Column("provinceid", Integer, primary_key=True),
    Column("countryid", Integer, ForeignKey("mastersetup.country.countryid"), nullable=False),
    Column("provincename", String(100), nullable=False),
    schema="mastersetup"
)

# District Table
district = Table(
    "district", metadata,
    Column("districtid", Integer, primary_key=True),
    Column("provinceid", Integer, ForeignKey("mastersetup.province.provinceid"), nullable=False),
    Column("districtname", String(100), nullable=False),
    schema="mastersetup"
)

# MunicipalityType Table
municipalitytype = Table(
    "municipalitytype", metadata,
    Column("municipalitytypeid", Integer, primary_key=True),
    Column("MunicipalityTypeName", String(500), nullable=False),
    schema="mastersetup"
)

# Municipality Table
municipality = Table(
    "municipality", metadata,
    Column("municipalityid", Integer, primary_key=True),
    Column("municipalitytypeid", Integer, ForeignKey("mastersetup.municipalitytype.municipalitytypeid"), nullable=False),
    Column("districtid", Integer, ForeignKey("mastersetup.district.districtid"), nullable=False),
    Column("municipalityname", String(500), nullable=False),
    schema="mastersetup"
)

# ============================
# Crop & Yield Tables
# ============================

# Season Master Table
season_master = Table(
    "season_master", metadata,
    Column("seasonid", Integer, primary_key=True),
    Column("seasonname", String(50), nullable=False, unique=True)
)

# Crop Type Master Table
crop_type_master = Table(
    "crop_type_master", metadata,
    Column("croptypeid", Integer, primary_key=True),
    Column("croptypename", String(100), nullable=False)
)

# Crop Master Table
crop_master = Table(
    "crop_master", metadata,
    Column("CropId", Integer, primary_key=True),
    Column("CropName", String(100), nullable=False),
    Column("croptypeid", Integer, ForeignKey("crop_type_master.croptypeid"), nullable=False)
)

# Yield Data Table
yielddata = Table(
    "yielddata", metadata,
    Column("yieldid", Integer, primary_key=True),
    Column("cropid", Integer, ForeignKey("crop_master.CropId"), nullable=False),
    Column("seasonid", Integer, ForeignKey("season_master.seasonid"), nullable=True),
    Column("year", Integer, nullable=False),
    Column("yieldamount", Float, nullable=False),
    Column("areaharvested", Float, nullable=False),
    Column("production", Float, nullable=False),
    Column("districtid", Integer, ForeignKey("mastersetup.district.districtid"), nullable=False),
    Column("municipalityid", Integer, ForeignKey("mastersetup.municipality.municipalityid"), nullable=False)
)

# ============================
# View: Yield Full Report
# ============================

# Note: Views in PostgreSQL cannot be created by SQLAlchemy Core directly
# You can define a Table object for querying purposes only
yield_full_report = Table(
    "vw_yield_full_report", metadata,
    Column("yieldid", Integer, primary_key=True),
    Column("cropid", Integer),
    Column("CropName", String(100)),
    Column("croptypename", String(100)),
    Column("year", Integer),
    Column("yieldamount", Float),
    Column("areaharvested", Float),
    Column("production", Float),
    Column("districtid", Integer),
    Column("districtname", String(100)),
    Column("provinceid", Integer),
    Column("provincename", String(100)),
    Column("municipalityid", Integer),
    Column("municipalityname", String(500)),
    Column("MunicipalityTypeName", String(500)),
    Column("seasonid", Integer),
    Column("seasonname", String(50))
    # No schema needed, views usually in default schema
)

# ============================
# Create All Tables
# ============================

metadata.create_all(engine)
print("All tables created programmatically using SQLAlchemy Core!")
