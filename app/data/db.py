"""Capa de acceso a datos: conexion y esquema."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    business_name TEXT NOT NULL,
    industry TEXT NOT NULL,
    notes TEXT,
    photo_file TEXT NOT NULL,
    photo_description TEXT,
    status TEXT NOT NULL DEFAULT 'guiones_listos',
    chosen_script_id INT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS scripts (
    id SERIAL PRIMARY KEY,
    campaign_id INT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    position INT NOT NULL,
    title TEXT NOT NULL,
    hook TEXT,
    body TEXT,
    cta TEXT,
    caption TEXT,
    scenes JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    campaign_id INT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('imagen', 'video')),
    file TEXT NOT NULL,
    source TEXT NOT NULL,
    position INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    campaign_id INT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    network TEXT NOT NULL,
    caption TEXT NOT NULL,
    status TEXT NOT NULL,
    external_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
"""


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        cursor_factory=RealDictCursor,
    )


def init_db():
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(SCHEMA)
    finally:
        conn.close()
