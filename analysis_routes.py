from flask import Blueprint, render_template, jsonify, flash, redirect, url_for
from sqlalchemy import select

from models import engine, crop_master, district
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
        return render_template("analysis.html", crops=crops, districts=districts)
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
