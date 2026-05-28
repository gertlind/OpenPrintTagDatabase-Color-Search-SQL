import sqlite3
from pathlib import Path
import yaml
import json

# Folder där OpenPrintTag-databasen ligger
DB_SOURCE = Path("openprinttag-database/data/materials")

# SQLite-fil
SQLITE_DB = "optd.db"


def normalize_hex(value):
    if not value:
        return ""

    value = str(value).strip().lower()

    if not value.startswith("#"):
        value = "#" + value

    if len(value) == 7:
        value += "ff"

    return value


def get_brand(item):
    brand = ""

    if isinstance(item.get("brand"), dict):
        brand = item["brand"].get("slug", "")

    if not brand:
        brand = item.get("brand", "")

    if isinstance(brand, str):
        brand = brand.replace("-", " ").title()

    return brand


def get_material(item):
    material = (
        item.get("type")
        or item.get("abbreviation")
        or ""
    )

    return str(material).strip().upper()


def get_name(item):
    return (
        item.get("name")
        or item.get("display_name")
        or item.get("title")
        or ""
    )


def get_color_hex(item):
    if isinstance(item.get("primary_color"), dict):
        if item["primary_color"].get("color_rgba"):
            return normalize_hex(
                item["primary_color"].get("color_rgba")
            )

    return ""


def get_photo(item):
    photos = item.get("photos")

    if isinstance(photos, list) and photos:
        first = photos[0]

        if isinstance(first, dict):
            return first.get("url", "")

    return ""


def get_url(item):

    for key in [
        "url",
        "website",
        "link",
        "productUrl",
        "product_url"
    ]:
        if item.get(key):
            return item.get(key)

    urls = item.get("urls")

    if isinstance(urls, dict):
        for value in urls.values():
            if value:
                return value

    if isinstance(urls, list):
        for value in urls:
            if value:
                return value

    return ""


print("Creating SQLite database...")

conn = sqlite3.connect(SQLITE_DB)
cursor = conn.cursor()

# Ta bort gammal tabell
cursor.execute("DROP TABLE IF EXISTS filaments")

# Skapa tabell
cursor.execute("""
CREATE TABLE filaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT,
    material TEXT,
    name TEXT,
    color TEXT,
    photo TEXT,
    url TEXT,
    yaml_file TEXT,
    properties_json TEXT,
    has_properties INTEGER
)
""")

count = 0

files = list(DB_SOURCE.rglob("*.yaml"))

for file in files:

    try:
        with open(file, "r", encoding="utf-8") as f:
            item = yaml.safe_load(f)

        if not isinstance(item, dict):
            continue

        brand = get_brand(item)
        material = get_material(item)
        name = get_name(item)
        color = get_color_hex(item)
        photo = get_photo(item)
        url = get_url(item)

        properties = item.get("properties", {})

        cursor.execute("""
        INSERT INTO filaments (
            brand,
            material,
            name,
            color,
            photo,
            url,
            yaml_file,
            properties_json,
            has_properties
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            brand,
            material,
            name,
            color,
            photo,
            url,
            str(file.relative_to(DB_SOURCE)),
            json.dumps(properties),
            1 if properties else 0
        ))

        count += 1

        if count % 500 == 0:
            print(f"{count} imported...")

    except Exception as e:
        print(f"ERROR: {file}")
        print(e)

conn.commit()

# Index för snabb sökning
cursor.execute(
    "CREATE INDEX idx_brand ON filaments(brand)"
)

cursor.execute(
    "CREATE INDEX idx_material ON filaments(material)"
)

cursor.execute(
    "CREATE INDEX idx_name ON filaments(name)"
)

cursor.execute(
    "CREATE INDEX idx_color ON filaments(color)"
)

conn.commit()
conn.close()

print()
print(f"Done.")
print(f"Imported {count} filaments.")
print(f"SQLite database: {SQLITE_DB}")
