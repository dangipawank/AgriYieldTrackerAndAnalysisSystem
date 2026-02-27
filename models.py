from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, ForeignKey, DateTime, func
from config import Config

engine = create_engine(Config.DATABASE_URL)

metadata = MetaData()


country = Table(
    "country", metadata,
    Column("countryid", Integer, primary_key=True),
    Column("countryname", String(100), nullable=False),
    schema="mastersetup"
)

province = Table(
    "province", metadata,
    Column("provinceid", Integer, primary_key=True),
    Column("countryid", Integer, ForeignKey("mastersetup.country.countryid"), nullable=False),
    Column("provincename", String(100), nullable=False),
    schema="mastersetup"
)

district = Table(
    "district", metadata,
    Column("districtid", Integer, primary_key=True),
    Column("provinceid", Integer, ForeignKey("mastersetup.province.provinceid"), nullable=False),
    Column("districtname", String(100), nullable=False),
    schema="mastersetup"
)

municipalitytype = Table(
    "municipalitytype", metadata,
    Column("municipalitytypeid", Integer, primary_key=True),
    Column("MunicipalityTypeName", String(500), nullable=False),
    schema="mastersetup"
)

municipality = Table(
    "municipality", metadata,
    Column("municipalityid", Integer, primary_key=True),
    Column("municipalitytypeid", Integer, ForeignKey("mastersetup.municipalitytype.municipalitytypeid"), nullable=False),
    Column("districtid", Integer, ForeignKey("mastersetup.district.districtid"), nullable=False),
    Column("municipalityname", String(500), nullable=False),
    schema="mastersetup"
)


users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(100), nullable=False, unique=True),
    Column("email", String(150), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("role", String(20), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now(), onupdate=func.now()),
)

season_master = Table(
    "season_master", metadata,
    Column("seasonid", Integer, primary_key=True),
    Column("seasonname", String(50), nullable=False, unique=True)
)

crop_type_master = Table(
    "crop_type_master", metadata,
    Column("croptypeid", Integer, primary_key=True),
    Column("croptypename", String(100), nullable=False)
)

crop_master = Table(
    "crop_master", metadata,
    Column("CropId", Integer, primary_key=True),
    Column("CropName", String(100), nullable=False),
    Column("croptypeid", Integer, ForeignKey("crop_type_master.croptypeid"), nullable=False),
    Column("created_by", Integer, ForeignKey("users.id"), nullable=True),
    Column("updated_by", Integer, ForeignKey("users.id"), nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now(), onupdate=func.now()),
)

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
    Column("municipalityid", Integer, ForeignKey("mastersetup.municipality.municipalityid"), nullable=False),
    Column("created_by", Integer, ForeignKey("users.id"), nullable=True),
    Column("updated_by", Integer, ForeignKey("users.id"), nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now(), onupdate=func.now()),
)


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
)

