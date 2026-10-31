"""Capa de presentacion: rutas y vistas."""
from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   send_from_directory, abort)
from app.business import services
from app.config import media_dir
from app.integrations import IntegrationError
from app.integrations.publisher import SUPPORTED_NETWORKS

bp = Blueprint("main", __name__, template_folder="templates")

STATUS_LABELS = {
    "guiones_listos": "Guiones listos",
    "guion_elegido": "Guion elegido",
    "material_listo": "Fotos y video listos",
    "publicado_simulado": "Publicado (simulado)",
}


@bp.app_context_processor
def inject_globals():
    return {"STATUS_LABELS": STATUS_LABELS, "NETWORKS": SUPPORTED_NETWORKS}


@bp.route("/")
def index():
    return render_template("index.html", campaigns=services.list_campaigns())


@bp.route("/nueva", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        try:
            cid = services.create_campaign(
                request.form.get("business_name"), request.form.get("industry"),
                request.form.get("notes"), request.files.get("photo"),
            )
            flash("Listo, la IA propuso 3 guiones. Elige el que más te guste.", "ok")
            return redirect(url_for("main.campaign", cid=cid))
        except (ValueError, IntegrationError) as e:
            flash(str(e), "error")
    return render_template("new.html")


@bp.route("/campana/<int:cid>")
def campaign(cid):
    try:
        detail = services.get_campaign_detail(cid)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("main.index"))
    return render_template("campaign.html", **detail)


@bp.route("/campana/<int:cid>/elegir/<int:sid>", methods=["POST"])
def choose(cid, sid):
    try:
        services.choose_script(cid, sid)
        flash("Guion elegido. Ahora puedes generar las fotos y el video.", "ok")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("main.campaign", cid=cid))


@bp.route("/campana/<int:cid>/generar", methods=["POST"])
def generate(cid):
    try:
        services.generate_media(cid)
        flash("Fotos y video generados.", "ok")
    except (ValueError, IntegrationError) as e:
        flash(str(e), "error")
    return redirect(url_for("main.campaign", cid=cid))


@bp.route("/campana/<int:cid>/publicar", methods=["POST"])
def publish(cid):
    try:
        services.publish(cid, request.form.get("network", ""))
        flash("Publicación SIMULADA registrada. No se envió nada a la red social.", "ok")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("main.campaign", cid=cid))


@bp.route("/media/<path:filename>")
def media(filename):
    try:
        return send_from_directory(media_dir(), filename)
    except Exception:
        abort(404)
