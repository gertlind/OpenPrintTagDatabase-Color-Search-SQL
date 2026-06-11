from flask import Flask, render_template, request
from pathlib import Path
import sqlite3
import json

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
SQLITE_DB = BASE_DIR / "optd.db"


def normalize_hex(value):
    if not value:
        return ""

    value = str(value).strip().lower()

    if not value.startswith("#"):
        value = "#" + value

    if len(value) == 7:
        value += "ff"

    return value


def db_connect():
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_database_stats():
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM filaments")
    filaments = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT brand) FROM filaments WHERE brand != ''")
    brands = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT material) FROM filaments WHERE material != ''")
    materials = cur.fetchone()[0]

    conn.close()

    return {
        "brands": brands,
        "materials": materials,
        "filaments": filaments,
    }


def search_filaments(
    manufacturer="",
    country="",
    material="",
    name="",
    color=""
):
    query = """
        SELECT *
        FROM filaments
        WHERE 1=1
    """

    params = []

    if manufacturer:
        query += " AND brand LIKE ?"
        params.append(f"%{manufacturer}%")

    if country:
        query += " AND country LIKE ?"
        params.append(f"%{country.upper()}%")

    if material:
        query += " AND material LIKE ?"
        params.append(f"%{material}%")

    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")

    if color:
        query += " AND color = ?"
        params.append(normalize_hex(color))

    query += " ORDER BY brand, name"

    conn = db_connect()
    cur = conn.cursor()
    cur.execute(query, params)

    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.route("/", methods=["GET"])
def index():
    manufacturer = request.args.get("manufacturer", "").strip()
    country = request.args.get("country", "").strip()
    material = request.args.get("material", "").strip()
    name = request.args.get("name", "").strip()
    color = request.args.get("color", "").strip()

    results = []

    if manufacturer or country or material or name or color:
        results = search_filaments(
            manufacturer=manufacturer,
            country=country,
            material=material,
            name=name,
            color=color
        )

    stats = get_database_stats()

    return render_template(
        "index.html",
        results=results,
        manufacturer=manufacturer,
        country=country,
        material=material,
        name=name,
        color=color,
        stats=stats
    )


@app.route("/properties/<int:filament_id>")
def properties_page(filament_id):
    return_query = request.args.get("return_query", "")

    conn = db_connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM filaments WHERE id = ?",
        (filament_id,)
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return "Filament hittades inte", 404

    item = dict(row)

    properties = json.loads(item.get("properties_json") or "{}")

    if not properties:
        return "Inga properties finns för detta filament", 404

    return render_template(
        "properties.html",
        brand=item.get("brand", ""),
        name=item.get("name", ""),
        color=item.get("color", ""),
        photo=item.get("photo", ""),
        properties=properties,
        return_query=return_query
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)