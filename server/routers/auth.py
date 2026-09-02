"""Auth router — Firebase ID token verification endpoint."""

from fastapi import APIRouter, HTTPException
from firebase_admin import auth as firebase_auth
from middleware.firebase_auth import _init_firebase
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenRequest(BaseModel):
    id_token: str


@router.post("/verify")
async def verify_token(body: TokenRequest):
    """
    Verify a Firebase ID token sent from the frontend.
    Returns basic user info on success.
    """
    _init_firebase()
    try:
        decoded = firebase_auth.verify_id_token(body.id_token)
        uid = decoded.get("uid")
        email = decoded.get("email") or ""
        from services import log_service
        log_service.add_log(uid, email, "SIGN_IN", "User signed in successfully.")
        return {
            "uid":   uid,
            "email": email,
            "name":  decoded.get("name"),
        }
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
