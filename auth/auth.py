"""
Firebase Authentication & RBAC middleware.
Uses Firebase Admin SDK for token verification.
"""
import os
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Initialize Firebase Admin SDK
_KEY_PATH = os.path.join(os.path.dirname(__file__), "..", "crs-app-e0093-firebase-adminsdk-fbsvc-76047bb4db.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(_KEY_PATH)
    firebase_admin.initialize_app(cred)

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
