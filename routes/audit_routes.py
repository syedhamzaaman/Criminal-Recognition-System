"""
Audit log viewing API routes — Firestore-backed.
"""
from fastapi import APIRouter, Depends
from auth.auth import get_current_user, require_role, db_firestore

router = APIRouter(prefix="/api/audit", tags=["Audit Log"])


@router.get("")
def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action_type: str = None,
    current_user: dict = Depends(require_role("admin", "officer")),
):
    db = db_firestore
    
    if action_type:
        query = db.collection("audit_log").where("action_type", "==", action_type).order_by("timestamp", direction="DESCENDING")
    else:
        query = db.collection("audit_log").order_by("timestamp", direction="DESCENDING")
    
    all_docs = list(query.stream())
    total = len(all_docs)
    paged = all_docs[skip:skip + limit]
    
    results = []
    for doc in paged:
        data = doc.to_dict()
        
        # Get person name if person_id exists
        person_name = None
        if data.get("person_id"):
            person_doc = db.collection("persons").document(data["person_id"]).get()
            if person_doc.exists:
                person_name = person_doc.to_dict().get("full_name")
        
        results.append({
            "id": doc.id,
            "officer_id": data.get("officer_id"),
            "officer_name": data.get("officer_name", "Unknown"),
            "officer_badge": data.get("officer_badge"),
            "action_type": data.get("action_type"),
            "timestamp": data.get("timestamp"),
            "person_id": data.get("person_id"),
            "person_name": person_name,
            "details": data.get("details"),
            "ip_address": data.get("ip_address"),
        })
    
    return {"total": total, "logs": results}
