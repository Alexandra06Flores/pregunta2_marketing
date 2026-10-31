# Marketing con IA para empresas

Aplicación web que recibe la foto de un producto o local y arma una campaña para redes sociales:

1. El sistema recibe una foto.
2. Una IA propone 3 guiones.
3. Se elige uno de ellos.
4. El sistema genera 3 fotos y un video vertical.
5. Se publica en una red social (Instagram o TikTok). **La publicación es SIMULADA** (ver más abajo).

## Arquitectura

```
Navegador
   |
   v
[Presentación]       app/presentation   rutas Flask y plantillas HTML
   |
   v
[Lógica de negocio]  app/business       reglas del flujo de la campaña
   |            \
   |             \--> app/integrations   Groq (guiones), Pollinations (imágenes),
   v                                     ffmpeg (video), publicador simulado
[Acceso a datos]     app/data           SQL con psycopg2
   |
   v
PostgreSQL (volumen pgdata)        Archivos generados (volumen media)
```

Servicios de docker-compose:
- **web**: aplicación Flask (gunicorn), publicada en el puerto 8080.
- **db**: PostgreSQL 16 con el volumen `pgdata`.
- Volumen `media`: guarda la foto original, las 3 fotos generadas y el video.

## Qué hace cada servicio externo

| Paso | Servicio | Detalle |
|---|---|---|
| Entender la foto y escribir 3 guiones | Groq, modelo `meta-llama/llama-4-scout-17b-16e-instruct` (visión) | Plan gratuito, requiere API key |
| Generar 3 fotos | Pollinations (FLUX) | Gratuito. Si no responde, se crea una imagen de respaldo señalada en pantalla |
| Armar el video | ffmpeg dentro del contenedor | Video vertical 1080x1920, 12 s, H.264, zoom suave y texto por escena |
| Publicar | Simulado | No se envía nada a ninguna red social |

## Publicación simulada

La aplicación **no publica** en Instagram ni en TikTok. Al presionar "Publicar (simulado)" se registra
la publicación en la base de datos con estado `SIMULADO` y se muestra una verificación técnica del video
(formato vertical 9:16, códec H.264 y duración).

Para publicar de verdad en Instagram se necesitaría una cuenta profesional vinculada a una página de
Facebook, una app en Meta for Developers y el permiso `instagram_business_content_publish`.
La publicación se hace en dos pasos: crear un contenedor de medios (`POST /{ig-user-id}/media`) y
publicarlo (`POST /{ig-user-id}/media_publish`).
En TikTok, las apps sin auditar solo pueden publicar en modo privado.

## Variables de entorno

Copiar `.env.example` a `.env` y completar:

| Variable | Descripción |
|---|---|
| DOCKERHUB_USER | Usuario de Docker Hub para nombrar la imagen |
| DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD | Conexión a PostgreSQL |
| GROQ_API_KEY | Clave de Groq (obligatoria) |
| GROQ_MODEL | Modelo de visión de Groq |
| IMAGE_API_URL, IMAGE_MODEL, IMAGE_WIDTH, IMAGE_HEIGHT | Generación de imágenes |
| POLLINATIONS_API_KEY | Opcional |
| MEDIA_DIR | Carpeta donde se guardan los archivos (volumen) |
| SECRET_KEY | Clave de sesión de Flask |

El archivo `.env` no se sube al repositorio.

## Ejecución local

```
cp .env.example .env
# editar .env y pegar GROQ_API_KEY
docker compose up -d --build
```
Abrir http://localhost:8080

## Publicar la imagen en Docker Hub

```
docker login
docker compose build
docker compose push web
```

## Despliegue en AWS EC2

1. Instancia EC2 Ubuntu con Docker y Docker Compose instalados.
2. En el grupo de seguridad, abrir el puerto 8080 (TCP, origen 0.0.0.0/0) además del 22.
3. Clonar el repositorio y crear el `.env`:
   ```
   git clone <URL_DEL_REPOSITORIO>
   cd marketing
   cp .env.example .env
   nano .env
   ```
4. Levantar los servicios:
   ```
   docker compose up -d --build
   docker ps
   ```
5. Abrir `http://<IP_PUBLICA_DE_LA_EC2>:8080`

## Persistencia

Los datos de PostgreSQL se guardan en el volumen `pgdata` y los archivos generados en el volumen `media`.
```
docker compose down
docker compose up -d
```
Las campañas, el video y las fotos siguen disponibles. No usar `docker compose down -v`, porque borra los volúmenes.

## Referencias

- Groq, visión: https://console.groq.com/docs/vision
- Pollinations: https://pollinations.ai
- Instagram, publicación de contenido: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing
- TikTok, guías de publicación: https://developers.tiktok.com/doc/content-sharing-guidelines
