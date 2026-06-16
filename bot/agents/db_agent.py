import logging
from datetime import datetime

# Temporary In-Memory Database Simulation (As per rules)
# Format: { "normalized_name": {"tg_id": 1234, "alias_history": [], "created_at": "date"} }
CONTACT_DB = {
    "ritik": {
        "tg_id": 997147,
        "alias_history": ["ritik_old"],
        "created_at": "2026-05-15 14:30:00"
    }
}

class DatabaseAgent:
    def __init__(self):
        self.logger = logging.getLogger("DatabaseAgent")

    def check_contact(self, name: str):
        """
        Scans database with case-insensitive normalization.
        """
        normalized_name = name.strip().lower()
        if normalized_name in CONTACT_DB:
            return {
                "exists": True,
                "data": CONTACT_DB[normalized_name],
                "normalized_name": normalized_name
            }
        return {"exists": False, "normalized_name": normalized_name}

    def update_contact_name(self, tg_id: int, old_name: str, new_name: str):
        """
        Safe Edit Rule: Updates identity without deleting history.
        """
        old_normalized = old_name.strip().lower()
        new_normalized = new_name.strip().lower()

        # Preserve alias history (Rule 12: Never delete history permanently)
        if old_normalized in CONTACT_DB:
            history = CONTACT_DB[old_normalized]["alias_history"]
            history.append(old_normalized)
            
            # Create new mapping
            CONTACT_DB[new_normalized] = {
                "tg_id": tg_id,
                "alias_history": history,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Mark old as deprecated/removed from active search but keep in logs
            del CONTACT_DB[old_normalized]
            
            # Log action (Rule 7: Logging Rule)
            print(f"[LOG] - ACTION: merge/modify | FILE: db_agent | TIMESTAMP: {datetime.now()} | AGENT: DatabaseAgent | REASON: Owner requested name change")
            return True
        return False