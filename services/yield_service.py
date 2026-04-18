from sqlalchemy import func, select

from models import crop_master, engine, yielddata


def _apply_created_by_filter(statement, created_by=None):
    if created_by is None:
        return statement
    return statement.where(yielddata.c.created_by == created_by)


def get_total_production(created_by=None):
    with engine.connect() as conn:
        statement = _apply_created_by_filter(select(func.sum(yielddata.c.production)), created_by)
        return conn.execute(statement).scalar() or 0


def get_total_cultivated_area(created_by=None):
    with engine.connect() as conn:
        statement = _apply_created_by_filter(select(func.sum(yielddata.c.areaharvested)), created_by)
        return conn.execute(statement).scalar() or 0


def get_average_yield(created_by=None):
    total_production = get_total_production(created_by)
    total_area = get_total_cultivated_area(created_by)
    return (total_production / total_area) if total_area else 0


def get_trend_data(crop_id, created_by=None):
    with engine.connect() as conn:
        statement = (
            select(
                yielddata.c.year.label("year"),
                func.sum(yielddata.c.production).label("production"),
            )
            .where(yielddata.c.cropid == crop_id)
            .group_by(yielddata.c.year)
            .order_by(yielddata.c.year)
        )
        rows = conn.execute(_apply_created_by_filter(statement, created_by)).mappings().all()

    return {
        "years": [row["year"] for row in rows],
        "production": [float(row["production"] or 0) for row in rows],
    }


def get_crop_comparison(created_by=None):
    with engine.connect() as conn:
        statement = (
            select(
                crop_master.c.CropName.label("crop_name"),
                func.sum(yielddata.c.production).label("production"),
            )
            .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
            .group_by(crop_master.c.CropName)
            .order_by(crop_master.c.CropName)
        )
        rows = conn.execute(_apply_created_by_filter(statement, created_by)).mappings().all()

    return {
        "crops": [row["crop_name"] for row in rows],
        "production": [float(row["production"] or 0) for row in rows],
    }


def get_district_analysis(district_id, created_by=None):
    with engine.connect() as conn:
        statement = (
            select(
                crop_master.c.CropName.label("crop_name"),
                func.sum(yielddata.c.production).label("production"),
            )
            .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
            .where(yielddata.c.districtid == district_id)
            .group_by(crop_master.c.CropName)
            .order_by(crop_master.c.CropName)
        )
        rows = conn.execute(_apply_created_by_filter(statement, created_by)).mappings().all()

    return {
        "crops": [row["crop_name"] for row in rows],
        "production": [float(row["production"] or 0) for row in rows],
    }


def get_highest_producing_crop(created_by=None):
    with engine.connect() as conn:
        statement = (
            select(
                crop_master.c.CropName.label("crop_name"),
                func.sum(yielddata.c.production).label("total_production"),
            )
            .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
            .group_by(crop_master.c.CropName)
            .order_by(func.sum(yielddata.c.production).desc())
            .limit(1)
        )
        row = conn.execute(_apply_created_by_filter(statement, created_by)).mappings().first()

    if not row:
        return {"crop_name": "N/A", "total_production": 0}

    return {
        "crop_name": row["crop_name"],
        "total_production": float(row["total_production"] or 0),
    }


def get_latest_year_data_count(created_by=None):
    with engine.connect() as conn:
        latest_year_statement = _apply_created_by_filter(select(func.max(yielddata.c.year)), created_by)
        latest_year = conn.execute(latest_year_statement).scalar()
        if latest_year is None:
            return 0

        count_statement = select(func.count(yielddata.c.yieldid)).where(yielddata.c.year == latest_year)
        count_statement = _apply_created_by_filter(count_statement, created_by)
        return conn.execute(count_statement).scalar() or 0


def get_analysis_summary(created_by=None):
    """Return aggregate analysis blocks for reporting and charts."""
    with engine.connect() as conn:
        by_year_statement = (
            select(
                yielddata.c.year.label("year"),
                func.sum(yielddata.c.production).label("total_production"),
            )
            .group_by(yielddata.c.year)
            .order_by(yielddata.c.year)
        )
        by_year_rows = conn.execute(_apply_created_by_filter(by_year_statement, created_by)).mappings().all()

        by_crop_statement = (
            select(
                crop_master.c.CropName.label("crop"),
                func.sum(yielddata.c.production).label("total_production"),
                func.avg(yielddata.c.yieldamount).label("avg_yield_per_hectare"),
                func.sum(yielddata.c.areaharvested).label("total_area"),
            )
            .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
            .group_by(crop_master.c.CropName)
            .order_by(crop_master.c.CropName)
        )
        by_crop_rows = conn.execute(_apply_created_by_filter(by_crop_statement, created_by)).mappings().all()

        by_district_statement = (
            select(
                yielddata.c.districtid.label("district_id"),
                func.sum(yielddata.c.production).label("total_production"),
                func.avg(yielddata.c.yieldamount).label("avg_yield_per_hectare"),
                func.sum(yielddata.c.areaharvested).label("total_area"),
            )
            .group_by(yielddata.c.districtid)
            .order_by(yielddata.c.districtid)
        )
        by_district_rows = conn.execute(_apply_created_by_filter(by_district_statement, created_by)).mappings().all()

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
