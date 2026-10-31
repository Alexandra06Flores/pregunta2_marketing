"""Publicación en redes sociales: SIMULADA.

Esta clase NO envía nada a Instagram ni a TikTok. Registra la publicación como "SIMULADO"
y entrega una verificacion tecnica del video. Para publicar de verdad en Instagram haria
falta una cuenta profesional vinculada a una pagina de Facebook, una app en Meta for
Developers y el permiso instagram_business_content_publish. El flujo real consiste en crear
un contenedor de medios (POST /{ig-user-id}/media) y luego publicarlo
(POST /{ig-user-id}/media_publish). Ver README.
"""
import json
import subprocess
import uuid

SUPPORTED_NETWORKS = ("Instagram", "TikTok")


def probe_video(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True, timeout=60, check=True,
    ).stdout
    data = json.loads(out)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    return {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "codec": video["codec_name"],
        "duration": float(data["format"]["duration"]),
    }


def reels_checks(path):
    """Verificacion tecnica del video (formato vertical, codec y duracion). Devuelve lista de (texto, ok)."""
    try:
        info = probe_video(path)
    except (OSError, subprocess.SubprocessError, StopIteration, KeyError, ValueError):
        return [("No se pudo leer el video", False)]
    return [
        (f"Resolucion {info['width']}x{info['height']} (vertical 9:16)",
         abs(info["width"] / info["height"] - 9 / 16) < 0.01),
        (f"Codec {info['codec']} (H.264)", info["codec"] == "h264"),
        (f"Duracion {info['duration']:.1f} s (entre 5 y 90 s)", 5 <= info["duration"] <= 90),
    ]


def publish(network, video_path, caption):
    if network not in SUPPORTED_NETWORKS:
        raise ValueError("Red social no válida")
    return {"status": "SIMULADO", "external_id": "sim_" + uuid.uuid4().hex[:10]}
