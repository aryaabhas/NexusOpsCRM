import datetime
import json
import os
from threading import Lock

LOGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "activity_logs.json")
_lock = Lock()

def add_log(uid: str, email: str, action: str, details: str, status: str = "SUCCESS"):
    """
    Log a user action. Appends it to the activity_logs.json file.
    """
    os.makedirs(os.path.dirname(LOGS_FILE), exist_ok=True)
    
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "uid": uid,
        "email": email,
        "action": action,
        "details": details,
        "status": status
    }

    with _lock:
        logs = []
        if os.path.exists(LOGS_FILE):
            try:
                with open(LOGS_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []
        
        logs.append(entry)
        
        try:
            with open(LOGS_FILE, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[LogService] Failed to write log: {e}")

def get_user_logs(uid: str) -> list[dict]:
    """
    Get all log entries matching the given Firebase UID, sorted by newest first.
    """
    if not os.path.exists(LOGS_FILE):
        return []
        
    with _lock:
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            return []
            
    # Filter by user UID and reverse to show newest first
    user_logs = [log for log in logs if log.get("uid") == uid]
    user_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return user_logs

def clear_user_logs(uid: str):
    if not os.path.exists(LOGS_FILE):
        return
    with _lock:
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
            remaining_logs = [log for log in logs if log.get("uid") != uid]
            with open(LOGS_FILE, "w", encoding="utf-8") as f:
                json.dump(remaining_logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[LogService] Failed to clear user logs: {e}")
