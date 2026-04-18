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
