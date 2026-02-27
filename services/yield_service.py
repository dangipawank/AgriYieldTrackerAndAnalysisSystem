from sqlalchemy import select, func
from models import engine, yielddata, crop_master




def get_total_production():
    with engine.connect() as conn:
        return conn.execute(select(func.sum(yielddata.c.production))).scalar() or 0


def get_total_cultivated_area():
    with engine.connect() as conn:
        return conn.execute(select(func.sum(yielddata.c.areaharvested))).scalar() or 0


def get_average_yield():
    total_production = get_total_production()
    total_area = get_total_cultivated_area()
    return (total_production / total_area) if total_area else 0


def get_trend_data(crop_id):
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                yielddata.c.year.label("year"),
                func.sum(yielddata.c.production).label("production")
            )
            .where(yielddata.c.cropid == crop_id)
            .group_by(yielddata.c.year)
            .order_by(yielddata.c.year)
        ).mappings().all()

    return {
        "years": [row["year"] for row in rows],
        "production": [float(row["production"] or 0) for row in rows]
    }


def get_crop_comparison():
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                crop_master.c.CropName.label("crop_name"),
                func.sum(yielddata.c.production).label("production")
            )
            .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
            .group_by(crop_master.c.CropName)
            .order_by(crop_master.c.CropName)
        ).mappings().all()

    return {
        "crops": [row["crop_name"] for row in rows],
        "production": [float(row["production"] or 0) for row in rows]
    }


def get_district_analysis(district_id):
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                crop_master.c.CropName.label("crop_name"),
                func.sum(yielddata.c.production).label("production")
            )
            .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
            .where(yielddata.c.districtid == district_id)
            .group_by(crop_master.c.CropName)
            .order_by(crop_master.c.CropName)
        ).mappings().all()

    return {
        "crops": [row["crop_name"] for row in rows],
        "production": [float(row["production"] or 0) for row in rows]
    }


def get_highest_producing_crop():
    with engine.connect() as conn:
        row = conn.execute(
            select(
                crop_master.c.CropName.label("crop_name"),
                func.sum(yielddata.c.production).label("total_production")
            )
            .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
            .group_by(crop_master.c.CropName)
            .order_by(func.sum(yielddata.c.production).desc())
            .limit(1)
        ).mappings().first()

    if not row:
        return {"crop_name": "N/A", "total_production": 0}

    return {
        "crop_name": row["crop_name"],
        "total_production": float(row["total_production"] or 0)
    }


def get_latest_year_data_count():
    with engine.connect() as conn:
        latest_year = conn.execute(select(func.max(yielddata.c.year))).scalar()
        if latest_year is None:
            return 0

        return conn.execute(
            select(func.count(yielddata.c.yieldid)).where(yielddata.c.year == latest_year)
        ).scalar() or 0


def get_analysis_summary():
    """Return aggregate analysis blocks for TU project reporting and charts."""
    with engine.connect() as conn:
        by_year_rows = conn.execute(
            select(
                yielddata.c.year.label("year"),
                func.sum(yielddata.c.production).label("total_production")
            )
            .group_by(yielddata.c.year)
            .order_by(yielddata.c.year)
        ).mappings().all()

        by_crop_rows = conn.execute(
            select(
                crop_master.c.CropName.label("crop"),
                func.sum(yielddata.c.production).label("total_production"),
                func.avg(yielddata.c.yieldamount).label("avg_yield_per_hectare"),
                func.sum(yielddata.c.areaharvested).label("total_area")
            )
            .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
            .group_by(crop_master.c.CropName)
            .order_by(crop_master.c.CropName)
        ).mappings().all()

        by_district_rows = conn.execute(
            select(
                yielddata.c.districtid.label("district_id"),
                func.sum(yielddata.c.production).label("total_production"),
                func.avg(yielddata.c.yieldamount).label("avg_yield_per_hectare"),
                func.sum(yielddata.c.areaharvested).label("total_area")
            )
            .group_by(yielddata.c.districtid)
            .order_by(yielddata.c.districtid)
        ).mappings().all()

    return {
        "by_year": [
            {"year": row["year"], "total_production": float(row["total_production"] or 0)}
            for row in by_year_rows
        ],
        "by_crop": [
            {
                "crop": row["crop"],
                "total_production": float(row["total_production"] or 0),
                "avg_yield_per_hectare": float(row["avg_yield_per_hectare"] or 0),
                "total_area": float(row["total_area"] or 0),
            }
            for row in by_crop_rows
        ],
        "by_district": [
            {
                "district_id": row["district_id"],
                "total_production": float(row["total_production"] or 0),
                "avg_yield_per_hectare": float(row["avg_yield_per_hectare"] or 0),
                "total_area": float(row["total_area"] or 0),
            }
            for row in by_district_rows
        ],
    }
