"""Groq: analiza la foto (modelo de vision) y propone 3 guiones."""
import base64
import io
import json
import os
import re

import requests
from PIL import Image

from app.integrations import IntegrationError

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SCHEMA = """{
  "photo_description": "que se ve en la foto, 1 o 2 frases",
  "scripts": [
    {
      "title": "nombre corto del enfoque",
      "hook": "frase de apertura que atrapa",
      "body": "desarrollo del guion en 2 o 3 frases",
      "cta": "llamado a la acción corto",
      "caption": "texto de la publicación con 3 a 5 hashtags",
      "scenes": [
        {"image_prompt": "...", "overlay_text": "..."},
        {"image_prompt": "...", "overlay_text": "..."},
        {"image_prompt": "...", "overlay_text": "..."}
      ]
    }
  ]
}"""


def _prepare_image(path):
    """Reduce la foto para respetar el limite de Groq para imagenes en base64 (4 MB)."""
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((1024, 1024))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _build_prompt(business_name, industry, notes):
    return (
        f"Negocio: {business_name}\n"
        f"Rubro: {industry}\n"
        f"Notas del dueño: {notes or 'ninguna'}\n\n"
        "Analiza la foto adjunta (producto o local de este negocio) y crea una campaña "
        "corta para redes sociales: un video vertical de 12 segundos con 3 escenas.\n"
        "Devuelve SOLO un objeto JSON con esta estructura:\n"
        f"{SCHEMA}\n\n"
        "Reglas:\n"
        "- Exactamente 3 guiones, con enfoques distintos (por ejemplo emocional, promocional, informativo).\n"
        "- Cada guion tiene exactamente 3 escenas.\n"
        "- Todos los textos en español, excepto image_prompt que va en inglés.\n"
        "- image_prompt describe una foto publicitaria realista del producto o servicio, sin texto ni logos.\n"
        "- overlay_text tiene maximo 8 palabras.\n"
        "- No inventes precios, descuentos ni datos que no se vean en la foto o en las notas."
    )


def _extract_json(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("La respuesta no contiene JSON")
    return json.loads(text[start:end + 1])


def _validate(data):
    """Normaliza y valida la respuesta del modelo."""
    scripts = data.get("scripts")
    if not isinstance(scripts, list) or len(scripts) < 3:
        raise ValueError("El modelo no devolvió 3 guiones")
    clean = []
    for s in scripts[:3]:
        scenes = s.get("scenes")
        if not isinstance(scenes, list) or len(scenes) < 3:
            raise ValueError("Un guion no trae 3 escenas")
        clean_scenes = []
        for sc in scenes[:3]:
            prompt = str(sc.get("image_prompt", "")).strip()
            overlay = str(sc.get("overlay_text", "")).strip()
            if not prompt or not overlay:
                raise ValueError("Una escena está incompleta")
            clean_scenes.append({"image_prompt": prompt[:400], "overlay_text": overlay[:70]})
        title = str(s.get("title", "")).strip()
        if not title:
            raise ValueError("Un guion no tiene titulo")
        clean.append({
            "title": title[:120],
            "hook": str(s.get("hook", "")).strip(),
            "body": str(s.get("body", "")).strip(),
            "cta": str(s.get("cta", "")).strip(),
            "caption": str(s.get("caption", "")).strip(),
            "scenes": clean_scenes,
        })
    return {"photo_description": str(data.get("photo_description", "")).strip(), "scripts": clean}


def generate_scripts(photo_path, business_name, industry, notes=""):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key.startswith("pega_"):
        raise IntegrationError("Falta configurar GROQ_API_KEY en el archivo .env")
    model = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

    payload = {
        "model": model,
        "temperature": 0.8,
        "max_tokens": 3500,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": _build_prompt(business_name, industry, notes)},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + _prepare_image(photo_path)}},
            ],
        }],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    last_error = None
    for _ in range(2):  # un reintento si el JSON viene mal formado
        try:
            resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=90)
        except requests.RequestException as e:
            raise IntegrationError(f"No se pudo conectar con Groq: {e}")

        if resp.status_code == 401:
            raise IntegrationError("La clave de Groq no es válida (error 401)")
        if resp.status_code == 429:
            raise IntegrationError("Se alcanzó el límite gratuito de Groq. Espera un minuto e intenta de nuevo")
        if resp.status_code >= 400:
            raise IntegrationError(f"Groq respondio con error {resp.status_code}: {resp.text[:300]}")

        try:
            content = resp.json()["choices"][0]["message"]["content"]
            return _validate(_extract_json(content))
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
            last_error = e
    raise IntegrationError(f"Groq devolvió una respuesta que no se pudo interpretar: {last_error}")
