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
    edit_country = None
    form_data = {"countryname": ""}

    with engine.begin() as conn:
        edit_country = conn.execute(
            select(country).where(country.c.countryid == country_id)
        ).mappings().first()
        if not edit_country:
            flash("Country not found.", "danger")
            return redirect(url_for("mastersetup.manage_country"))

        form_data["countryname"] = edit_country["countryname"]

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

            if not field_errors:
                conn.execute(
                    update(country)
                    .where(country.c.countryid == country_id)
                    .values(countryname=form_data["countryname"])
                )
                flash("Country updated successfully.", "success")
                return redirect(url_for("mastersetup.manage_country"))

    with engine.connect() as conn:
        countries = _load_countries(conn)

    return render_template(
        "country.html",
        countries=countries,
        form_data=form_data,
        field_errors=field_errors,
        edit_country=edit_country,
    )


@mastersetup_bp.route("/master/country/<int:country_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def delete_country(country_id):
    with engine.begin() as conn:
        referenced = conn.execute(
            select(province).where(province.c.countryid == country_id)
        ).mappings().first()
        if referenced:
            flash("Cannot delete country because provinces are assigned to it.", "danger")
            return redirect(url_for("mastersetup.manage_country"))

        conn.execute(delete(country).where(country.c.countryid == country_id))
        flash("Country deleted successfully.", "success")

    return redirect(url_for("mastersetup.manage_country"))


@mastersetup_bp.route("/master/province", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def manage_province():
    field_errors = {}
    form_data = {"countryid": None, "provincename": ""}

    with engine.connect() as conn:
        country_options = _load_countries(conn)
        province_rows = conn.execute(
            select(
                province.c.provinceid,
                province.c.provincename,
                country.c.countryid,
                country.c.countryname,
            )
            .join(country, province.c.countryid == country.c.countryid)
            .order_by(country.c.countryname, province.c.provincename)
        ).mappings().all()

    if request.method == "POST":
        form_data["countryid"] = request.form.get("countryid", type=int)
        form_data["provincename"] = request.form.get("provincename", "").strip()
        if not form_data["countryid"]:
            field_errors["countryid"] = "Country selection is required."
        if not form_data["provincename"]:
            field_errors["provincename"] = "Province name is required."

        if not field_errors:
            try:
                with engine.begin() as conn:
                    existing = conn.execute(
                        select(province)
                        .where(province.c.provincename.ilike(form_data["provincename"]))
                        .where(province.c.countryid == form_data["countryid"])
                    ).mappings().first()
                    if existing:
                        field_errors["provincename"] = "Province already exists for this country."
                    else:
                        conn.execute(
                            insert(province).values(
                                countryid=form_data["countryid"],
                                provincename=form_data["provincename"],
                            )
                        )
                        flash("Province added successfully.", "success")
                        return redirect(url_for("mastersetup.manage_province"))
            except IntegrityError:
                field_errors["provincename"] = "Province could not be added due to duplicate or integrity issue."
            except Exception as exc:
                field_errors["provincename"] = f"Unable to add province: {exc}"

    return render_template(
        "province.html",
        province_rows=province_rows,
        country_options=country_options,
        form_data=form_data,
        field_errors=field_errors,
        edit_province=None,
    )


@mastersetup_bp.route("/master/province/<int:province_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_province(province_id):
    field_errors = {}
    edit_province = None
    form_data = {"countryid": None, "provincename": ""}

    with engine.begin() as conn:
        edit_province = conn.execute(
            select(province).where(province.c.provinceid == province_id)
        ).mappings().first()
        if not edit_province:
            flash("Province not found.", "danger")
            return redirect(url_for("mastersetup.manage_province"))

        form_data["countryid"] = edit_province["countryid"]
        form_data["provincename"] = edit_province["provincename"]

        if request.method == "POST":
            form_data["countryid"] = request.form.get("countryid", type=int)
            form_data["provincename"] = request.form.get("provincename", "").strip()
            if not form_data["countryid"]:
                field_errors["countryid"] = "Country selection is required."
            if not form_data["provincename"]:
                field_errors["provincename"] = "Province name is required."

            existing = conn.execute(
                select(province)
                .where(province.c.provincename.ilike(form_data["provincename"]))
                .where(province.c.countryid == form_data["countryid"])
                .where(province.c.provinceid != province_id)
            ).mappings().first()
            if existing:
                field_errors["provincename"] = "Province already exists for this country."

            if not field_errors:
                conn.execute(
                    update(province)
                    .where(province.c.provinceid == province_id)
                    .values(
                        countryid=form_data["countryid"],
                        provincename=form_data["provincename"],
                    )
                )
                flash("Province updated successfully.", "success")
                return redirect(url_for("mastersetup.manage_province"))

    with engine.connect() as conn:
        country_options = _load_countries(conn)
        province_rows = conn.execute(
            select(
                province.c.provinceid,
                province.c.provincename,
                country.c.countryid,
                country.c.countryname,
            )
            .join(country, province.c.countryid == country.c.countryid)
            .order_by(country.c.countryname, province.c.provincename)
        ).mappings().all()

    return render_template(
        "province.html",
        province_rows=province_rows,
        country_options=country_options,
        form_data=form_data,
        field_errors=field_errors,
        edit_province=edit_province,
    )


@mastersetup_bp.route("/master/province/<int:province_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def delete_province(province_id):
    with engine.begin() as conn:
        referenced = conn.execute(
            select(district).where(district.c.provinceid == province_id)
        ).mappings().first()
        if referenced:
            flash("Cannot delete province because districts are assigned to it.", "danger")
            return redirect(url_for("mastersetup.manage_province"))

        conn.execute(delete(province).where(province.c.provinceid == province_id))
        flash("Province deleted successfully.", "success")

    return redirect(url_for("mastersetup.manage_province"))


@mastersetup_bp.route("/master/district", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def manage_district():
    field_errors = {}
    form_data = {"countryid": None, "provinceid": None, "districtname": ""}

    with engine.connect() as conn:
        country_options = _load_countries(conn)
        province_options = _load_provinces(conn)
        district_rows = _load_districts_with_hierarchy(conn)

    if request.method == "POST":
        form_data["countryid"] = request.form.get("countryid", type=int)
        form_data["provinceid"] = request.form.get("provinceid", type=int)
        form_data["districtname"] = request.form.get("districtname", "").strip()

        if not form_data["countryid"]:
            field_errors["countryid"] = "Country selection is required."
        if not form_data["provinceid"]:
            field_errors["provinceid"] = "Province selection is required."
        if not form_data["districtname"]:
            field_errors["districtname"] = "District name is required."

        if not field_errors:
            try:
                with engine.begin() as conn:
                    existing = conn.execute(
                        select(district)
                        .where(district.c.districtname.ilike(form_data["districtname"]))
                        .where(district.c.provinceid == form_data["provinceid"])
                    ).mappings().first()
                    if existing:
                        field_errors["districtname"] = "District already exists for this province."
                    else:
                        conn.execute(
                            insert(district).values(
                                provinceid=form_data["provinceid"],
                                districtname=form_data["districtname"],
                            )
                        )
                        flash("District added successfully.", "success")
                        return redirect(url_for("mastersetup.manage_district"))
            except IntegrityError:
                field_errors["districtname"] = "District could not be added due to duplicate or integrity issue."
            except Exception as exc:
                field_errors["districtname"] = f"Unable to add district: {exc}"

    return render_template(
        "district.html",
        district_rows=district_rows,
        country_options=country_options,
        province_options=province_options,
        form_data=form_data,
        field_errors=field_errors,
        edit_district=None,
    )


@mastersetup_bp.route("/master/district/<int:district_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_district(district_id):
    field_errors = {}
    edit_district = None
    form_data = {"countryid": None, "provinceid": None, "districtname": ""}

    with engine.begin() as conn:
        edit_district = conn.execute(
            select(district).where(district.c.districtid == district_id)
        ).mappings().first()
        if not edit_district:
            flash("District not found.", "danger")
            return redirect(url_for("mastersetup.manage_district"))

        province_row = conn.execute(
            select(province).where(province.c.provinceid == edit_district["provinceid"])
        ).mappings().first()
        form_data["provinceid"] = edit_district["provinceid"]
        form_data["countryid"] = province_row["countryid"] if province_row else None
        form_data["districtname"] = edit_district["districtname"]

        if request.method == "POST":
            form_data["countryid"] = request.form.get("countryid", type=int)
            form_data["provinceid"] = request.form.get("provinceid", type=int)
            form_data["districtname"] = request.form.get("districtname", "").strip()

            if not form_data["countryid"]:
                field_errors["countryid"] = "Country selection is required."
            if not form_data["provinceid"]:
                field_errors["provinceid"] = "Province selection is required."
            if not form_data["districtname"]:
                field_errors["districtname"] = "District name is required."

            existing = conn.execute(
                select(district)
                .where(district.c.districtname.ilike(form_data["districtname"]))
                .where(district.c.provinceid == form_data["provinceid"])
                .where(district.c.districtid != district_id)
            ).mappings().first()
            if existing:
                field_errors["districtname"] = "District already exists for this province."

            if not field_errors:
                conn.execute(
                    update(district)
                    .where(district.c.districtid == district_id)
                    .values(
                        provinceid=form_data["provinceid"],
                        districtname=form_data["districtname"],
                    )
                )
                flash("District updated successfully.", "success")
                return redirect(url_for("mastersetup.manage_district"))

    with engine.connect() as conn:
        country_options = _load_countries(conn)
        province_options = _load_provinces(conn)
        district_rows = _load_districts_with_hierarchy(conn)

    return render_template(
        "district.html",
        district_rows=district_rows,
        country_options=country_options,
        province_options=province_options,
        form_data=form_data,
        field_errors=field_errors,
        edit_district=edit_district,
    )


@mastersetup_bp.route("/master/district/<int:district_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def delete_district(district_id):
    with engine.begin() as conn:
        referenced = conn.execute(
            select(municipality).where(municipality.c.districtid == district_id)
        ).mappings().first()
        if referenced:
            flash("Cannot delete district because municipalities are assigned to it.", "danger")
            return redirect(url_for("mastersetup.manage_district"))

        conn.execute(delete(district).where(district.c.districtid == district_id))
        flash("District deleted successfully.", "success")

    return redirect(url_for("mastersetup.manage_district"))


@mastersetup_bp.route("/master/municipality-type", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def manage_municipality_type():
    field_errors = {}
    form_data = {"MunicipalityTypeName": ""}

    if request.method == "POST":
        form_data["MunicipalityTypeName"] = request.form.get("MunicipalityTypeName", "").strip()
        if not form_data["MunicipalityTypeName"]:
            field_errors["MunicipalityTypeName"] = "Municipality type name is required."

        if not field_errors:
            try:
                with engine.begin() as conn:
                    existing = conn.execute(
                        select(municipalitytype).where(
                            municipalitytype.c.MunicipalityTypeName.ilike(form_data["MunicipalityTypeName"])
                        )
                    ).mappings().first()
                    if existing:
                        field_errors["MunicipalityTypeName"] = "Municipality type already exists."
                    else:
                        conn.execute(
                            insert(municipalitytype).values(
                                MunicipalityTypeName=form_data["MunicipalityTypeName"]
                            )
                        )
                        flash("Municipality type added successfully.", "success")
                        return redirect(url_for("mastersetup.manage_municipality_type"))
            except IntegrityError:
                field_errors["MunicipalityTypeName"] = "Unable to add municipality type due to duplicate or integrity issue."
            except Exception as exc:
                field_errors["MunicipalityTypeName"] = f"Unable to add municipality type: {exc}"

    with engine.connect() as conn:
        municipality_types = _load_municipality_types(conn)

    return render_template(
        "municipality_type.html",
        municipality_types=municipality_types,
        form_data=form_data,
        field_errors=field_errors,
        edit_type=None,
    )


@mastersetup_bp.route("/master/municipality-type/<int:type_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_municipality_type(type_id):
    field_errors = {}
    edit_type = None
    form_data = {"MunicipalityTypeName": ""}

    with engine.begin() as conn:
        edit_type = conn.execute(
            select(municipalitytype).where(municipalitytype.c.municipalitytypeid == type_id)
        ).mappings().first()
        if not edit_type:
            flash("Municipality type not found.", "danger")
            return redirect(url_for("mastersetup.manage_municipality_type"))

        form_data["MunicipalityTypeName"] = edit_type["MunicipalityTypeName"]

        if request.method == "POST":
            form_data["MunicipalityTypeName"] = request.form.get("MunicipalityTypeName", "").strip()
            if not form_data["MunicipalityTypeName"]:
                field_errors["MunicipalityTypeName"] = "Municipality type name is required."

            existing = conn.execute(
                select(municipalitytype)
                .where(municipalitytype.c.MunicipalityTypeName.ilike(form_data["MunicipalityTypeName"]))
                .where(municipalitytype.c.municipalitytypeid != type_id)
            ).mappings().first()
            if existing:
                field_errors["MunicipalityTypeName"] = "Municipality type already exists."

            if not field_errors:
                conn.execute(
                    update(municipalitytype)
                    .where(municipalitytype.c.municipalitytypeid == type_id)
                    .values(MunicipalityTypeName=form_data["MunicipalityTypeName"])
                )
                flash("Municipality type updated successfully.", "success")
                return redirect(url_for("mastersetup.manage_municipality_type"))

    with engine.connect() as conn:
        municipality_types = _load_municipality_types(conn)

    return render_template(
        "municipality_type.html",
        municipality_types=municipality_types,
        form_data=form_data,
        field_errors=field_errors,
        edit_type=edit_type,
    )


@mastersetup_bp.route("/master/municipality-type/<int:type_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def delete_municipality_type(type_id):
    with engine.begin() as conn:
        referenced = conn.execute(
            select(municipality).where(municipality.c.municipalitytypeid == type_id)
        ).mappings().first()
        if referenced:
            flash("Cannot delete municipality type because municipalities are assigned to it.", "danger")
            return redirect(url_for("mastersetup.manage_municipality_type"))

        conn.execute(delete(municipalitytype).where(municipalitytype.c.municipalitytypeid == type_id))
        flash("Municipality type deleted successfully.", "success")

    return redirect(url_for("mastersetup.manage_municipality_type"))


@mastersetup_bp.route("/master/municipality", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def manage_municipality():
    field_errors = {}
    form_data = {"districtid": None, "municipalitytypeid": None, "municipalityname": ""}

    with engine.connect() as conn:
        district_options = _load_districts_with_hierarchy(conn)
        municipality_type_options = _load_municipality_types(conn)
        municipality_rows = _load_municipalities_with_hierarchy(conn)

    if request.method == "POST":
        form_data["districtid"] = request.form.get("districtid", type=int)
        form_data["municipalitytypeid"] = request.form.get("municipalitytypeid", type=int)
        form_data["municipalityname"] = request.form.get("municipalityname", "").strip()

        if not form_data["districtid"]:
            field_errors["districtid"] = "District selection is required."
        if not form_data["municipalitytypeid"]:
            field_errors["municipalitytypeid"] = "Municipality type selection is required."
        if not form_data["municipalityname"]:
            field_errors["municipalityname"] = "Municipality name is required."

        if not field_errors:
            try:
                with engine.begin() as conn:
                    existing = conn.execute(
                        select(municipality)
                        .where(municipality.c.municipalityname.ilike(form_data["municipalityname"]))
                        .where(municipality.c.districtid == form_data["districtid"])
                        .where(municipality.c.municipalitytypeid == form_data["municipalitytypeid"])
                    ).mappings().first()
                    if existing:
                        field_errors["municipalityname"] = "Municipality already exists for the selected district and type."
                    else:
                        conn.execute(
                            insert(municipality).values(
                                districtid=form_data["districtid"],
                                municipalitytypeid=form_data["municipalitytypeid"],
                                municipalityname=form_data["municipalityname"],
                            )
                        )
                        flash("Municipality added successfully.", "success")
                        return redirect(url_for("mastersetup.manage_municipality"))
            except IntegrityError:
                field_errors["municipalityname"] = "Municipality could not be added due to duplicate or integrity issue."
            except Exception as exc:
                field_errors["municipalityname"] = f"Unable to add municipality: {exc}"

    return render_template(
        "municipality.html",
        municipality_rows=municipality_rows,
        district_options=district_options,
        municipality_type_options=municipality_type_options,
        form_data=form_data,
        field_errors=field_errors,
        edit_municipality=None,
    )


@mastersetup_bp.route("/master/municipality/<int:municipality_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_municipality(municipality_id):
    field_errors = {}
    edit_municipality = None
    form_data = {"districtid": None, "municipalitytypeid": None, "municipalityname": ""}

    with engine.begin() as conn:
        edit_municipality = conn.execute(
            select(municipality).where(municipality.c.municipalityid == municipality_id)
        ).mappings().first()
        if not edit_municipality:
            flash("Municipality not found.", "danger")
            return redirect(url_for("mastersetup.manage_municipality"))

        form_data["districtid"] = edit_municipality["districtid"]
        form_data["municipalitytypeid"] = edit_municipality["municipalitytypeid"]
        form_data["municipalityname"] = edit_municipality["municipalityname"]

        if request.method == "POST":
            form_data["districtid"] = request.form.get("districtid", type=int)
            form_data["municipalitytypeid"] = request.form.get("municipalitytypeid", type=int)
            form_data["municipalityname"] = request.form.get("municipalityname", "").strip()

            if not form_data["districtid"]:
                field_errors["districtid"] = "District selection is required."
            if not form_data["municipalitytypeid"]:
                field_errors["municipalitytypeid"] = "Municipality type selection is required."
            if not form_data["municipalityname"]:
                field_errors["municipalityname"] = "Municipality name is required."

            existing = conn.execute(
                select(municipality)
                .where(municipality.c.municipalityname.ilike(form_data["municipalityname"]))
                .where(municipality.c.districtid == form_data["districtid"])
                .where(municipality.c.municipalitytypeid == form_data["municipalitytypeid"])
                .where(municipality.c.municipalityid != municipality_id)
            ).mappings().first()
            if existing:
                field_errors["municipalityname"] = "Municipality already exists for the selected district and type."

            if not field_errors:
                conn.execute(
                    update(municipality)
                    .where(municipality.c.municipalityid == municipality_id)
                    .values(
                        districtid=form_data["districtid"],
                        municipalitytypeid=form_data["municipalitytypeid"],
                        municipalityname=form_data["municipalityname"],
                    )
                )
                flash("Municipality updated successfully.", "success")
                return redirect(url_for("mastersetup.manage_municipality"))

    with engine.connect() as conn:
        district_options = _load_districts_with_hierarchy(conn)
        municipality_type_options = _load_municipality_types(conn)
        municipality_rows = _load_municipalities_with_hierarchy(conn)

    return render_template(
        "municipality.html",
        municipality_rows=municipality_rows,
        district_options=district_options,
        municipality_type_options=municipality_type_options,
        form_data=form_data,
        field_errors=field_errors,
        edit_municipality=edit_municipality,
    )


@mastersetup_bp.route("/master/municipality/<int:municipality_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def delete_municipality(municipality_id):
    with engine.begin() as conn:
        conn.execute(delete(municipality).where(municipality.c.municipalityid == municipality_id))
        flash("Municipality deleted successfully.", "success")

    return redirect(url_for("mastersetup.manage_municipality"))
