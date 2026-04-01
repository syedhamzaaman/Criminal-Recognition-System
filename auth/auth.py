"""
Firebase Authentication & RBAC middleware.
Uses Firebase Admin SDK for token verification.
Loads credentials from environment variables (no JSON file needed).
"""
import os
import uuid
import urllib.parse
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore, storage
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def _build_firebase_credentials():
    """
    Build Firebase credentials from environment variables.
    Falls back to JSON file if env vars are not set (local dev).
    """
    project_id = os.environ.get("FIREBASE_PROJECT_ID")

    if project_id:
        # Build service account dict from env vars
        private_key = os.environ.get("FIREBASE_PRIVATE_KEY", "")
        # Handle escaped newlines from env var
        private_key = private_key.replace("\\n", "\n")

        service_account_info = {
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
            "private_key": private_key,
            "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL", ""),
            "client_id": os.environ.get("FIREBASE_CLIENT_ID", ""),
            "auth_uri": os.environ.get("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": os.environ.get("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL", ""),
            "universe_domain": "googleapis.com",
        }
        return credentials.Certificate(service_account_info)
    else:
        # Fallback: look for JSON file (local development)
        _KEY_PATH = os.path.join(os.path.dirname(__file__), "..", "crs-app-e0093-firebase-adminsdk-fbsvc-76047bb4db.json")
        if os.path.exists(_KEY_PATH):
            return credentials.Certificate(_KEY_PATH)
        raise RuntimeError(
            "Firebase credentials not found! Set FIREBASE_PROJECT_ID and related "
            "env vars, or provide the service account JSON file."
        )


# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = _build_firebase_credentials()
    bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET", "crs-app-e0093.firebasestorage.app")
    firebase_admin.initialize_app(cred, {
        'storageBucket': bucket_name
    })

import requests
import base64

def upload_image_to_imgbb(file_path_or_bytes, destination_filename=None):
    """
    Uploads an image to ImgBB and returns its public direct URL.
    This avoids Firebase Cloud Storage billing requirements.
    """
    api_key = os.environ.get("IMGBB_API_KEY")
    if not api_key:
        raise RuntimeError("IMGBB_API_KEY environment variable is missing!")
        
    url = "https://api.imgbb.com/1/upload"
    
    # Read bytes if string path is provided
    if isinstance(file_path_or_bytes, str):
        with open(file_path_or_bytes, "rb") as f:
            image_data = f.read()
    else:
        image_data = file_path_or_bytes
        
    payload = {
        "key": api_key,
        "image": base64.b64encode(image_data).decode('utf-8')
    }
    
    res = requests.post(url, data=payload)
    if res.status_code == 200:
        return res.json()["data"]["url"]
    else:
        raise Exception(f"ImgBB upload failed: {res.text}")

# Firestore client
db_firestore = firestore.client()

# Use HTTPBearer instead of OAuth2PasswordBearer for Firebase tokens
security = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency — verifies Firebase ID token and returns user info."""
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = creds.credentials
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    uid = decoded.get("uid")
    email = decoded.get("email", "")
    
    # Look up officer profile in Firestore
    officers_ref = db_firestore.collection("officers")
    docs = officers_ref.where("email", "==", email).limit(1).stream()
    officer_doc = None
    for doc in docs:
        officer_doc = doc
        break
    
    if officer_doc:
        officer_data = officer_doc.to_dict()
        return {
            "uid": uid,
            "email": email,
            "officer_id": officer_doc.id,
            "sub": officer_data.get("username", email),
            "full_name": officer_data.get("full_name", email.split("@")[0]),
            "role": officer_data.get("role", "officer"),
            "badge_number": officer_data.get("badge_number", ""),
            "department": officer_data.get("department", ""),
        }
    
    # If no officer profile exists, create a default one
    return {
        "uid": uid,
        "email": email,
        "officer_id": uid,
        "sub": email.split("@")[0],
        "full_name": email.split("@")[0].replace(".", " ").title(),
        "role": "officer",
        "badge_number": "",
        "department": "",
    }


def require_role(*roles):
    """RBAC dependency factory — restrict endpoint to specified roles."""
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "")
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(roles)}"
            )
        return current_user
    return role_checker
