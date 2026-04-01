"""
Configuration API routes — serves non-secret config to the frontend.
"""
import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/config", tags=["Configuration"])


@router.get("/firebase")
def get_firebase_client_config():
    """
    Return Firebase client SDK config for the frontend.
    These are NOT secret — they are meant to be public (same as embedding in HTML).
    But we serve them from env vars so they aren't hardcoded in the repo.
    """
    return {
        "apiKey": os.environ.get("FIREBASE_API_KEY", ""),
        "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.environ.get("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.environ.get("FIREBASE_APP_ID", ""),
    }
