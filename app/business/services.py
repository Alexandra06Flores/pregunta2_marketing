"""Capa de logica de negocio: flujo de la campaña y reglas."""
import os
import uuid

from PIL import Image, UnidentifiedImageError

from app.config import media_dir
from app.data import repositories as repo
from app.integrations import groq_client, image_client, video_builder, publisher

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def _save_photo(file_storage):
    """Valida que sea una imagen real y la guarda como JPEG. Devuelve la ruta relativa."""
    if not file_storage or not file_storage.filename:
        raise ValueError("Sube una foto del producto o del local")
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("La foto debe ser JPG, PNG o WEBP")
    try:
        img = Image.open(file_storage.stream)
        img.load()
    except (UnidentifiedImageError, OSError):
        raise ValueError("El archivo no es una imagen válida")
    img = img.convert("RGB")
    img.thumbnail((2048, 2048))
    rel = f"photos/{uuid.uuid4().hex}.jpg"
    path = os.path.join(media_dir(), rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=90)
    return rel


def create_campaign(business_name, industry, notes, photo):
    business_name = (business_name or "").strip()
    industry = (industry or "").strip()
    notes = (notes or "").strip()
    if not business_name or not industry:
        raise ValueError("Escribe el nombre y el rubro del negocio")

    rel = _save_photo(photo)
    try:
        result = groq_client.generate_scripts(os.path.join(media_dir(), rel), business_name, industry, notes)
        return repo.create_campaign(
            business_name, industry, notes, rel, result["photo_description"], result["scripts"]
        )
    except Exception:
        # Si algo falla, no dejamos la foto huérfana en el disco
        try:
            os.remove(os.path.join(media_dir(), rel))
        except OSError:
            pass
        raise


def list_campaigns():
    return repo.list_campaigns()


def get_campaign_detail(campaign_id):
    campaign = repo.get_campaign(campaign_id)
    if not campaign:
        raise ValueError("La campaña no existe")
    assets = repo.get_assets(campaign_id)
    images = [a for a in assets if a["kind"] == "imagen"]
    videos = [a for a in assets if a["kind"] == "video"]
    video = videos[0] if videos else None
    checks = publisher.reels_checks(os.path.join(media_dir(), video["file"])) if video else []
    return {
        "campaign": campaign,
        "scripts": repo.get_scripts(campaign_id),
        "images": images,
        "video": video,
        "checks": checks,
        "posts": repo.get_posts(campaign_id),
    }


def choose_script(campaign_id, script_id):
    campaign = repo.get_campaign(campaign_id)
    if not campaign:
        raise ValueError("La campaña no existe")
    if campaign["status"] not in ("guiones_listos", "guion_elegido"):
        raise ValueError("Esta campaña ya generó su material, no se puede cambiar el guion")
    if script_id not in [s["id"] for s in repo.get_scripts(campaign_id)]:
        raise ValueError("Ese guion no pertenece a la campaña")
    repo.choose_script(campaign_id, script_id)


def generate_media(campaign_id):
    campaign = repo.get_campaign(campaign_id)
    if not campaign:
        raise ValueError("La campaña no existe")
    if not campaign["chosen_script_id"]:
        raise ValueError("Primero elige uno de los 3 guiones")
    if campaign["status"] not in ("guion_elegido", "material_listo"):
        raise ValueError("El material de esta campaña ya fue generado y publicado")

    script = next(s for s in repo.get_scripts(campaign_id) if s["id"] == campaign["chosen_script_id"])
    scenes = script["scenes"]
    folder = f"campaigns/{campaign_id}"

    image_rels, assets = [], []
    for i, scene in enumerate(scenes, start=1):
        rel = f"{folder}/img_{i}.jpg"
        source = image_client.generate_image(
            scene["image_prompt"], os.path.join(media_dir(), rel),
            seed=campaign_id * 10 + i, label=campaign["business_name"],
        )
        image_rels.append(rel)
        assets.append({"kind": "imagen", "file": rel, "source": source, "position": i})

    # En la última escena se muestra el llamado a la acción si es corto
    texts = [s["overlay_text"] for s in scenes]
    if script["cta"] and len(script["cta"]) <= 60:
        texts[-1] = script["cta"]

    video_rel = f"{folder}/video.mp4"
    video_builder.build_video([os.path.join(media_dir(), r) for r in image_rels], texts,
                              os.path.join(media_dir(), video_rel))
    assets.append({"kind": "video", "file": video_rel, "source": "ffmpeg", "position": 1})

    repo.replace_assets(campaign_id, assets)
    repo.set_status(campaign_id, "material_listo")


def publish(campaign_id, network):
    campaign = repo.get_campaign(campaign_id)
    if not campaign:
        raise ValueError("La campaña no existe")
    if campaign["status"] not in ("material_listo", "publicado_simulado"):
        raise ValueError("Primero genera las fotos y el video")
    script = next(s for s in repo.get_scripts(campaign_id) if s["id"] == campaign["chosen_script_id"])
    video = next(a for a in repo.get_assets(campaign_id) if a["kind"] == "video")

    result = publisher.publish(network, os.path.join(media_dir(), video["file"]), script["caption"])
    repo.create_post(campaign_id, network, script["caption"], result["status"], result["external_id"])
    repo.set_status(campaign_id, "publicado_simulado")
