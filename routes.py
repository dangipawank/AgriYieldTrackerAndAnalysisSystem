from datetime import datetime
from io import BytesIO
import csv
import io

from openpyxl import Workbook
from flask import Blueprint, flash, render_template, request, redirect, url_for, send_file, Response, session
from sqlalchemy import select, func, insert, update, delete, text
from sqlalchemy.exc import IntegrityError

from models import (
    engine,
    crop_master,
    district,
    municipality,
    season_master,
    crop_type_master,
    yielddata,
    yield_full_report,
    users,
)
from services.yield_service import (
    get_total_production,
    get_total_cultivated_area,
    get_average_yield,
    get_highest_producing_crop,
    get_latest_year_data_count,
)
from services.audit_service import log_audit
from services.auth_service import ROLE_ADMIN, ROLE_FARMER, ROLE_OFFICER, hash_password
from utils.security import login_required, role_required, get_current_user_id


main = Blueprint("main", __name__)




def validate_yield_data(data):
    """Validate business rules and FK references before writing yield records."""
    errors = []
    current_year = datetime.now().year

    if data.get("yieldamount", 0) < 0:
        errors.append("Yield amount cannot be negative")
    if data.get("production", 0) < 0:
        errors.append("Production cannot be negative")
    if data.get("areaharvested", 0) < 0:
        errors.append("Area harvested cannot be negative")

    if not (1900 <= data.get("year", 0) <= current_year):
        errors.append(f"Year must be between 1900 and {current_year}")

    with engine.connect() as conn:
        if not conn.execute(select(crop_master).where(crop_master.c.CropId == data.get("crop_id"))).first():
            errors.append("Invalid crop selected")
        if not conn.execute(select(district).where(district.c.districtid == data.get("district_id"))).first():
            errors.append("Invalid district selected")
        if not conn.execute(select(municipality).where(municipality.c.municipalityid == data.get("municipality_id"))).first():
            errors.append("Invalid municipality selected")
        if not conn.execute(select(season_master).where(season_master.c.seasonid == data.get("season_id"))).first():
            errors.append("Invalid season selected")

    return errors


def _build_full_report_query(selected_year, selected_crop_id, selected_district_id, selected_season_id):
    query = select(yield_full_report)
    if selected_year is not None:
        query = query.where(yield_full_report.c.year == selected_year)
    if selected_crop_id is not None:
        query = query.where(yield_full_report.c.cropid == selected_crop_id)
    if selected_district_id is not None:
        query = query.where(yield_full_report.c.districtid == selected_district_id)
    if selected_season_id is not None:
        query = query.where(yield_full_report.c.seasonid == selected_season_id)
    return query


def _sync_crop_type_sequence(conn):
    conn.execute(
        text(
            """
            SELECT setval(
                pg_get_serial_sequence('crop_type_master', 'croptypeid'),
                COALESCE((SELECT MAX(croptypeid) FROM crop_type_master), 0) + 1,
                false
            )
            """
        )
    )


def _sync_season_sequence(conn):
    conn.execute(
        text(
            """
            SELECT setval(
                pg_get_serial_sequence('season_master', 'seasonid'),
                COALESCE((SELECT MAX(seasonid) FROM season_master), 0) + 1,
                false
            )
            """
        )
    )


