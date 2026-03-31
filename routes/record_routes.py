"""
Criminal record management API routes — Firestore-backed.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from auth.auth import get_current_user, require_role, db_firestore

router = APIRouter(prefix="/api/records", tags=["Criminal Records"])


class RecordCreate(BaseModel):
    person_id: str
    crime_type: str
    crime_description: Optional[str] = None
    case_number: Optional[str] = None
    date_of_offense: Optional[str] = None
    arrest_date: Optional[str] = None
    conviction_status: Optional[str] = None
    sentence_details: Optional[str] = None
    law_enforcement_agency: Optional[str] = None
    court_name: Optional[str] = None
    officer_notes: Optional[str] = None
    update_record_status: Optional[str] = None
    update_risk_level: Optional[str] = None


class RecordUpdate(BaseModel):
    crime_type: Optional[str] = None
    crime_description: Optional[str] = None
    case_number: Optional[str] = None
    date_of_offense: Optional[str] = None
    arrest_date: Optional[str] = None
    conviction_status: Optional[str] = None
    sentence_details: Optional[str] = None
    law_enforcement_agency: Optional[str] = None
    court_name: Optional[str] = None
    officer_notes: Optional[str] = None


@router.get("")
def list_records(
    person_id: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    db = db_firestore
    if person_id:
        query = db.collection("criminal_records").where("person_id", "==", person_id)
    else:
        query = db.collection("criminal_records")
    
    all_docs = list(query.stream())
    # Sort by last_updated descending
    all_docs.sort(key=lambda d: d.to_dict().get("last_updated", "") or "", reverse=True)
    total = len(all_docs)
    paged = all_docs[skip:skip + limit]
    
    return {
        "total": total,
        "records": [_doc_to_dict(d) for d in paged],
    }


@router.get("/{record_id}")
def get_record(record_id: str, current_user: dict = Depends(get_current_user)):
    db = db_firestore
    doc = db.collection("criminal_records").document(record_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Record not found")
    return _doc_to_dict(doc)


@router.post("")
def create_record(
    data: RecordCreate,
    current_user: dict = Depends(require_role("admin", "officer")),
):
    db = db_firestore
    
    # Verify person exists
    person_doc = db.collection("persons").document(data.person_id).get()
    if not person_doc.exists:
        raise HTTPException(status_code=404, detail="Person not found")

    now = datetime.utcnow().isoformat()
    record_data = {
        "person_id": data.person_id,
        "crime_type": data.crime_type,
        "crime_description": data.crime_description,
        "case_number": data.case_number,
        "date_of_offense": data.date_of_offense,
        "arrest_date": data.arrest_date,
        "conviction_status": data.conviction_status,
        "sentence_details": data.sentence_details,
        "law_enforcement_agency": data.law_enforcement_agency,
        "court_name": data.court_name,
        "officer_notes": data.officer_notes,
        "last_updated": now,
    }
    _, doc_ref = db.collection("criminal_records").add(record_data)

    # Update person status if specified
    person_updates = {"updated_at": now}
    if data.update_record_status:
        person_updates["record_status"] = data.update_record_status
    if data.update_risk_level:
        person_updates["risk_level"] = data.update_risk_level
    db.collection("persons").document(data.person_id).update(person_updates)

    # Audit log
    db.collection("audit_log").add({
        "officer_id": current_user.get("officer_id"),
        "officer_name": current_user.get("full_name", "Unknown"),
        "action_type": "Add",
        "person_id": data.person_id,
        "details": f"Added criminal record: {data.crime_type} (Case: {data.case_number})",
        "timestamp": now,
    })

    record_data["id"] = doc_ref.id
    return record_data


@router.put("/{record_id}")
def update_record(
    record_id: str,
    data: RecordUpdate,
    current_user: dict = Depends(require_role("admin", "officer")),
):
    db = db_firestore
    doc_ref = db.collection("criminal_records").document(record_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Record not found")

    updates = {"last_updated": datetime.utcnow().isoformat()}
    for field, value in data.dict(exclude_unset=True).items():
        if value is not None:
            updates[field] = value
    
    doc_ref.update(updates)

    doc_data = doc.to_dict()
    db.collection("audit_log").add({
        "officer_id": current_user.get("officer_id"),
        "officer_name": current_user.get("full_name", "Unknown"),
        "action_type": "Update",
        "person_id": doc_data.get("person_id"),
        "details": f"Updated record #{record_id}: {doc_data.get('crime_type', '')}",
        "timestamp": datetime.utcnow().isoformat(),
    })

    updated = doc_ref.get()
    return _doc_to_dict(updated)


def _doc_to_dict(doc):
    data = doc.to_dict()
    return {
        "id": doc.id,
        "person_id": data.get("person_id"),
        "crime_type": data.get("crime_type"),
        "crime_description": data.get("crime_description"),
        "case_number": data.get("case_number"),
        "date_of_offense": data.get("date_of_offense"),
        "arrest_date": data.get("arrest_date"),
        "conviction_status": data.get("conviction_status"),
        "sentence_details": data.get("sentence_details"),
        "law_enforcement_agency": data.get("law_enforcement_agency"),
        "court_name": data.get("court_name"),
        "officer_notes": data.get("officer_notes"),
        "last_updated": data.get("last_updated"),
    }
