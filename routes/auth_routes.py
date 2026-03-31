"""
Authentication API routes — Firebase-based.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from auth.auth import get_current_user, db_firestore

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class SessionRequest(BaseModel):
    """Client sends Firebase ID token after login."""
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    officer: dict


@router.post("/session")
def create_session(req: SessionRequest):
    """
    Client logs in via Firebase JS SDK, then sends the ID token here.
    We verify it and return the officer profile.
    """
    from firebase_admin import auth as firebase_auth
    
    try:
        decoded = firebase_auth.verify_id_token(req.id_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
    
    uid = decoded.get("uid")
    email = decoded.get("email", "")
    
    # Look up officer in Firestore
    db = db_firestore
    officers_ref = db.collection("officers")
    docs = officers_ref.where("email", "==", email).limit(1).stream()
    officer_data = None
    officer_id = None
    for doc in docs:
        officer_data = doc.to_dict()
        officer_id = doc.id
        break
    
    if not officer_data:
        # Auto-create officer profile for new Firebase users
        officer_data = {
            "username": email.split("@")[0],
            "email": email,
            "full_name": email.split("@")[0].replace(".", " ").title(),
            "role": "officer",
            "badge_number": f"AUTO-{uid[:6].upper()}",
            "department": "General",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        _, doc_ref = db.collection("officers").add(officer_data)
        officer_id = doc_ref.id
    
    # Log login
    db.collection("audit_log").add({
        "officer_id": officer_id,
        "officer_name": officer_data.get("full_name", "Unknown"),
        "action_type": "Login",
        "details": f"Officer {officer_data.get('username', email)} logged in",
        "timestamp": datetime.utcnow().isoformat(),
        "person_id": None,
    })
    
    return {
        "access_token": req.id_token,
        "token_type": "bearer",
        "officer": {
            "id": officer_id,
            "username": officer_data.get("username", ""),
            "full_name": officer_data.get("full_name", ""),
            "role": officer_data.get("role", "officer"),
            "badge_number": officer_data.get("badge_number", ""),
            "department": officer_data.get("department", ""),
        }
    }


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user.get("officer_id"),
        "username": current_user.get("sub"),
        "full_name": current_user.get("full_name"),
        "role": current_user.get("role"),
        "badge_number": current_user.get("badge_number"),
        "department": current_user.get("department"),
    }
