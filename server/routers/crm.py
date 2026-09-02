import json
import os
import time
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException
from middleware.firebase_auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/crm", tags=["crm"])

INTERACTIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "crm_interactions.json")
_lock = Lock()

class InteractionSchema(BaseModel):
    client_email: str
    date: str
    topic: str
    outcome: str
    has_grievance: bool

def _load_interactions() -> list[dict]:
    if not os.path.exists(INTERACTIONS_FILE):
        return []
    try:
        with open(INTERACTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_interactions(data: list[dict]):
    os.makedirs(os.path.dirname(INTERACTIONS_FILE), exist_ok=True)
    try:
        with open(INTERACTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[CRM Router] Save failed: {e}")

@router.get("/interactions")
async def get_interactions(client_email: str | None = None, user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    with _lock:
        all_logs = _load_interactions()
    
    # Filter logs belonging to this user
    if client_email:
        filtered = [
            log for log in all_logs
            if log.get("uid") == uid and log.get("client_email", "").strip().lower() == client_email.strip().lower()
        ]
    else:
        filtered = [
            log for log in all_logs
            if log.get("uid") == uid
        ]
    # Sort chronologically by date
    filtered.sort(key=lambda x: x.get("date", ""), reverse=True)
    return {"interactions": filtered}

@router.post("/interactions")
async def add_interaction(body: InteractionSchema, user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    email_addr = user.get("email") or ""
    
    with _lock:
        all_logs = _load_interactions()
        
        new_log = {
            "id": f"int_{int(time.time())}",
            "uid": uid,
            "client_email": body.client_email.strip().lower(),
            "date": body.date,
            "topic": body.topic,
            "outcome": body.outcome,
            "has_grievance": body.has_grievance,
            "created_at": time.time()
        }
        all_logs.append(new_log)
        _save_interactions(all_logs)
        
    from services import log_service
    log_service.add_log(uid, email_addr, "LOG_TOUCHPOINT", f"Logged CRM touchpoint for '{body.client_email}' on {body.date} (Grievance: {body.has_grievance}).", "SUCCESS")
    return {"status": "success", "interaction": new_log}

@router.put("/interactions/{interaction_id}")
async def update_interaction(interaction_id: str, body: InteractionSchema, user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    email_addr = user.get("email") or ""
    with _lock:
        all_logs = _load_interactions()
        
        target_log = None
        for log in all_logs:
            if log.get("id") == interaction_id and log.get("uid") == uid:
                target_log = log
                break
                
        if not target_log:
            from services import log_service
            log_service.add_log(uid, email_addr, "EDIT_TOUCHPOINT", f"Failed to edit touchpoint {interaction_id}: Not found.", "ERROR")
            raise HTTPException(status_code=404, detail="Touchpoint not found")
            
        target_log["date"] = body.date
        target_log["topic"] = body.topic
        target_log["outcome"] = body.outcome
        target_log["has_grievance"] = body.has_grievance
        
        _save_interactions(all_logs)
        
    from services import log_service
    log_service.add_log(uid, email_addr, "EDIT_TOUCHPOINT", f"Updated CRM touchpoint details for '{body.client_email}' (Grievance: {body.has_grievance}).", "SUCCESS")
    return {"status": "success", "interaction": target_log}

@router.get("/analytics")
async def get_analytics(user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    with _lock:
        all_logs = _load_interactions()
        
    user_logs = [log for log in all_logs if log.get("uid") == uid]
    
    # Track unique client emails with active grievances
    # Active grievance = most recent interaction for a client email flags has_grievance as true
    grievances_map = {}
    for log in user_logs:
        email = log.get("client_email", "").strip().lower()
        if not email:
            continue
        # We want to find the latest log by date/created_at to see if the grievance is resolved or active
        if email not in grievances_map or log.get("created_at", 0) > grievances_map[email].get("created_at", 0):
            grievances_map[email] = log
            
    active_grievances_count = sum(1 for log in grievances_map.values() if log.get("has_grievance"))
    active_grievance_emails = [email for email, log in grievances_map.items() if log.get("has_grievance")]
    
    return {
        "total_interactions": len(user_logs),
        "active_grievances": active_grievances_count,
        "grievance_emails": active_grievance_emails
    }
