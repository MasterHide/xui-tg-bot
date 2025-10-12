import sqlite3, json, logging
from config_loader import load_config

def toggle_user(email, state: bool):
    cfg = load_config()
    conn = sqlite3.connect(cfg["db_path"])
    cur = conn.cursor()
    row = cur.execute("SELECT id, settings FROM inbounds WHERE settings LIKE ?", (f"%{email}%",)).fetchone()
    if not row:
        logging.warning(f"User {email} not found.")
        return False
    inbound_id, settings = row
    s = json.loads(settings)
    for c in s["clients"]:
        if c.get("email") == email:
            c["enable"] = state
    cur.execute("UPDATE inbounds SET settings=? WHERE id=?", (json.dumps(s), inbound_id))
    conn.commit(); conn.close()
    logging.info(f"User {email} {'enabled' if state else 'disabled'}.")
    return True
