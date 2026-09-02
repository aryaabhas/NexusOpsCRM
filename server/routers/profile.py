import json
import os
from threading import Lock
from fastapi import APIRouter, Depends, HTTPException
from middleware.firebase_auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/profile", tags=["profile"])

PROFILE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_profiles.json")
_lock = Lock()

class UserProfileSchema(BaseModel):
    name: str
    designation: str
    company_name: str
    phone_number: str

def _load_profiles() -> dict:
    if not os.path.exists(PROFILE_FILE):
        return {}
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_profiles(data: dict):
    os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Profile Router] Save failed: {e}")

@router.get("")
async def get_profile(user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    with _lock:
        profiles = _load_profiles()
    return profiles.get(uid, {
        "name": "",
        "designation": "",
        "company_name": "",
        "phone_number": ""
    })

@router.post("")
async def save_profile(body: UserProfileSchema, user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    with _lock:
        profiles = _load_profiles()
        profiles[uid] = {
            "name": body.name,
            "designation": body.designation,
            "company_name": body.company_name,
            "phone_number": body.phone_number
        }
        _save_profiles(profiles)
    return {"status": "success", "profile": profiles[uid]}
