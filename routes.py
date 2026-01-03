from flask import Blueprint, flash, render_template, request, redirect, url_for
from datetime import datetime
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
def validate_yield_data(data):
    errors = []
    current_year = datetime.now().year

    # Numeric checks
    if data.get('yieldamount', 0) < 0:
        errors.append("Yield amount cannot be negative")
    if data.get('production', 0) < 0:
        errors.append("Production cannot be negative")
    if data.get('areaharvested', 0) < 0:
        errors.append("Area harvested cannot be negative")

    # Year check
    if not (1900 <= data.get('year', 0) <= current_year):
        errors.append(f"Year must be between 1900 and {current_year}")

    # Foreign key checks (using engine)
    with engine.connect() as conn:
        if not conn.execute(select(crop_master).where(crop_master.c.CropId == data.get('crop_id'))).first():
            errors.append("Invalid crop selected")
        if not conn.execute(select(district).where(district.c.districtid == data.get('district_id'))).first():
            errors.append("Invalid district selected")
        if not conn.execute(select(municipality).where(municipality.c.municipalityid == data.get('municipality_id'))).first():
            errors.append("Invalid municipality selected")
        if not conn.execute(select(season_master).where(season_master.c.seasonid == data.get('season_id'))).first():
            errors.append("Invalid season selected")

    return errors

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

        # Fetch dropdown data
        crops = conn.execute(
            select(crop_master).order_by(crop_master.c.CropName)
        ).mappings().all()

        districts = conn.execute(
            select(district).order_by(district.c.districtname)
        ).mappings().all()

        municipalities = conn.execute(
            select(municipality).order_by(municipality.c.municipalityname)
        ).mappings().all()

        seasons = conn.execute(
            select(season_master).order_by(season_master.c.seasonname)
        ).mappings().all()

        form_data = {}
        errors = []

        if request.method == "POST":
            try:
                form_data = {
                    "crop_id": int(request.form.get("crop_id", 0)),
                    "district_id": int(request.form.get("district_id", 0)),
                    "municipality_id": int(request.form.get("municipality_id", 0)),
                    "season_id": int(request.form.get("season_id", 0)),
                    "year": int(request.form.get("year", 0)),
                    "areaharvested": float(request.form.get("area_harvested", 0)),
                    "yieldamount": float(request.form.get("yield_amount", 0)),
                    "production": float(request.form.get("production", 0)),
                }
            except ValueError:
                flash("Please enter valid numeric values.", "danger")
            else:
                errors = validate_yield_data(form_data)

                if not errors:
                    stmt = insert(yielddata).values(
                        cropid=form_data["crop_id"],
                        districtid=form_data["district_id"],
                        municipalityid=form_data["municipality_id"],
                        seasonid=form_data["season_id"],
                        year=form_data["year"],
                        areaharvested=form_data["areaharvested"],
                        yieldamount=form_data["yieldamount"],
                        production=form_data["production"],
                    )
                    conn.execute(stmt)
                    conn.commit()

                    flash("Yield record added successfully!", "success")
                    return redirect(url_for("main.dashboard"))

            # Validation failed → show errors on same page
            for error in errors:
                flash(error, "danger")

        return render_template(
            "add_yield.html",
            crops=crops,
            districts=districts,
            municipalities=municipalities,
            seasons=seasons,
            form_data=form_data
        )
# ----------------------
# Add Crop Master
# ----------------------
@main.route("/master/crop/add", methods=["GET", "POST"])
def add_crop_master():
    with engine.connect() as conn:
        crop_types = conn.execute(select(crop_type_master)).mappings().all()
        form_data = {"crop_name": "", "croptype_id": ""}  # default empty

        if request.method == "POST":
            # Collect form data
            form_data = {
                "crop_name": request.form.get("crop_name", "").strip(),
                "croptype_id": request.form.get("croptype_id", "")
            }

            errors = []

            # Validation
            if not form_data["crop_name"]:
                errors.append("Crop name cannot be empty.")
            if not form_data["croptype_id"]:
                errors.append("Please select a crop type.")

            # Check uniqueness
            existing = conn.execute(
                select(crop_master).where(crop_master.c.CropName.ilike(form_data["crop_name"]))
            ).mappings().first()
            if existing:
                errors.append("This crop name already exists.")

            if errors:
                # Validation failed → show form again with errors
                for e in errors:
                    flash(e, "danger")
                return render_template(
                    "add_crop.html",
                    crop_types=crop_types,
                    form_data=form_data
                )

            # ✅ Insert into DB
            stmt = insert(crop_master).values(
                CropName=form_data["crop_name"],
                croptypeid=form_data["croptype_id"]
            )
            conn.execute(stmt)
            conn.commit()

            # ✅ Redirect to list page (flash will appear there)
            flash("Crop added successfully!", "success")
            return redirect(url_for("main.list_crop_master"))

    # GET request → show blank form
    return render_template("add_crop.html", crop_types=crop_types, form_data=form_data)

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
# Edit Crop Master
# ----------------------
@main.route("/master/crop/<int:crop_id>/edit", methods=["GET", "POST"])
def edit_crop_master(crop_id):
    with engine.connect() as conn:
        # Fetch the crop to edit
        crop = conn.execute(
            select(crop_master).where(crop_master.c.CropId == crop_id)
        ).mappings().first()

        if not crop:
            flash("Crop not found.", "danger")
            return redirect(url_for("main.list_crop_master"))

        # Fetch crop types
        crop_types = conn.execute(select(crop_type_master)).mappings().all()

        # Normalize keys for the template
        form_data = {
            "CropId": crop["CropId"],            # optional, if you use it
            "crop_name": crop["CropName"],
            "croptype_id": crop["croptypeid"]
        }

        if request.method == "POST":
            name = request.form.get("crop_name", "").strip()
            croptype_id = request.form.get("croptype_id")

            errors = []

            # Validations
            if not name:
                errors.append("Crop name cannot be empty.")

            if not croptype_id:
                errors.append("Crop type must be selected.")

            # Check for uniqueness (ignore current crop)
            existing = conn.execute(
                select(crop_master)
                .where(crop_master.c.CropName == name)
                .where(crop_master.c.CropId != crop_id)
            ).mappings().first()
            if existing:
                errors.append("Another crop with the same name already exists.")

            if errors:
                # Keep user input in form
                form_data["crop_name"] = name
                form_data["croptype_id"] = croptype_id
                for e in errors:
                    flash(e, "danger")
            else:
                # Update DB
                stmt = (
                    update(crop_master)
                    .where(crop_master.c.CropId == crop_id)
                    .values(CropName=name, croptypeid=croptype_id)
                )
                conn.execute(stmt)
                conn.commit()
                flash("Crop updated successfully!", "success")
                return redirect(url_for("main.list_crop_master"))

        return render_template(
            "edit_crop.html",
            crop_types=crop_types,
            form_data=form_data
        )

