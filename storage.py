import sqlite3
import json
import os

# DB-Verbindung persistent im Volume speichern
DB_PATH = "/mnt/data/exports.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# Tabelle erstellen, falls sie noch nicht existiert
c.execute("""
CREATE TABLE IF NOT EXISTS exports (
    guild_id TEXT PRIMARY KEY,
    data TEXT
)
""")
conn.commit()

async def save_export(guild_id, data):
    try:
        json_str = json.dumps(data)
        c.execute(
            "INSERT OR REPLACE INTO exports (guild_id, data) VALUES (?, ?)",
            (guild_id, json_str)
        )
        conn.commit()
    except Exception as e:
        print(f"❌ Error saving export for {guild_id}: {e}")

async def load_export_from_db(guild_id):
    try:
        c.execute("SELECT data FROM exports WHERE guild_id = ?", (guild_id,))
        row = c.fetchone()
        if row:
            return json.loads(row[0])
    except Exception as e:
        print(f"❌ Error loading export for {guild_id}: {e}")
    return None
