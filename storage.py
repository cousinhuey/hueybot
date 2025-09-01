import aiosqlite
import json
import os

# DB-Verbindung persistent im Volume speichern
DB_PATH = "/mnt/data/exports.db"

# Initialisierung: Tabelle erstellen
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS exports (
            guild_id TEXT PRIMARY KEY,
            data TEXT
        )
        """)
        await db.commit()

# Export speichern (async)
async def save_export(guild_id, data):
    try:
        json_str = json.dumps(data)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO exports (guild_id, data) VALUES (?, ?)",
                (guild_id, json_str)
            )
            await db.commit()
    except Exception as e:
        print(f"❌ Error saving export for {guild_id}: {e}")

# Export aus DB laden (async)
async def load_export_from_db(guild_id):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT data FROM exports WHERE guild_id = ?", (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
    except Exception as e:
        print(f"❌ Error loading export for {guild_id}: {e}")
    return None