# ----------------------
# Delete Crop Master
# ----------------------
@main.route("/master/crop/<int:crop_id>/delete", methods=["POST", "GET"])
def delete_crop_master(crop_id):
    with engine.connect() as conn:
        # Check if crop exists
        crop = conn.execute(
            select(crop_master).where(crop_master.c.CropId == crop_id)
        ).mappings().first()

        if not crop:
            flash("Crop not found.", "danger")
        else:
            # Optional: Check if crop is referenced in yielddata
            referenced = conn.execute(
                select(yielddata).where(yielddata.c.cropid == crop_id)
            ).mappings().first()
            if referenced:
                flash("Cannot delete crop. It is used in yield records.", "danger")
            else:
                conn.execute(
                    crop_master.delete().where(crop_master.c.CropId == crop_id)
                )
                conn.commit()
                flash("Crop deleted successfully!", "success")

    return redirect(url_for("main.list_crop_master"))


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
        # Fetch the record to edit
        yield_record = conn.execute(
            select(yielddata).where(yielddata.c.yieldid == yield_id)
        ).mappings().first()

        if not yield_record:
            flash("Yield record not found.", "danger")
            return redirect(url_for("main.dashboard"))

        # Fetch dropdowns
        crops = conn.execute(select(crop_master).order_by(crop_master.c.CropName)).mappings().all()
        districts = conn.execute(select(district).order_by(district.c.districtname)).mappings().all()
        municipalities = conn.execute(select(municipality).order_by(municipality.c.municipalityname)).mappings().all()
        seasons = conn.execute(select(season_master).order_by(season_master.c.seasonname)).mappings().all()

        # Initialize form_data with original values
        form_data = {
            "crop_id": yield_record["cropid"],
            "district_id": yield_record["districtid"],
            "municipality_id": yield_record["municipalityid"],
            "season_id": yield_record["seasonid"],
            "year": yield_record["year"],
            "areaharvested": yield_record["areaharvested"],
            "yieldamount": yield_record["yieldamount"],
            "production": yield_record["production"]
        }

        if request.method == "POST":
            try:
                # Overwrite with user-submitted data
                form_data.update({
                    "crop_id": int(request.form.get("crop_id", 0)),
                    "district_id": int(request.form.get("district_id", 0)),
                    "municipality_id": int(request.form.get("municipality_id", 0)),
                    "season_id": int(request.form.get("season_id", 0)),
                    "year": int(request.form.get("year", 0)),
                    "areaharvested": float(request.form.get("area_harvested", 0)),
                    "yieldamount": float(request.form.get("yield_amount", 0)),
                    "production": float(request.form.get("production", 0))
                })
            except ValueError:
                flash("Please enter valid numeric values.", "danger")
            else:
                errors = validate_yield_data(form_data)

                if not errors:
                    # Update database
                    stmt = update(yielddata).where(yielddata.c.yieldid == yield_id).values(
                        cropid=form_data["crop_id"],
                        districtid=form_data["district_id"],
                        municipalityid=form_data["municipality_id"],
                        seasonid=form_data["season_id"],
                        year=form_data["year"],
                        areaharvested=form_data["areaharvested"],
                        yieldamount=form_data["yieldamount"],
                        production=form_data["production"]
                    )
                    conn.execute(stmt)
                    conn.commit()
                    flash("Yield record updated successfully!", "success")
                    return redirect(url_for("main.dashboard"))

                # Show validation errors and retain user-entered values
                for e in errors:
                    flash(e, "danger")

        return render_template(
            "edit_yield.html",
            form_data=form_data,
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
