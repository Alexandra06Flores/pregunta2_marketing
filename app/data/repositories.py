"""Capa de acceso a datos: consultas SQL."""
from psycopg2.extras import Json
from app.data.db import get_conn


def _run(sql, params=None, fetch=False):
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if fetch else None
    finally:
        conn.close()


def create_campaign(business_name, industry, notes, photo_file, photo_description, scripts):
    """Guarda la campana y sus 3 guiones en una sola transaccion. Devuelve el id."""
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO campaigns (business_name, industry, notes, photo_file, photo_description)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (business_name, industry, notes, photo_file, photo_description),
            )
            campaign_id = cur.fetchone()["id"]
            for pos, s in enumerate(scripts, start=1):
                cur.execute(
                    """INSERT INTO scripts (campaign_id, position, title, hook, body, cta, caption, scenes)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (campaign_id, pos, s["title"], s["hook"], s["body"], s["cta"], s["caption"], Json(s["scenes"])),
                )
            return campaign_id
    finally:
        conn.close()


def list_campaigns():
    return _run("SELECT * FROM campaigns ORDER BY created_at DESC, id DESC", fetch=True)


def get_campaign(campaign_id):
    rows = _run("SELECT * FROM campaigns WHERE id = %s", (campaign_id,), fetch=True)
    return rows[0] if rows else None


def get_scripts(campaign_id):
    return _run("SELECT * FROM scripts WHERE campaign_id = %s ORDER BY position", (campaign_id,), fetch=True)


def choose_script(campaign_id, script_id):
    _run(
        "UPDATE campaigns SET chosen_script_id = %s, status = 'guion_elegido' WHERE id = %s",
        (script_id, campaign_id),
    )


def set_status(campaign_id, status):
    _run("UPDATE campaigns SET status = %s WHERE id = %s", (status, campaign_id))


def replace_assets(campaign_id, assets):
    """assets: lista de dicts con kind, file, source, position."""
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM assets WHERE campaign_id = %s", (campaign_id,))
            for a in assets:
                cur.execute(
                    "INSERT INTO assets (campaign_id, kind, file, source, position) VALUES (%s, %s, %s, %s, %s)",
                    (campaign_id, a["kind"], a["file"], a["source"], a["position"]),
                )
    finally:
        conn.close()


def get_assets(campaign_id):
    return _run("SELECT * FROM assets WHERE campaign_id = %s ORDER BY kind DESC, position", (campaign_id,), fetch=True)


def create_post(campaign_id, network, caption, status, external_id):
    _run(
        "INSERT INTO posts (campaign_id, network, caption, status, external_id) VALUES (%s, %s, %s, %s, %s)",
        (campaign_id, network, caption, status, external_id),
    )


def get_posts(campaign_id):
    return _run("SELECT * FROM posts WHERE campaign_id = %s ORDER BY created_at DESC, id DESC", (campaign_id,), fetch=True)
