FROM python:3.12-slim

# ffmpeg arma el video y las fuentes DejaVu se usan para los textos del video
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data/media

EXPOSE 5000

# Un solo worker con hilos: la app crea las tablas al iniciar y generar el video puede tardar
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "300", "run:app"]