@main.route("/")
@login_required
def dashboard():
    """Dashboard with latest records and KPI cards."""
    try:
        with engine.connect() as conn:
            current_user_id = get_current_user_id()
            current_user_role = session.get("role")

            yield_query = select(yielddata)
            count_query = select(func.count(yielddata.c.yieldid))

            if current_user_role == ROLE_FARMER and current_user_id:
                yield_query = yield_query.where(yielddata.c.created_by == current_user_id)
                count_query = count_query.where(yielddata.c.created_by == current_user_id)

            result = conn.execute(yield_query.order_by(yielddata.c.year.desc()).limit(10)).mappings()
            yield_records = result.all()
            columns = yield_records[0].keys() if yield_records else []
            total_records = conn.execute(count_query).scalar() or 0

            farmer_summary = None
            if current_user_role == ROLE_FARMER and current_user_id:
                my_records = conn.execute(
                    select(func.count(yielddata.c.yieldid)).where(yielddata.c.created_by == current_user_id)
                ).scalar() or 0
                my_production = conn.execute(
                    select(func.sum(yielddata.c.production)).where(yielddata.c.created_by == current_user_id)
                ).scalar() or 0
                my_area = conn.execute(
                    select(func.sum(yielddata.c.areaharvested)).where(yielddata.c.created_by == current_user_id)
                ).scalar() or 0
                farmer_summary = {
                    "records": my_records,
                    "production": float(my_production),
                    "area": float(my_area),
                    "avg_yield": float(my_production / my_area) if my_area else 0.0,
                }

        return render_template(
            "index.html",
            yield_records=yield_records,
            columns=columns,
            total_production=get_total_production(),
            total_area=get_total_cultivated_area(),
            avg_yield_per_ha=get_average_yield(),
            total_records=total_records,
            highest_crop=get_highest_producing_crop(),
            latest_year_data_count=get_latest_year_data_count(),
            farmer_summary=farmer_summary,
        )
    except Exception as exc:
        flash(f"Unable to load dashboard: {exc}", "danger")
        return render_template(
            "index.html",
            yield_records=[],
            columns=[],
            total_production=0,
            total_area=0,
            avg_yield_per_ha=0,
            total_records=0,
            highest_crop={"crop_name": "N/A", "total_production": 0},
            latest_year_data_count=0,
            farmer_summary=None,
        )


@main.route("/yield/add", methods=["GET", "POST"])
@login_required
@role_required(ROLE_FARMER, ROLE_ADMIN)
def add_yield():
    """Add a new yield record. Farmer role only."""
    user_id = get_current_user_id()
    form_data = {}
    errors = []

    try:
        with engine.connect() as conn:
            crops = conn.execute(select(crop_master).order_by(crop_master.c.CropName)).mappings().all()
            districts = conn.execute(select(district).order_by(district.c.districtname)).mappings().all()
            municipalities = conn.execute(select(municipality).order_by(municipality.c.municipalityname)).mappings().all()
            seasons = conn.execute(select(season_master).order_by(season_master.c.seasonname)).mappings().all()

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
                    errors.append("Please enter valid numeric values.")
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
                        created_by=user_id,
                        updated_by=user_id,
                    )
                    result = conn.execute(stmt)
                    conn.commit()
                    log_audit("INSERT", "yielddata", user_id=user_id, record_id=getattr(result, "inserted_primary_key", [None])[0])
                    flash("Yield record added successfully!", "success")
                    return redirect(url_for("main.dashboard"))

        for error in errors:
            flash(error, "danger")

        return render_template(
            "add_yield.html",
            crops=crops,
            districts=districts,
            municipalities=municipalities,
            seasons=seasons,
            form_data=form_data,
            field_errors={},
        )
    except Exception as exc:
        flash(f"Unable to process yield form: {exc}", "danger")
        return redirect(url_for("main.dashboard"))


