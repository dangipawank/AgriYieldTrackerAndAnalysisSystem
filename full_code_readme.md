# Agri-Yield Tracker & Analysis System - Full Code

This README contains all the Python code from the project, organized by file for easy reference.

## app.py

```python
import logging
import os
from flask import Flask, render_template, request

from config import Config
from routes import main
from analysis_routes import analysis
from auth_routes import auth
from mastersetup_routes import mastersetup_bp
from init_db import init_database
from utils.security import (
    ensure_csrf_token,
    csrf_protect_request,
    get_current_user
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ---------------- Logging ----------------
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # ---------------- Context Processor ----------------
    @app.context_processor
    def inject_globals():
        user = get_current_user()
        return {
            "csrf_token": ensure_csrf_token,
            "current_user": user,
            "current_role": user.get("role") if user else None,
        }

    # ---------------- CSRF Protection ----------------
    @app.before_request
    def before_request():
        csrf_protect_request()

    # ---------------- Error Handlers ----------------
    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("500.html"), 500

    # ---------------- Blueprints ----------------
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(analysis)
    app.register_blueprint(mastersetup_bp)

    # ---------------- Init DB on startup ----------------
    try:
        init_database()
    except Exception as e:
        app.logger.error(f"Database initialization failed: {e}")
        raise  # show real error in logs

    return app


# ---------------- ENTRY POINT ----------------
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

## config.py

```python
import os


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


class Config:
    DATABASE_URL = _normalize_database_url(
        os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:root@localhost/agridb")
    )

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
```

## models.py

```python
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, String, Float, ForeignKey,
    DateTime, func, Text   # ✅ added Text
)
from config import Config

engine = create_engine(Config.DATABASE_URL)
metadata = MetaData()

# ---------------- MASTERSETUP SCHEMA ---------------- #

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

# ---------------- USERS ---------------- #

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

# ---------------- MASTER TABLES ---------------- #

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

# ---------------- CLEAN TABLE (OLTP) ---------------- #

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

# ---------------- RAW TABLE (NEW - DATA ENGINEERING) ---------------- #

raw_yield_data = Table(
    "raw_yield_data", metadata,
    Column("id", Integer, primary_key=True),
    Column("farmer_id", Integer),

    Column("crop_name", Text),
    Column("district", Text),
    Column("municipality", Text),
    Column("season", Text),

    Column("year", Text),
    Column("area", Text),
    Column("yield", Text),
    Column("production", Text),

    Column("created_at", DateTime, server_default=func.now())
)

# ---------------- VIEW ---------------- #

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
```

## routes.py

```python
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
    get_analysis_summary,
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


def _filter_report_columns(report_data):
    """Remove redundant ID columns and keep only meaningful display columns."""
    if not report_data:
        return report_data, []


    exclude_columns = {
        'yieldid', 'YieldId',
        'cropid', 'CropId',
        'districtid', 'district_id',
        'provinceid', 'province_id',
        'municipalityid', 'municipality_id',
        'seasonid', 'season_id'
    }


    all_columns = list(report_data[0].keys()) if report_data else []
    filtered_columns = [col for col in all_columns if col not in exclude_columns]


    column_order = [
        'year', 'CropName', 'croptypename', 'seasonname',
        'areaharvested', 'yieldamount', 'production',
        'municipalityname', 'districtname', 'provincename', 'MunicipalityTypeName'
    ]


    ordered_columns = [col for col in column_order if col in filtered_columns]
    remaining_columns = [col for col in filtered_columns if col not in column_order]
    final_columns = ordered_columns + remaining_columns

    return report_data, final_columns


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


