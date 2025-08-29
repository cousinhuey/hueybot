import sqlite3
import json

conn = sqlite3.connect("exports.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS exports (
    guild_id TEXT PRIMARY KEY,
    data TEXT
)
""")
conn.commit()

def save_export(guild_id, data):
    json_str = json.dumps(data)
    c.execute("INSERT OR REPLACE INTO exports (guild_id, data) VALUES (?, ?)", (guild_id, json_str))
    conn.commit()

def load_export_from_db(guild_id):
    c.execute("SELECT data FROM exports WHERE guild_id = ?", (guild_id,))
    row = c.fetchone()
    if row:
        return json.loads(row[0])
    return None
