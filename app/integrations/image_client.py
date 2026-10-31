"""Generacion de imagenes con Pollinations (gratuito). Si falla, crea una imagen de respaldo."""
import hashlib
import io
import os
import time
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = os.getenv("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def _size():
    return int(os.getenv("IMAGE_WIDTH", "768")), int(os.getenv("IMAGE_HEIGHT", "1344"))


def _from_ai(prompt, dest_path, seed):
    """Pide la imagen a Pollinations.

    Sin clave usa la API clasica gratuita (sin registro, con una marca pequena de Pollinations).
    Con POLLINATIONS_API_KEY usa la API con cuenta (enter.pollinations.ai), que consume el saldo "pollen".
    """
    width, height = _size()
    full_prompt = f"{prompt}, vertical composition, professional advertising photo, no text, no watermark"
    key = os.getenv("POLLINATIONS_API_KEY", "").strip()

    params = {"width": width, "height": height, "seed": seed}
    headers = {}
    if key:
        base = "https://gen.pollinations.ai/image"
        headers["Authorization"] = f"Bearer {key}"
    else:
        base = "https://image.pollinations.ai/prompt"
    model = os.getenv("POLLINATIONS_MODEL", "").strip()
    if model:
        params["model"] = model
    url = f"{base}/{quote(full_prompt, safe='')}"

    last = None
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=120)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img.save(dest_path, "JPEG", quality=90)
                time.sleep(3)  # pausa corta entre imagenes para no saturar el servicio gratuito
                return True
            last = f"HTTP {resp.status_code}"
            if resp.status_code in (401, 402, 403):
                # Problema de clave o saldo: reintentar no sirve
                last += " (se requiere clave o saldo: ver POLLINATIONS_API_KEY)"
                break
        except (requests.RequestException, OSError) as e:
            last = str(e)
        time.sleep(3 * (attempt + 1))
    print(f"[image_client] no se pudo generar con IA: {last}", flush=True)
    return False


def _fallback(dest_path, seed, label):
    """Degradado con un aviso visible. Evita que todo el flujo falle si el servicio de IA no responde."""
    width, height = _size()
    h = hashlib.sha256(str(seed).encode()).digest()
    top = (30 + h[0] % 80, 40 + h[1] % 80, 90 + h[2] % 120)
    bottom = (20 + h[3] % 60, 20 + h[4] % 60, 40 + h[5] % 80)
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        draw.line([(0, y), (width, y)], fill=tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)))
    try:
        font = ImageFont.truetype(FONT_PATH, max(24, width // 18))
    except OSError:
        font = ImageFont.load_default()
    for i, line in enumerate([label[:28], "Imagen de respaldo", "(IA no disponible)"]):
        w = draw.textlength(line, font=font)
        draw.text(((width - w) / 2, height * 0.45 + i * (width // 14)), line, fill=(255, 255, 255), font=font)
    img.save(dest_path, "JPEG", quality=90)


def generate_image(prompt, dest_path, seed, label="Campaña"):
    """Devuelve 'ia' si la imagen la genero el servicio, o 'respaldo' si se uso la imagen de respaldo."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if _from_ai(prompt, dest_path, seed):
        return "ia"
    _fallback(dest_path, seed, label)
    return "respaldo"