@main.route("/")
@login_required
def dashboard():
    """Dashboard with latest records and KPI cards."""
    try:
        with engine.connect() as conn:
            current_user_id = get_current_user_id()
            current_user_role = session.get("role")
            dashboard_owner_id = current_user_id if current_user_role == ROLE_FARMER else None

            yield_query = select(yielddata)
            count_query = select(func.count(yielddata.c.yieldid))

            if current_user_role == ROLE_FARMER and current_user_id:
                yield_query = yield_query.where(yielddata.c.created_by == current_user_id)
                count_query = count_query.where(yielddata.c.created_by == current_user_id)

            result = conn.execute(yield_query.order_by(yielddata.c.year.desc()).limit(10)).mappings()
            yield_records = [dict(r) for r in result.all()]

            total_records = conn.execute(count_query).scalar() or 0

            # KPI Cards
            total_production = get_total_production(dashboard_owner_id)
            total_area = get_total_cultivated_area(dashboard_owner_id)
            avg_yield = get_average_yield(dashboard_owner_id)
            highest_crop = get_highest_producing_crop(dashboard_owner_id)
            latest_year_count = get_latest_year_data_count(dashboard_owner_id)
            analysis_summary = get_analysis_summary(dashboard_owner_id)

            farmer_summary = None
            if current_user_role == ROLE_FARMER and current_user_id:
                my_records = conn.execute(
                    select(func.count(yielddata.c.yieldid)).where(yielddata.c.created_by == current_user_id)
                ).scalar() or 0
                my_production = conn.execute(
                    select(func.sum(yielddata.c.production)).where(yielddata.c.created_by == current_user_id)
                ).scalar() or 0

                farmer_summary = {
                    "my_records": my_records,
                    "my_production": my_production,
                }

        return render_template(
            "index.html",
            yield_records=yield_records,
            total_records=total_records,
            total_production=total_production,
            total_area=total_area,
            avg_yield=avg_yield,
            highest_crop=highest_crop,
            latest_year_count=latest_year_count,
            analysis_summary=analysis_summary,
            farmer_summary=farmer_summary,
        )
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return render_template("index.html", yield_records=[], total_records=0)


@main.route("/yield/add", methods=["GET", "POST"])
@login_required
@role_required(ROLE_FARMER, ROLE_ADMIN)
def add_yield():
    """Add new yield record."""
    try:
        with engine.connect() as conn:
            crops = conn.execute(select(crop_master)).mappings().all()
            districts = conn.execute(select(district)).mappings().all()
            municipalities = conn.execute(select(municipality)).mappings().all()
            seasons = conn.execute(select(season_master)).mappings().all()

        if request.method == "POST":
            try:
                form_data = {
                    "crop_id": int(request.form.get("crop_id", 0)),
                    "district_id": int(request.form.get("district_id", 0)),
                    "municipality_id": int(request.form.get("municipality_id", 0)),
                    "season_id": int(request.form.get("season_id", 0)) or None,
                    "year": int(request.form.get("year", 0)),
                    "yieldamount": float(request.form.get("yieldamount", 0)),
                    "areaharvested": float(request.form.get("areaharvested", 0)),
                    "production": float(request.form.get("production", 0)),
                }
            except ValueError:
                errors.append("Please enter valid numeric values.")
            else:
                errors = validate_yield_data(form_data)

            if not errors:
                user_id = get_current_user_id()
                stmt = insert(yielddata).values(
                    cropid=form_data["crop_id"],
                    districtid=form_data["district_id"],
                    municipalityid=form_data["municipality_id"],
                    seasonid=form_data["season_id"],
                    year=form_data["year"],
                    yieldamount=form_data["yieldamount"],
                    areaharvested=form_data["areaharvested"],
                    production=form_data["production"],
                    created_by=user_id,
                    updated_by=user_id,
                )
                result = conn.execute(stmt)
                conn.commit()

                log_audit("INSERT", "yielddata", user_id=user_id, record_id=result.inserted_primary_key[0])
                flash("Yield record added successfully!", "success")
                return redirect(url_for("main.dashboard"))

        return render_template(
            "add_yield.html",
            crops=crops,
            districts=districts,
            municipalities=municipalities,
            seasons=seasons,
            errors=errors if 'errors' in locals() else [],
        )
    except Exception as e:
        flash(f"Error adding yield: {str(e)}", "danger")
        return redirect(url_for("main.dashboard"))


