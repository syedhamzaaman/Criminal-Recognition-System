"""
Dashboard statistics API routes — Firestore-backed.
"""
from fastapi import APIRouter, Depends
from auth.auth import get_current_user, db_firestore

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    db = db_firestore

    # Get all persons
    persons = list(db.collection("persons").stream())
    total_persons = len(persons)

    # Get all records
    records = list(db.collection("criminal_records").stream())
    total_records = len(records)

    # Count searches — simple where query (single field, no composite index needed)
    try:
        audit_docs = list(db.collection("audit_log").where("action_type", "==", "Search").stream())
        total_searches = len(audit_docs)
    except Exception:
        total_searches = 0

    # Count active officers
    try:
        officer_docs = list(db.collection("officers").where("is_active", "==", True).stream())
        total_officers = len(officer_docs)
    except Exception:
        total_officers = 0

    # Status distribution
    status_dist = {}
    risk_dist = {}
    most_wanted = []

    for doc in persons:
        data = doc.to_dict()
        s = data.get("record_status", "Unknown") or "Unknown"
        status_dist[s] = status_dist.get(s, 0) + 1

        r = data.get("risk_level", "Unknown") or "Unknown"
        risk_dist[r] = risk_dist.get(r, 0) + 1

        # Collect most wanted (High risk)
        if data.get("risk_level") == "High":
            most_wanted.append({
                "id": doc.id,
                "full_name": data.get("full_name", ""),
                "risk_level": "High",
                "record_status": data.get("record_status", ""),
                "last_seen_location": data.get("last_seen_location", "Unknown"),
                "image_path": data.get("image_path"),
            })

    # Crime type distribution
    crime_dist = {}
    for doc in records:
        data = doc.to_dict()
        ct = data.get("crime_type", "Unknown") or "Unknown"
        crime_dist[ct] = crime_dist.get(ct, 0) + 1

    # Recent activity (last 20) — try order_by, fall back to fetching all and sorting in-memory
    recent_activity = []
    try:
        recent_logs = db.collection("audit_log").order_by("timestamp", direction="DESCENDING").limit(20).stream()
        for doc in recent_logs:
            data = doc.to_dict()
            recent_activity.append({
                "id": doc.id,
                "action_type": data.get("action_type"),
                "officer_name": data.get("officer_name", "Unknown"),
                "details": data.get("details"),
                "timestamp": data.get("timestamp"),
                "person_id": data.get("person_id"),
            })
    except Exception:
        # Fallback: fetch all audit logs and sort in memory
        try:
            all_logs = list(db.collection("audit_log").stream())
            all_entries = []
            for doc in all_logs:
                data = doc.to_dict()
                all_entries.append({
                    "id": doc.id,
                    "action_type": data.get("action_type"),
                    "officer_name": data.get("officer_name", "Unknown"),
                    "details": data.get("details"),
                    "timestamp": data.get("timestamp"),
                    "person_id": data.get("person_id"),
                })
            all_entries.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
            recent_activity = all_entries[:20]
        except Exception:
            recent_activity = []

    # Latest detections — avoid composite index requirement (where + order_by)
    latest_detections = []
    try:
        # Try composite query first (needs index)
        search_logs = db.collection("audit_log").where("action_type", "==", "Search").order_by("timestamp", direction="DESCENDING").limit(10).stream()
        for doc in search_logs:
            data = doc.to_dict()
            if data.get("person_id"):
                latest_detections.append({
                    "officer_name": data.get("officer_name", "Unknown"),
                    "details": data.get("details", ""),
                    "timestamp": data.get("timestamp"),
                    "person_id": data.get("person_id"),
                })
    except Exception:
        # Fallback: filter + sort in memory
        try:
            search_docs = list(db.collection("audit_log").where("action_type", "==", "Search").stream())
            search_entries = []
            for doc in search_docs:
                data = doc.to_dict()
                if data.get("person_id"):
                    search_entries.append({
                        "officer_name": data.get("officer_name", "Unknown"),
                        "details": data.get("details", ""),
                        "timestamp": data.get("timestamp"),
                        "person_id": data.get("person_id"),
                    })
            search_entries.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
            latest_detections = search_entries[:10]
        except Exception:
            latest_detections = []

    return {
        "total_persons": total_persons,
        "total_records": total_records,
        "total_searches": total_searches,
        "total_officers": total_officers,
        "status_distribution": status_dist,
        "risk_distribution": risk_dist,
        "crime_distribution": crime_dist,
        "recent_activity": recent_activity,
        "most_wanted": most_wanted[:5],
        "latest_detections": latest_detections[:5],
    }
