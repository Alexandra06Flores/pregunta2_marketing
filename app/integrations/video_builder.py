"""Arma el video vertical 9:16 a partir de las 3 imagenes usando ffmpeg."""
import os
import subprocess
import tempfile
import textwrap

from app.integrations import IntegrationError

FONT_PATH = os.getenv("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FPS = 25


def _run(cmd):
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        raise IntegrationError("ffmpeg no está instalado en el contenedor")
    except subprocess.TimeoutExpired:
        raise IntegrationError("ffmpeg tardó demasiado en armar el video")
    except subprocess.CalledProcessError as e:
        raise IntegrationError(f"ffmpeg falló: {e.stderr[-400:]}")


def build_video(image_paths, texts, out_path, seconds_per_scene=4):
    """Une las imagenes con zoom suave y un texto por escena. Devuelve la ruta del video."""
    frames = seconds_per_scene * FPS
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        segments = []
        for i, (img, text) in enumerate(zip(image_paths, texts), start=1):
            text_file = os.path.join(tmp, f"t{i}.txt")
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(textwrap.fill(text, width=22))

            vf = (
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                f"zoompan=z='min(zoom+0.0015,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={frames}:s=1080x1920:fps={FPS},"
                f"drawtext=fontfile={FONT_PATH}:textfile={text_file}:fontcolor=white:fontsize=64"
                ":line_spacing=12:box=1:boxcolor=black@0.55:boxborderw=26"
                ":x=(w-text_w)/2:y=h*0.70,format=yuv420p"
            )
            seg = os.path.join(tmp, f"seg{i}.mp4")
            _run([
                "ffmpeg", "-y", "-i", img, "-vf", vf, "-frames:v", str(frames),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-r", str(FPS), seg,
            ])
            segments.append(seg)

        list_file = os.path.join(tmp, "list.txt")
        with open(list_file, "w") as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")

        # Pista de audio silenciosa: algunas redes esperan que el video tenga audio
        _run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", out_path,
        ])
    return out_path