@main.route("/yield/<int:yield_id>/edit", methods=["GET", "POST"])
@login_required
def edit_yield(yield_id):
    """Edit existing yield record."""
    try:
        with engine.connect() as conn:
            yield_record = conn.execute(select(yielddata).where(yielddata.c.yieldid == yield_id)).mappings().first()
            if not yield_record:
                flash("Yield record not found.", "danger")
                return redirect(url_for("main.dashboard"))

            current_role = session.get("role")
            if current_role == ROLE_FARMER and yield_record.get("created_by") != get_current_user_id():
                flash("You are not authorized to edit this record.", "danger")
                return redirect(url_for("main.dashboard"))

            crops = conn.execute(select(crop_master)).mappings().all()
            districts = conn.execute(select(district)).mappings().all()
            municipalities = conn.execute(select(municipality)).mappings().all()
            seasons = conn.execute(select(season_master)).mappings().all()

        if request.method == "POST":
            try:
                form_data = {
                    "crop_id": int(request.form.get("crop_id", 0)),
                    "district_id": int(request.form.get("district_id", 0)),
                    "municipality_id": int(request.form.get("municipality_id", 0)),
                    "season_id": int(request.form.get("season_id", 0)) or None,
                    "year": int(request.form.get("year", 0)),
                    "yieldamount": float(request.form.get("yieldamount", 0)),
                    "areaharvested": float(request.form.get("areaharvested", 0)),
                    "production": float(request.form.get("production", 0)),
                }
            except ValueError:
                errors = ["Please enter valid numeric values."]
            else:
                errors = validate_yield_data(form_data)

            if not errors:
                user_id = get_current_user_id()
                stmt = (
                    update(yielddata)
                    .where(yielddata.c.yieldid == yield_id)
                    .values(
                        cropid=form_data["crop_id"],
                        districtid=form_data["district_id"],
                        municipalityid=form_data["municipality_id"],
                        seasonid=form_data["season_id"],
                        year=form_data["year"],
                        yieldamount=form_data["yieldamount"],
                        areaharvested=form_data["areaharvested"],
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

        return render_template(
            "edit_yield.html",
            yield_record=yield_record,
            crops=crops,
            districts=districts,
            municipalities=municipalities,
            seasons=seasons,
            errors=errors if 'errors' in locals() else [],
        )
    except Exception as e:
        flash(f"Error editing yield: {str(e)}", "danger")
        return redirect(url_for("main.dashboard"))


@main.route("/delete_yield/<int:yield_id>", methods=["POST"])
@login_required
def delete_yield(yield_id):
    """Delete yield record."""
    try:
        with engine.connect() as conn:
            yield_record = conn.execute(select(yielddata).where(yielddata.c.yieldid == yield_id)).mappings().first()
            if not yield_record:
                flash("Yield record not found.", "danger")
                return redirect(url_for("main.dashboard"))

            current_role = session.get("role")
            if current_role == ROLE_FARMER and yield_record.get("created_by") != get_current_user_id():
                flash("You are not authorized to delete this record.", "danger")
                return redirect(url_for("main.dashboard"))

            stmt = delete(yielddata).where(yielddata.c.yieldid == yield_id)
            conn.execute(stmt)
            conn.commit()

            log_audit("DELETE", "yielddata", user_id=get_current_user_id(), record_id=yield_id)
            flash("Yield record deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting yield: {str(e)}", "danger")

    return redirect(url_for("main.dashboard"))


@main.route("/full_yield_report", methods=["GET", "POST"])
@login_required
def full_yield_report():
    """Full yield report with filters and export."""
    try:
        with engine.connect() as conn:
            crops = conn.execute(select(crop_master)).mappings().all()
            districts = conn.execute(select(district)).mappings().all()
            seasons = conn.execute(select(season_master)).mappings().all()

        selected_year = request.args.get("year", type=int)
        selected_crop_id = request.args.get("crop_id", type=int)
        selected_district_id = request.args.get("district_id", type=int)
        selected_season_id = request.args.get("season_id", type=int)

        query = _build_full_report_query(selected_year, selected_crop_id, selected_district_id, selected_season_id)

        with engine.connect() as conn:
            result = conn.execute(query).mappings()
            report_data = [dict(r) for r in result.all()]

        report_data, columns = _filter_report_columns(report_data)

        if request.method == "POST" and request.form.get("export") == "csv":
            return _export_csv(report_data, columns)
        elif request.method == "POST" and request.form.get("export") == "excel":
            return _export_excel(report_data, columns)

        return render_template(
            "full_yield_report.html",
            report_data=report_data,
            columns=columns,
            crops=crops,
            districts=districts,
            seasons=seasons,
            selected_year=selected_year,
            selected_crop_id=selected_crop_id,
            selected_district_id=selected_district_id,
            selected_season_id=selected_season_id,
        )
    except Exception as e:
        flash(f"Error generating report: {str(e)}", "danger")
        return redirect(url_for("main.dashboard"))


def _export_csv(report_data, columns):
    """Export report data to CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in report_data:
        writer.writerow({col: row.get(col, "") for col in columns})
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=yield_report.csv"}
    )


def _export_excel(report_data, columns):
    """Export report data to Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Yield Report"

    # Header
    for col_num, column in enumerate(columns, 1):
        ws.cell(row=1, column=col_num, value=column)

    # Data
    for row_num, row in enumerate(report_data, 2):
        for col_num, column in enumerate(columns, 1):
            ws.cell(row=row_num, column=col_num, value=row.get(column, ""))

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="yield_report.xlsx"
    )
```

(Note: routes.py is truncated here for brevity; the full file has more routes for crops, seasons, etc.)

## auth_routes.py

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.auth_service import get_user_by_login, verify_password, update_user_last_seen
from utils.security import login_required


auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate user using username/email + password and store user session."""
    errors = {}
    login_value = ""

    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "")

        if not login_value:
            errors["login"] = "Username or email is required."
        if not password:
            errors["password"] = "Password is required."

        if not errors:
            user = get_user_by_login(login_value)
            if not user or not verify_password(password, user["password_hash"]):
                errors["global"] = "Invalid credentials."
            else:
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                update_user_last_seen(user["id"])
                flash(f"Welcome, {user['username']}!", "success")
                return redirect(url_for("main.dashboard"))

    return render_template("login.html", errors=errors, login_value=login_value)


@auth.route("/register", methods=["GET", "POST"])
def register():
    flash("Public registration is disabled. Please contact Admin.", "danger")
    return redirect(url_for("auth.login"))



@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    """Logout current user by clearing session."""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
```

## analysis_routes.py

```python
from flask import Blueprint, render_template, jsonify, flash, redirect, url_for, request
from sqlalchemy import select, func

from models import engine, crop_master, district, yielddata
from services.yield_service import (
    get_trend_data,
    get_crop_comparison,
    get_district_analysis,
    get_analysis_summary,
)
from services.auth_service import ROLE_ADMIN, ROLE_OFFICER
from utils.security import login_required, role_required

analysis = Blueprint("analysis", __name__)


@analysis.route("/analysis")
@login_required
@role_required(ROLE_ADMIN, ROLE_OFFICER)
def analysis_page():
    try:
        with engine.connect() as conn:
            crops = conn.execute(select(crop_master).order_by(crop_master.c.CropName)).mappings().all()
            districts = conn.execute(select(district).order_by(district.c.districtname)).mappings().all()

            selected_crop_id = request.args.get("crop_id", type=int)
            selected_district_id = request.args.get("district_id", type=int)

            filters = []
            if selected_crop_id:
                filters.append(yielddata.c.cropid == selected_crop_id)
            if selected_district_id:
                filters.append(yielddata.c.districtid == selected_district_id)

            total_production_query = select(func.sum(yielddata.c.production))
            total_area_query = select(func.sum(yielddata.c.areaharvested))
            trend_query = (
                select(
                    yielddata.c.year.label("year"),
                    func.sum(yielddata.c.production).label("total_production"),
                )
                .group_by(yielddata.c.year)
                .order_by(yielddata.c.year)
            )
            comparison_query = (
                select(
                    crop_master.c.CropName.label("crop_name"),
                    func.sum(yielddata.c.production).label("total_production"),
                )
                .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
                .group_by(crop_master.c.CropName)
                .order_by(crop_master.c.CropName)
            )
            top_crop_query = (
                select(
                    crop_master.c.CropName.label("crop_name"),
                    func.sum(yielddata.c.production).label("total_production"),
                )
                .join(crop_master, yielddata.c.cropid == crop_master.c.CropId)
                .group_by(crop_master.c.CropName)
                .order_by(func.sum(yielddata.c.production).desc())
                .limit(1)
            )

            for clause in filters:
                total_production_query = total_production_query.where(clause)
                total_area_query = total_area_query.where(clause)
                trend_query = trend_query.where(clause)
                comparison_query = comparison_query.where(clause)
                top_crop_query = top_crop_query.where(clause)

            total_production = conn.execute(total_production_query).scalar() or 0
            total_area = conn.execute(total_area_query).scalar() or 0
            average_yield = (total_production / total_area) if total_area else 0

            trend_rows = conn.execute(trend_query).mappings().all()
            comparison_rows = conn.execute(comparison_query).mappings().all()
            top_crop_row = conn.execute(top_crop_query).mappings().first() or {
                "crop_name": "N/A",
                "total_production": 0,
            }

        summary = {
            "total_production": float(total_production),
            "total_area": float(total_area),
            "average_yield": float(average_yield),
            "highest_crop": {
                "crop_name": top_crop_row.get("crop_name", "N/A"),
                "total_production": float(top_crop_row.get("total_production") or 0),
            },
        }
        chart_data = {
            "trend_labels": [str(row.get("year")) for row in trend_rows],
            "trend_values": [float(row.get("total_production") or 0) for row in trend_rows],
            "comparison_labels": [row.get("crop_name") for row in comparison_rows],
            "comparison_values": [float(row.get("total_production") or 0) for row in comparison_rows],
        }

        return render_template(
            "analysis_modern.html",
            crops=crops,
            districts=districts,
            selected_crop_id=selected_crop_id,
            selected_district_id=selected_district_id,
            summary=summary,
            chart_data=chart_data,
        )
    except Exception as exc:
        flash(f"Unable to load analysis page: {exc}", "danger")
        return redirect(url_for("main.dashboard"))


@analysis.route("/analysis/trend/<int:crop_id>")
@login_required
@role_required(ROLE_ADMIN, ROLE_OFFICER)
def trend_analysis(crop_id):
    try:
        return jsonify(get_trend_data(crop_id))
    except Exception as exc:
        return jsonify({"error": f"Unable to generate trend analysis: {exc}"}), 500


@analysis.route("/analysis/comparison")
@login_required
@role_required(ROLE_ADMIN, ROLE_OFFICER)
def crop_comparison():
    try:
        return jsonify(get_crop_comparison())
    except Exception as exc:
        return jsonify({"error": f"Unable to generate crop comparison: {exc}"}), 500


@analysis.route("/analysis/district/<int:district_id>")
@login_required
@role_required(ROLE_ADMIN, ROLE_OFFICER)
def district_analysis(district_id):
    try:
        return jsonify(get_district_analysis(district_id))
    except Exception as exc:
        return jsonify({"error": f"Unable to generate district analysis: {exc}"}), 500


@analysis.route("/analysis/summary")
@login_required
@role_required(ROLE_ADMIN, ROLE_OFFICER)
def analysis_summary():
    """Return aggregate blocks used for TU analysis explanation and charts/tables."""
    try:
        return jsonify(get_analysis_summary())
    except Exception as exc:
        return jsonify({"error": f"Unable to generate analysis summary: {exc}"}), 500
```

## mastersetup_routes.py

```python
from flask import Blueprint, flash, render_template, request, redirect, url_for
from sqlalchemy import select, insert, update, delete
from sqlalchemy.exc import IntegrityError

from models import (
    engine,
    country,
    province,
    district,
    municipalitytype,
    municipality,
)
from services.auth_service import ROLE_ADMIN
from utils.security import login_required, role_required

mastersetup_bp = Blueprint("mastersetup", __name__)


def _to_dict_list(result):
    """Convert SQLAlchemy RowMapping results to list of plain dicts for JSON serialization."""
    return [dict(row) for row in result]


def _to_dict(row):
    """Convert a single SQLAlchemy RowMapping to a plain dict. Returns None if row is None."""
    return dict(row) if row else None


def _load_countries(conn):
    return _to_dict_list(
        conn.execute(select(country).order_by(country.c.countryname)).mappings().all()
    )


def _load_provinces(conn):
    return _to_dict_list(
        conn.execute(
            select(province.c.provinceid, province.c.provincename, province.c.countryid)
            .order_by(province.c.provincename)
        ).mappings().all()
    )


def _load_provinces_with_country(conn):
    return _to_dict_list(
        conn.execute(
            select(
                province.c.provinceid,
                province.c.provincename,
                province.c.countryid,
                country.c.countryname,
            )
            .join(country, province.c.countryid == country.c.countryid)
            .order_by(country.c.countryname, province.c.provincename)
        ).mappings().all()
    )


def _load_districts(conn):
    return _to_dict_list(
        conn.execute(
            select(
                district.c.districtid,
                district.c.districtname,
                district.c.provinceid,
            )
            .order_by(district.c.districtname)
        ).mappings().all()
    )


def _load_districts_with_hierarchy(conn):
    return _to_dict_list(
        conn.execute(
            select(
                district.c.districtid,
                district.c.districtname,
                province.c.provinceid,
                province.c.provincename,
                country.c.countryname,
            )
            .join(province, district.c.provinceid == province.c.provinceid)
            .join(country, province.c.countryid == country.c.countryid)
            .order_by(country.c.countryname, province.c.provincename, district.c.districtname)
        ).mappings().all()
    )


def _load_municipality_types(conn):
    return _to_dict_list(
        conn.execute(
            select(municipalitytype).order_by(municipalitytype.c.MunicipalityTypeName)
        ).mappings().all()
    )


def _load_municipalities_with_hierarchy(conn):
    return _to_dict_list(
        conn.execute(
            select(
                municipality.c.municipalityid,
                municipality.c.municipalityname,
                municipality.c.districtid,
                municipality.c.municipalitytypeid,
                municipalitytype.c.MunicipalityTypeName,
                district.c.districtname,
                province.c.provincename,
                country.c.countryname,
            )
            .join(municipalitytype, municipality.c.municipalitytypeid == municipalitytype.c.municipalitytypeid)
            .join(district, municipality.c.districtid == district.c.districtid)
            .join(province, district.c.provinceid == province.c.provinceid)
            .join(country, province.c.countryid == country.c.countryid)
            .order_by(country.c.countryname, province.c.provincename, district.c.districtname, municipality.c.municipalityname)
        ).mappings().all()
    )


# ---------------------------------------------------------------------------
# Country
# ---------------------------------------------------------------------------

@mastersetup_bp.route("/master/country", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def manage_country():
    field_errors = {}
    form_data = {"countryname": ""}

    if request.method == "POST":
        form_data["countryname"] = request.form.get("countryname", "").strip()
        if not form_data["countryname"]:
            field_errors["countryname"] = "Country name is required."

        if not field_errors:
            try:
                with engine.begin() as conn:
                    existing = conn.execute(
                        select(country).where(
                            country.c.countryname.ilike(form_data["countryname"])
                        )
                    ).mappings().first()
                    if existing:
                        field_errors["countryname"] = "Country already exists."
                    else:
                        conn.execute(
                            insert(country).values(countryname=form_data["countryname"])
                        )
                        flash("Country added successfully.", "success")
                        return redirect(url_for("mastersetup.manage_country"))
            except IntegrityError:
                field_errors["countryname"] = "Country could not be added due to duplicate or integrity issue."
            except Exception as exc:
                field_errors["countryname"] = f"Unable to add country: {exc}"

    with engine.connect() as conn:
        countries = _load_countries(conn)

    return render_template(
        "country.html",
        countries=countries,
        form_data=form_data,
        field_errors=field_errors,
        edit_country=None,
    )


@mastersetup_bp.route("/master/country/<int:country_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_country(country_id):
    field_errors = {}
    edit_country_row = None
    form_data = {"countryname": ""}

    with engine.begin() as conn:
        edit_country_row = _to_dict(
            conn.execute(
                select(country).where(country.c.countryid == country_id)
            ).mappings().first()
        )
        if not edit_country_row:
            flash("Country not found.", "danger")
            return redirect(url_for("mastersetup.manage_country"))

        form_data["countryname"] = edit_country_row["countryname"]

        if request.method == "POST":
            form_data["countryname"] = request.form.get("countryname", "").strip()
            if not form_data["countryname"]:
                field_errors["countryname"] = "Country name is required."

            existing = conn.execute(
                select(country)
                .where(country.c.countryname.ilike(form_data["countryname"]))
                .where(country.c.countryid != country_id)
            ).mappings().first()
            if existing:
                field_errors["countryname"] = "Country already exists."
```