@main.route("/yield/<int:yield_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_FARMER, ROLE_ADMIN)
def edit_yield(yield_id):
    """Edit existing yield record. Farmer role only."""
    user_id = get_current_user_id()

    with engine.connect() as conn:
        yield_record = conn.execute(select(yielddata).where(yielddata.c.yieldid == yield_id)).mappings().first()
        if not yield_record:
            flash("Yield record not found.", "danger")
            return redirect(url_for("main.dashboard"))

        current_role = session.get("role")
        if current_role == ROLE_FARMER and yield_record.get("created_by") != user_id:
            flash("You are not authorized to edit this record.", "danger")
            return redirect(url_for("main.dashboard"))

        crops = conn.execute(select(crop_master).order_by(crop_master.c.CropName)).mappings().all()
        districts = conn.execute(select(district).order_by(district.c.districtname)).mappings().all()
        municipalities = conn.execute(select(municipality).order_by(municipality.c.municipalityname)).mappings().all()
        seasons = conn.execute(select(season_master).order_by(season_master.c.seasonname)).mappings().all()

        form_data = {
            "crop_id": yield_record["cropid"],
            "district_id": yield_record["districtid"],
            "municipality_id": yield_record["municipalityid"],
            "season_id": yield_record["seasonid"],
            "year": yield_record["year"],
            "areaharvested": yield_record["areaharvested"],
            "yieldamount": yield_record["yieldamount"],
            "production": yield_record["production"],
        }

        if request.method == "POST":
            try:
                form_data.update(
                    {
                        "crop_id": int(request.form.get("crop_id", 0)),
                        "district_id": int(request.form.get("district_id", 0)),
                        "municipality_id": int(request.form.get("municipality_id", 0)),
                        "season_id": int(request.form.get("season_id", 0)),
                        "year": int(request.form.get("year", 0)),
                        "areaharvested": float(request.form.get("area_harvested", 0)),
                        "yieldamount": float(request.form.get("yield_amount", 0)),
                        "production": float(request.form.get("production", 0)),
                    }
                )
            except ValueError:
                flash("Please enter valid numeric values.", "danger")
            else:
                errors = validate_yield_data(form_data)
                if not errors:
                    stmt = (
                        update(yielddata)
                        .where(yielddata.c.yieldid == yield_id)
                        .values(
                            cropid=form_data["crop_id"],
                            districtid=form_data["district_id"],
                            municipalityid=form_data["municipality_id"],
                            seasonid=form_data["season_id"],
                            year=form_data["year"],
                            areaharvested=form_data["areaharvested"],
                            yieldamount=form_data["yieldamount"],
                            production=form_data["production"],
                            updated_by=user_id,
                            updated_at=datetime.utcnow(),
                        )
                    )
                    conn.execute(stmt)
                    conn.commit()
                    log_audit("UPDATE", "yielddata", user_id=user_id, record_id=yield_id)
                    flash("Yield record updated successfully!", "success")
                    return redirect(url_for("main.dashboard"))

                for err in errors:
                    flash(err, "danger")

    return render_template(
        "edit_yield_fixed.html",
        form_data=form_data,
        crops=crops,
        districts=districts,
        municipalities=municipalities,
        seasons=seasons,
        field_errors={},
    )


@main.route("/delete_yield/<int:yield_id>", methods=["POST"])
@login_required
@role_required(ROLE_FARMER, ROLE_ADMIN)
def delete_yield(yield_id):
    """Delete yield record. POST only."""
    user_id = get_current_user_id()
    try:
        with engine.connect() as conn:
            current_role = session.get("role")
            record = conn.execute(select(yielddata).where(yielddata.c.yieldid == yield_id)).mappings().first()
            if not record:
                flash("Yield record not found.", "danger")
                return redirect(url_for("main.dashboard"))
            if current_role == ROLE_FARMER and record.get("created_by") != user_id:
                flash("You are not authorized to delete this record.", "danger")
                return redirect(url_for("main.dashboard"))

            stmt = delete(yielddata).where(yielddata.c.yieldid == yield_id)
            conn.execute(stmt)
            conn.commit()
            log_audit("DELETE", "yielddata", user_id=user_id, record_id=yield_id)
            flash("Yield record deleted successfully!", "success")
    except Exception as exc:
        flash(f"Error deleting record: {exc}", "danger")
    return redirect(url_for("main.dashboard"))


@main.route("/master/crop")
@login_required
@role_required(ROLE_ADMIN)
def list_crop_master():
    """List crop master entries. Admin role only."""
    with engine.connect() as conn:
        result = conn.execute(
            select(crop_master.c.CropId, crop_master.c.CropName, crop_type_master.c.croptypename).join(
                crop_type_master, crop_master.c.croptypeid == crop_type_master.c.croptypeid
            )
        ).mappings()
        crops = result.all()
        columns = crops[0].keys() if crops else []

    return render_template("list_crops.html", crops=crops, columns=columns)


@main.route("/master/crop/add", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def add_crop_master():
    """Add crop master record. Admin role only."""
    user_id = get_current_user_id()

    with engine.connect() as conn:
        crop_types = conn.execute(select(crop_type_master)).mappings().all()
        form_data = {"crop_name": "", "croptype_id": ""}
        field_errors = {}

        if request.method == "POST":
            form_data = {
                "crop_name": request.form.get("crop_name", "").strip(),
                "croptype_id": request.form.get("croptype_id", ""),
            }

            if not form_data["crop_name"]:
                field_errors["crop_name"] = "Crop name is required."
            if not form_data["croptype_id"]:
                field_errors["croptype_id"] = "Crop type is required."

            existing = conn.execute(
                select(crop_master).where(crop_master.c.CropName.ilike(form_data["crop_name"]))
            ).mappings().first()
            if existing:
                field_errors["crop_name"] = "This crop name already exists."

            if not field_errors:
                stmt = insert(crop_master).values(
                    CropName=form_data["crop_name"],
                    croptypeid=form_data["croptype_id"],
                    created_by=user_id,
                    updated_by=user_id,
                )
                result = conn.execute(stmt)
                conn.commit()
                log_audit("INSERT", "crop_master", user_id=user_id, record_id=getattr(result, "inserted_primary_key", [None])[0])
                flash("Crop added successfully!", "success")
                return redirect(url_for("main.list_crop_master"))

    return render_template("add_crop_fixed.html", crop_types=crop_types, form_data=form_data, field_errors=field_errors)


@main.route("/master/crop/<int:crop_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_crop_master(crop_id):
    """Edit crop master. Admin role only."""
    user_id = get_current_user_id()

    with engine.connect() as conn:
        crop = conn.execute(select(crop_master).where(crop_master.c.CropId == crop_id)).mappings().first()
        if not crop:
            flash("Crop not found.", "danger")
            return redirect(url_for("main.list_crop_master"))

        crop_types = conn.execute(select(crop_type_master)).mappings().all()
        form_data = {
            "CropId": crop["CropId"],
            "crop_name": crop["CropName"],
            "croptype_id": crop["croptypeid"],
        }
        field_errors = {}

        if request.method == "POST":
            name = request.form.get("crop_name", "").strip()
            croptype_id = request.form.get("croptype_id")

            if not name:
                field_errors["crop_name"] = "Crop name is required."
            if not croptype_id:
                field_errors["croptype_id"] = "Crop type is required."

            existing = conn.execute(
                select(crop_master)
                .where(crop_master.c.CropName == name)
                .where(crop_master.c.CropId != crop_id)
            ).mappings().first()
            if existing:
                field_errors["crop_name"] = "Another crop with same name exists."

            if not field_errors:
                conn.execute(
                    update(crop_master)
                    .where(crop_master.c.CropId == crop_id)
                    .values(
                        CropName=name,
                        croptypeid=croptype_id,
                        updated_by=user_id,
                        updated_at=datetime.utcnow(),
                    )
                )
                conn.commit()
                log_audit("UPDATE", "crop_master", user_id=user_id, record_id=crop_id)
                flash("Crop updated successfully!", "success")
                return redirect(url_for("main.list_crop_master"))

            form_data["crop_name"] = name
            form_data["croptype_id"] = croptype_id

    return render_template("edit_crop_fixed.html", crop_types=crop_types, form_data=form_data, field_errors=field_errors)


@main.route("/master/crop/<int:crop_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def delete_crop_master(crop_id):
    """Delete crop master record if unused. Admin role only."""
    user_id = get_current_user_id()

    try:
        with engine.connect() as conn:
            crop = conn.execute(select(crop_master).where(crop_master.c.CropId == crop_id)).mappings().first()
            if not crop:
                flash("Crop not found.", "danger")
            else:
                referenced = conn.execute(select(yielddata).where(yielddata.c.cropid == crop_id)).mappings().first()
                if referenced:
                    flash("Cannot delete crop. It is used in yield records.", "danger")
                else:
                    conn.execute(delete(crop_master).where(crop_master.c.CropId == crop_id))
                    conn.commit()
                    log_audit("DELETE", "crop_master", user_id=user_id, record_id=crop_id)
                    flash("Crop deleted successfully!", "success")
    except Exception as exc:
        flash(f"Unable to delete crop: {exc}", "danger")

    return redirect(url_for("main.list_crop_master"))


@main.route("/master/crop-type")
@login_required
@role_required(ROLE_ADMIN)
def list_crop_types():
    """List crop types. Admin role only."""
    with engine.connect() as conn:
        crop_types = conn.execute(select(crop_type_master).order_by(crop_type_master.c.croptypename)).mappings().all()
    return render_template("list_crop_types.html", crop_types=crop_types)


@main.route("/master/crop-type/add", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def add_crop_type():
    """Add crop type. Admin role only."""
    field_errors = {}
    form_data = {"croptypename": ""}

    if request.method == "POST":
        form_data["croptypename"] = request.form.get("croptypename", "").strip()
        if not form_data["croptypename"]:
            field_errors["croptypename"] = "Crop type name is required."

        with engine.connect() as conn:
            existing = conn.execute(
                select(crop_type_master).where(crop_type_master.c.croptypename.ilike(form_data["croptypename"]))
            ).mappings().first()
            if existing:
                field_errors["croptypename"] = "Crop type already exists."

            if not field_errors:
                try:
                    _sync_crop_type_sequence(conn)
                    conn.execute(insert(crop_type_master).values(croptypename=form_data["croptypename"]))
                    conn.commit()
                    flash("Crop type added successfully.", "success")
                    return redirect(url_for("main.list_crop_types"))
                except IntegrityError:
                    conn.rollback()
                    field_errors["croptypename"] = "Unable to add crop type due to data conflict. Please try a different name."
                except Exception as exc:
                    conn.rollback()
                    field_errors["croptypename"] = f"Unable to add crop type: {exc}"

    return render_template("add_crop_type.html", form_data=form_data, field_errors=field_errors)


@main.route("/master/crop-type/<int:croptype_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_crop_type(croptype_id):
    """Edit crop type. Admin role only."""
    with engine.connect() as conn:
        crop_type = conn.execute(
            select(crop_type_master).where(crop_type_master.c.croptypeid == croptype_id)
        ).mappings().first()
        if not crop_type:
            flash("Crop type not found.", "danger")
            return redirect(url_for("main.list_crop_types"))

        field_errors = {}
        form_data = {"croptypeid": croptype_id, "croptypename": crop_type["croptypename"]}

        if request.method == "POST":
            form_data["croptypename"] = request.form.get("croptypename", "").strip()
            if not form_data["croptypename"]:
                field_errors["croptypename"] = "Crop type name is required."

            existing = conn.execute(
                select(crop_type_master)
                .where(crop_type_master.c.croptypename == form_data["croptypename"])
                .where(crop_type_master.c.croptypeid != croptype_id)
            ).mappings().first()
            if existing:
                field_errors["croptypename"] = "Crop type already exists."

            if not field_errors:
                conn.execute(
                    update(crop_type_master)
                    .where(crop_type_master.c.croptypeid == croptype_id)
                    .values(croptypename=form_data["croptypename"])
                )
                conn.commit()
                flash("Crop type updated successfully.", "success")
                return redirect(url_for("main.list_crop_types"))

    return render_template("edit_crop_type.html", form_data=form_data, field_errors=field_errors)


@main.route("/master/crop-type/<int:croptype_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def delete_crop_type(croptype_id):
    """Delete crop type if not referenced by crops. Admin role only."""
    with engine.connect() as conn:
        referenced = conn.execute(
            select(crop_master).where(crop_master.c.croptypeid == croptype_id)
        ).mappings().first()
        if referenced:
            flash("Cannot delete crop type. It is used in crop records.", "danger")
            return redirect(url_for("main.list_crop_types"))

        conn.execute(delete(crop_type_master).where(crop_type_master.c.croptypeid == croptype_id))
        conn.commit()
        flash("Crop type deleted successfully.", "success")

    return redirect(url_for("main.list_crop_types"))


@main.route("/master/season")
@login_required
@role_required(ROLE_ADMIN)
def list_seasons():
    """List seasons. Admin role only."""
    with engine.connect() as conn:
        seasons = conn.execute(select(season_master).order_by(season_master.c.seasonname)).mappings().all()
    return render_template("list_seasons.html", seasons=seasons)


@main.route("/master/season/add", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def add_season():
    """Add season. Admin role only."""
    field_errors = {}
    form_data = {"seasonname": ""}

    if request.method == "POST":
        form_data["seasonname"] = request.form.get("seasonname", "").strip()
        if not form_data["seasonname"]:
            field_errors["seasonname"] = "Season name is required."

        with engine.connect() as conn:
            existing = conn.execute(
                select(season_master).where(season_master.c.seasonname.ilike(form_data["seasonname"]))
            ).mappings().first()
            if existing:
                field_errors["seasonname"] = "Season already exists."

            if not field_errors:
                try:
                    _sync_season_sequence(conn)
                    conn.execute(insert(season_master).values(seasonname=form_data["seasonname"]))
                    conn.commit()
                    flash("Season added successfully.", "success")
                    return redirect(url_for("main.list_seasons"))
                except IntegrityError:
                    conn.rollback()
                    field_errors["seasonname"] = "Unable to add season due to data conflict."
                except Exception as exc:
                    conn.rollback()
                    field_errors["seasonname"] = f"Unable to add season: {exc}"

    return render_template("add_season.html", form_data=form_data, field_errors=field_errors)


@main.route("/master/season/<int:season_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_season(season_id):
    """Edit season. Admin role only."""
    with engine.connect() as conn:
        season_row = conn.execute(select(season_master).where(season_master.c.seasonid == season_id)).mappings().first()
        if not season_row:
            flash("Season not found.", "danger")
            return redirect(url_for("main.list_seasons"))

        field_errors = {}
        form_data = {"seasonid": season_id, "seasonname": season_row["seasonname"]}

        if request.method == "POST":
            form_data["seasonname"] = request.form.get("seasonname", "").strip()
            if not form_data["seasonname"]:
                field_errors["seasonname"] = "Season name is required."

            existing = conn.execute(
                select(season_master)
                .where(season_master.c.seasonname.ilike(form_data["seasonname"]))
                .where(season_master.c.seasonid != season_id)
            ).mappings().first()
            if existing:
                field_errors["seasonname"] = "Season already exists."

            if not field_errors:
                conn.execute(
                    update(season_master)
                    .where(season_master.c.seasonid == season_id)
                    .values(seasonname=form_data["seasonname"])
                )
                conn.commit()
                flash("Season updated successfully.", "success")
                return redirect(url_for("main.list_seasons"))

    return render_template("edit_season.html", form_data=form_data, field_errors=field_errors)


@main.route("/master/season/<int:season_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def delete_season(season_id):
    """Delete season if unused by yield records. Admin role only."""
    with engine.connect() as conn:
        in_use = conn.execute(
            select(func.count(yielddata.c.yieldid)).where(yielddata.c.seasonid == season_id)
        ).scalar() or 0
        if in_use > 0:
            flash("Cannot delete season. It is used by yield records.", "danger")
            return redirect(url_for("main.list_seasons"))

        conn.execute(delete(season_master).where(season_master.c.seasonid == season_id))
        conn.commit()
        flash("Season deleted successfully.", "success")

    return redirect(url_for("main.list_seasons"))


@main.route("/admin/users")
@login_required
@role_required(ROLE_ADMIN)
def list_users():
    with engine.connect() as conn:
        rows = conn.execute(
            select(users.c.id, users.c.username, users.c.email, users.c.role, users.c.updated_at)
            .order_by(users.c.id)
        ).mappings().all()
    return render_template("list_users.html", users_data=rows)


@main.route("/admin/users/add", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def add_user_admin():
    form_data = {"username": "", "email": "", "role": ROLE_FARMER}
    errors = {}

    if request.method == "POST":
        form_data["username"] = request.form.get("username", "").strip()
        form_data["email"] = request.form.get("email", "").strip().lower()
        form_data["role"] = request.form.get("role", ROLE_FARMER)
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not form_data["username"]:
            errors["username"] = "Username is required."
        if not form_data["email"]:
            errors["email"] = "Email is required."
        if form_data["role"] not in {ROLE_FARMER, ROLE_OFFICER, ROLE_ADMIN}:
            errors["role"] = "Invalid role selected."
        if not password:
            errors["password"] = "Password is required."
        elif len(password) < 6:
            errors["password"] = "Password must be at least 6 characters."
        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        with engine.connect() as conn:
            existing = conn.execute(
                select(users).where((users.c.username == form_data["username"]) | (users.c.email == form_data["email"]))
            ).mappings().first()
            if existing:
                errors["global"] = "Username or email already exists."

            if not errors:
                conn.execute(
                    insert(users).values(
                        username=form_data["username"],
                        email=form_data["email"],
                        password_hash=hash_password(password),
                        role=form_data["role"],
                    )
                )
                conn.commit()
                flash("User created successfully.", "success")
                return redirect(url_for("main.list_users"))

    return render_template("add_user.html", form_data=form_data, errors=errors)


@main.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_user_admin(user_id):
    with engine.connect() as conn:
        record = conn.execute(select(users).where(users.c.id == user_id)).mappings().first()
        if not record:
            flash("User not found.", "danger")
            return redirect(url_for("main.list_users"))

        form_data = {
            "username": record["username"],
            "email": record["email"],
            "role": record["role"],
        }
        errors = {}

        if request.method == "POST":
            form_data["username"] = request.form.get("username", "").strip()
            form_data["email"] = request.form.get("email", "").strip().lower()
            form_data["role"] = request.form.get("role", ROLE_FARMER)
            new_password = request.form.get("password", "")

            if not form_data["username"]:
                errors["username"] = "Username is required."
            if not form_data["email"]:
                errors["email"] = "Email is required."
            if form_data["role"] not in {ROLE_FARMER, ROLE_OFFICER, ROLE_ADMIN}:
                errors["role"] = "Invalid role selected."

            existing = conn.execute(
                select(users)
                .where((users.c.username == form_data["username"]) | (users.c.email == form_data["email"]))
                .where(users.c.id != user_id)
            ).mappings().first()
            if existing:
                errors["global"] = "Username or email already exists."

            if not errors:
                values = {
                    "username": form_data["username"],
                    "email": form_data["email"],
                    "role": form_data["role"],
                    "updated_at": datetime.utcnow(),
                }
                if new_password:
                    if len(new_password) < 6:
                        errors["password"] = "Password must be at least 6 characters."
                    else:
                        values["password_hash"] = hash_password(new_password)

                if not errors:
                    conn.execute(update(users).where(users.c.id == user_id).values(**values))
                    conn.commit()
                    flash("User updated successfully.", "success")
                    return redirect(url_for("main.list_users"))

    return render_template("edit_user.html", form_data=form_data, errors=errors, edit_user_id=user_id)


@main.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def delete_user_admin(user_id):
    current_user_id = get_current_user_id()
    if current_user_id == user_id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("main.list_users"))

    with engine.connect() as conn:
        record = conn.execute(select(users).where(users.c.id == user_id)).mappings().first()
        if not record:
            flash("User not found.", "danger")
            return redirect(url_for("main.list_users"))

        conn.execute(delete(users).where(users.c.id == user_id))
        conn.commit()
        flash("User deleted successfully.", "success")

    return redirect(url_for("main.list_users"))


@main.route("/yield/full_report")
@login_required
def full_yield_report():
    """Full report with safe optional filtering."""
    try:
        selected_year = request.args.get("year", type=int)
        selected_crop_id = request.args.get("crop_id", type=int)
        selected_district_id = request.args.get("district_id", type=int)
        selected_season_id = request.args.get("season_id", type=int)
        current_user_role = session.get("role")
        current_user_id = get_current_user_id()

        with engine.connect() as conn:
            query = _build_full_report_query(selected_year, selected_crop_id, selected_district_id, selected_season_id)
            if current_user_role == ROLE_FARMER and current_user_id:
                owned_ids = select(yielddata.c.yieldid).where(yielddata.c.created_by == current_user_id)
                query = query.where(yield_full_report.c.yieldid.in_(owned_ids))
            report_data = conn.execute(query).mappings().all()
            columns = report_data[0].keys() if report_data else []

            crops = conn.execute(select(crop_master).order_by(crop_master.c.CropName)).mappings().all()
            districts = conn.execute(select(district).order_by(district.c.districtname)).mappings().all()
            seasons = conn.execute(select(season_master).order_by(season_master.c.seasonname)).mappings().all()
            years = conn.execute(
                select(yield_full_report.c.year).distinct().order_by(yield_full_report.c.year.desc())
            ).scalars().all()

        return render_template(
            "full_yield_report_fixed.html",
            report_data=report_data,
            columns=columns,
            crops=crops,
            districts=districts,
            seasons=seasons,
            years=years,
            selected_year=selected_year,
            selected_crop_id=selected_crop_id,
            selected_district_id=selected_district_id,
            selected_season_id=selected_season_id,
        )
    except Exception as exc:
        flash(f"Unable to load full report: {exc}", "danger")
        return render_template(
            "full_yield_report_fixed.html",
            report_data=[],
            columns=[],
            crops=[],
            districts=[],
            seasons=[],
            years=[],
            selected_year=None,
            selected_crop_id=None,
            selected_district_id=None,
            selected_season_id=None,
        )


@main.route("/yield/full_report/export/<string:file_format>")
@login_required
def export_full_report(file_format):
    """Export filtered report to CSV or Excel."""
    selected_year = request.args.get("year", type=int)
    selected_crop_id = request.args.get("crop_id", type=int)
    selected_district_id = request.args.get("district_id", type=int)
    selected_season_id = request.args.get("season_id", type=int)
    current_user_role = session.get("role")
    current_user_id = get_current_user_id()

    with engine.connect() as conn:
        query = _build_full_report_query(selected_year, selected_crop_id, selected_district_id, selected_season_id)
        if current_user_role == ROLE_FARMER and current_user_id:
            owned_ids = select(yielddata.c.yieldid).where(yielddata.c.created_by == current_user_id)
            query = query.where(yield_full_report.c.yieldid.in_(owned_ids))
        rows = conn.execute(query).mappings().all()

    if not rows:
        flash("No data to export for current filters.", "danger")
        return redirect(url_for("main.full_yield_report", year=selected_year, crop_id=selected_crop_id, district_id=selected_district_id, season_id=selected_season_id))

    columns = list(rows[0].keys())

    if file_format.lower() == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})
        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=yield_report.csv"},
        )

    if file_format.lower() == "excel":
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Yield Report"
        worksheet.append(columns)
        for row in rows:
            worksheet.append([row[column] for column in columns])

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="yield_report.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    flash("Unsupported export format.", "danger")
    return redirect(url_for("main.full_yield_report", year=selected_year, crop_id=selected_crop_id, district_id=selected_district_id, season_id=selected_season_id))
