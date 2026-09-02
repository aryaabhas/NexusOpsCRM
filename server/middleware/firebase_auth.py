"""
Firebase ID token verification middleware for FastAPI.
Usage as a dependency: current_user = Depends(get_current_user)
"""

import os

import firebase_admin
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

# ── Initialize Firebase Admin SDK (once at module load) ──────────────────────
_firebase_initialized = False

def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized or firebase_admin._apps:
        _firebase_initialized = True
        return
    sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./serviceAccountKey.json")
    if os.path.exists(sa_path):
        cred = credentials.Certificate(sa_path)
    else:
        # Fallback: initialize with project ID only (limited verification)
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        if not project_id:
            raise RuntimeError(
                "Firebase not configured. Set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_PROJECT_ID."
            )
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)
    _firebase_initialized = True


_security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_security),
) -> dict:
    """
    FastAPI dependency that verifies a Firebase ID token from the
    'Authorization: Bearer <token>' header.
    Returns the decoded token dict on success.
    """
    _init_firebase()
    id_token = credentials.credentials
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
        )
    except firebase_auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {e}",
        )
