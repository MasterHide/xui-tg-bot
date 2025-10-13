import sqlite3, json, logging
from config_loader import load_config

def toggle_user(email: str, state: bool):
    """
    Enable or disable a specific user (client) inside the XUI database.
    Returns True if updated, False if not found or on error.
    """
    cfg = load_config()
    db_path = cfg.get("db_path", "/etc/x-ui/x-ui.db")

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Look for inbound containing the email in client settings
        row = cur.execute(
            "SELECT id, settings FROM inbounds WHERE settings LIKE ?",
            (f"%{email}%",)
        ).fetchone()

        if not row:
            logging.warning(f"User {email} not found.")
            conn.close()
            return False

        inbound_id, settings = row

        try:
            s = json.loads(settings)
        except Exception as e:
            logging.error(f"Invalid JSON in settings for inbound {inbound_id}: {e}")
            conn.close()
            return False

        found = False
        for c in s.get("clients", []):
            if c.get("email") == email:
                c["enable"] = state
                found = True
                break

        if not found:
            logging.warning(f"User {email} not found in clients list (inbound {inbound_id}).")
            conn.close()
            return False

        # Update database with modified settings
        cur.execute(
            "UPDATE inbounds SET settings=? WHERE id=?",
            (json.dumps(s, ensure_ascii=False), inbound_id)
        )
        conn.commit()
        conn.close()

        logging.info(f"User {email} {'enabled' if state else 'disabled'}.")
        return True

    except Exception as e:
        logging.error(f"toggle_user() failed for {email}: {e}")
        return False
