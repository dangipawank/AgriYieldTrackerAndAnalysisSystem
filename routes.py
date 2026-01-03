from flask import Blueprint, flash, render_template, request, redirect, url_for
from sqlalchemy import select, func, insert, update, delete
from models import (
    engine,
    crop_master,
    district,
    municipality,
    season_master,
    crop_type_master,
    yielddata,
    yield_full_report
)

main = Blueprint("main", __name__)

# ----------------------
# Dashboard
# ----------------------
@main.route("/")
def dashboard():
    with engine.connect() as conn:
        # Fetch last 10 yield records
        result = conn.execute(
            select(yielddata).order_by(yielddata.c.year.desc()).limit(10)
        ).mappings()
        yield_records = result.all()
        columns = yield_records[0].keys() if yield_records else []

        # Aggregates
        total_production = conn.execute(select(func.sum(yielddata.c.production))).scalar() or 0
        total_area = conn.execute(select(func.sum(yielddata.c.areaharvested))).scalar() or 0
        avg_yield_per_ha = total_production / total_area if total_area else 0
        total_records = conn.execute(select(func.count(yielddata.c.yieldid))).scalar() or 0

    return render_template(
        "index.html",
        yield_records=yield_records,
        columns=columns,
        total_production=total_production,
        total_area=total_area,
        avg_yield_per_ha=avg_yield_per_ha,
        total_records=total_records
    )

# ----------------------
# Add Yield
# ----------------------
@main.route("/yield/add", methods=["GET", "POST"])
def add_yield():
    with engine.connect() as conn:
        # Fetch dropdown options
        crops = conn.execute(select(crop_master).order_by(crop_master.c.CropName)).mappings().all()
        districts = conn.execute(select(district).order_by(district.c.districtname)).mappings().all()
        municipalities = conn.execute(select(municipality).order_by(municipality.c.municipalityname)).mappings().all()
        seasons = conn.execute(select(season_master).order_by(season_master.c.seasonname)).mappings().all()

        if request.method == "POST":
            stmt = insert(yielddata).values(
                cropid=request.form.get("crop_id"),
                districtid=request.form.get("district_id"),
                municipalityid=request.form.get("municipality_id"),
                seasonid=request.form.get("season_id"),
                year=request.form.get("year"),
                areaharvested=request.form.get("area_harvested"),
                yieldamount=request.form.get("yield_amount"),
                production=request.form.get("production")
            )
            conn.execute(stmt)
            conn.commit()
            flash("Yield record added successfully!", "success")
            return redirect(url_for("main.dashboard"))

    return render_template(
        "add_yield.html",
        crops=crops,
        districts=districts,
        municipalities=municipalities,
        seasons=seasons
    )

# ----------------------
# Add Crop Master
# ----------------------
@main.route("/master/crop/add", methods=["GET", "POST"])
def add_crop_master():
    with engine.connect() as conn:
        crop_types = conn.execute(select(crop_type_master)).mappings().all()

        if request.method == "POST":
            stmt = insert(crop_master).values(
                CropName=request.form.get("crop_name"),
                croptypeid=request.form.get("croptype_id")
            )
            conn.execute(stmt)
            conn.commit()
            flash("Crop added successfully!", "success")
            return redirect(url_for("main.list_crop_master"))

    return render_template("add_crop.html", crop_types=crop_types)

# ----------------------
# List Crops
# ----------------------
@main.route("/master/crop")
def list_crop_master():
    with engine.connect() as conn:
        # Join crop_master with crop_type_master dynamically
        result = conn.execute(
            select(
                crop_master.c.CropId,
                crop_master.c.CropName,
                crop_type_master.c.croptypename
            ).join(crop_type_master, crop_master.c.croptypeid == crop_type_master.c.croptypeid)
        ).mappings()
        crops = result.all()
        columns = crops[0].keys() if crops else []

    return render_template("list_crops.html", crops=crops, columns=columns)

# ----------------------
# Delete Yield
# ----------------------
@main.route("/delete_yield/<int:yield_id>", methods=["POST"])
def delete_yield(yield_id):
    with engine.connect() as conn:
        try:
            stmt = delete(yielddata).where(yielddata.c.yieldid == yield_id)
            conn.execute(stmt)
            conn.commit()
            flash("Yield record deleted successfully!", "success")
        except Exception as e:
            flash(f"Error deleting record: {str(e)}", "danger")
    return redirect(url_for("main.dashboard"))

# ----------------------
# Edit Yield
# ----------------------
@main.route("/yield/<int:yield_id>/edit", methods=["GET", "POST"])
def edit_yield(yield_id):
    with engine.connect() as conn:
        yield_record = conn.execute(
            select(yielddata).where(yielddata.c.yieldid == yield_id)
        ).mappings().first()

        # Fetch related tables
        crops = conn.execute(select(crop_master)).mappings().all()
        districts = conn.execute(select(district)).mappings().all()
        municipalities = conn.execute(select(municipality)).mappings().all()
        seasons = conn.execute(select(season_master).order_by(season_master.c.seasonname)).mappings().all()

        if request.method == "POST":
            stmt = update(yielddata).where(yielddata.c.yieldid == yield_id).values(
                cropid=request.form.get("crop_id"),
                districtid=request.form.get("district_id"),
                municipalityid=request.form.get("municipality_id"),
                seasonid=request.form.get("season_id"),
                year=request.form.get("year"),
                areaharvested=request.form.get("area_harvested"),
                yieldamount=request.form.get("yield_amount"),
                production=request.form.get("production")
            )
            conn.execute(stmt)
            conn.commit()
            flash("Yield record updated successfully!", "success")
            return redirect(url_for("main.dashboard"))

    return render_template(
        "edit_yield.html",
        yield_record=yield_record,
        crops=crops,
        districts=districts,
        municipalities=municipalities,
        seasons=seasons
    )


# ----------------------
# Full Yield Report
# ----------------------
@main.route("/yield/full_report")
def full_yield_report():
    with engine.connect() as conn:
        result = conn.execute(select(yield_full_report)).mappings()
        report_data = result.all()
        columns = report_data[0].keys() if report_data else []

    return render_template(
        "full_yield_report.html",
        report_data=report_data,
        columns=columns
    )
