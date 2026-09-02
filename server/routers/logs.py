from fastapi import APIRouter, Depends
from middleware.firebase_auth import get_current_user
from services import log_service

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("")
@router.get("/")
async def get_logs_route(user: dict = Depends(get_current_user)):
    """
    Get all activity logs for the logged-in user.
    """
    uid = user.get("uid", "")
    logs = log_service.get_user_logs(uid)
    return {"logs": logs}

@router.post("/clear")
async def clear_logs_route(user: dict = Depends(get_current_user)):
    """
    Purge activity logs for the logged-in user.
    """
    uid = user.get("uid", "")
    log_service.clear_user_logs(uid)
    return {"status": "success"}
