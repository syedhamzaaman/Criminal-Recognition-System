"""
Person management API routes — Firestore-backed.
"""
import os
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from auth.auth import get_current_user, require_role, db_firestore
from database.models import person_to_dict
from database.encryption import encrypt_embedding
from face_pipeline.embedder import extract_embedding
from PIL import Image
import io

router = APIRouter(prefix="/api/persons", tags=["Persons"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")


@router.get("")
def list_persons(
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    risk: str = None,
    search: str = None,
    current_user: dict = Depends(get_current_user),
):
    db = db_firestore
    persons_ref = db.collection("persons")
    
    # Firestore doesn't support complex OR queries, so we filter in Python for search
    all_docs = persons_ref.stream()
    results = []
    for doc in all_docs:
        data = doc.to_dict()
        if status and data.get("record_status") != status:
            continue
        if risk and data.get("risk_level") != risk:
            continue
        if search and search.lower() not in (data.get("full_name", "")).lower():
            continue
        results.append(person_to_dict(doc.id, data))
    
    # Sort by updated_at descending
    results.sort(key=lambda x: x.get("updated_at", "") or "", reverse=True)
    total = len(results)
    paged = results[skip:skip + limit]
    
    return {"total": total, "persons": paged}


@router.get("/{person_id}")
def get_person(person_id: str, current_user: dict = Depends(get_current_user)):
    db = db_firestore
    doc = db.collection("persons").document(person_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Person not found")
    
    result = person_to_dict(doc.id, doc.to_dict())
    
    # Get criminal records
    records_ref = db.collection("criminal_records").where("person_id", "==", person_id)
    records = []
    for rec_doc in records_ref.stream():
        rec_data = rec_doc.to_dict()
        records.append({
            "id": rec_doc.id,
            "crime_type": rec_data.get("crime_type"),
            "crime_description": rec_data.get("crime_description"),
            "case_number": rec_data.get("case_number"),
            "date_of_offense": rec_data.get("date_of_offense"),
            "arrest_date": rec_data.get("arrest_date"),
            "conviction_status": rec_data.get("conviction_status"),
            "sentence_details": rec_data.get("sentence_details"),
            "law_enforcement_agency": rec_data.get("law_enforcement_agency"),
            "court_name": rec_data.get("court_name"),
            "officer_notes": rec_data.get("officer_notes"),
            "last_updated": rec_data.get("last_updated"),
        })
    result["criminal_records"] = records
    return result


@router.post("")
async def create_person(
    full_name: str = Form(...),
    date_of_birth: str = Form(None),
    gender: str = Form(None),
    nationality: str = Form(None),
    address: str = Form(None),
    government_id_number: str = Form(None),
    record_status: str = Form("Clean"),
    risk_level: str = Form("Low"),
    last_seen_location: str = Form(None),
    photos: List[UploadFile] = File(None),
    current_user: dict = Depends(require_role("admin", "officer")),
):
    db = db_firestore
    now = datetime.utcnow().isoformat()
    
    person_data = {
        "full_name": full_name,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "nationality": nationality,
        "address": address,
        "government_id_number": government_id_number,
        "record_status": record_status,
        "risk_level": risk_level,
        "last_seen_location": last_seen_location,
        "image_path": None,
        "face_embedding_encrypted": None,
        "created_at": now,
        "updated_at": now,
    }

    # Handle photo upload and embedding
    if photos:
        from face_pipeline.embedder import extract_multi_embedding
        from auth.auth import upload_image_to_firebase
        images_for_embedding = []

        for i, photo in enumerate(photos):
            if not photo.filename:
                continue
            ext = photo.filename.split(".")[-1] if "." in photo.filename else "jpg"
            filename = f"{uuid.uuid4()}.{ext}"

            contents = await photo.read()

            if i == 0:
                try:
                    person_data["image_path"] = upload_image_to_firebase(contents, filename)
                except Exception as e:
                    print(f"[ERR] Failed to upload to Firebase: {e}")

            try:
                img = Image.open(io.BytesIO(contents)).convert("RGB")
                images_for_embedding.append(img)
            except Exception:
                pass

        if images_for_embedding:
            try:
                embedding = extract_multi_embedding(images_for_embedding)
                if embedding:
                    person_data["face_embedding_encrypted"] = encrypt_embedding(embedding)
                    print(f"[PERSON] Generated embedding from {len(images_for_embedding)} photo(s) for {full_name}")
            except Exception as e:
                print(f"[PERSON] Embedding extraction failed: {e}")

    _, doc_ref = db.collection("persons").add(person_data)
    person_id = doc_ref.id

    # Audit log
    db.collection("audit_log").add({
        "officer_id": current_user.get("officer_id"),
        "officer_name": current_user.get("full_name", "Unknown"),
        "action_type": "Add",
        "person_id": person_id,
        "details": f"Added person: {full_name}",
        "timestamp": now,
    })

    return person_to_dict(person_id, person_data)


@router.put("/{person_id}")
async def update_person(
    person_id: str,
    full_name: str = Form(None),
    date_of_birth: str = Form(None),
    gender: str = Form(None),
    nationality: str = Form(None),
    address: str = Form(None),
    government_id_number: str = Form(None),
    record_status: str = Form(None),
    risk_level: str = Form(None),
    last_seen_location: str = Form(None),
    current_user: dict = Depends(require_role("admin", "officer")),
):
    db = db_firestore
    doc_ref = db.collection("persons").document(person_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Person not found")

    updates = {"updated_at": datetime.utcnow().isoformat()}
    for field, value in [
        ("full_name", full_name), ("date_of_birth", date_of_birth),
        ("gender", gender), ("nationality", nationality),
        ("address", address), ("government_id_number", government_id_number),
        ("record_status", record_status), ("risk_level", risk_level),
        ("last_seen_location", last_seen_location),
    ]:
        if value is not None:
            updates[field] = value

    doc_ref.update(updates)
    
    db.collection("audit_log").add({
        "officer_id": current_user.get("officer_id"),
        "officer_name": current_user.get("full_name", "Unknown"),
        "action_type": "Update",
        "person_id": person_id,
        "details": f"Updated person: {full_name or doc.to_dict().get('full_name', '')}",
        "timestamp": datetime.utcnow().isoformat(),
    })

    updated_doc = doc_ref.get()
    return person_to_dict(updated_doc.id, updated_doc.to_dict())


@router.delete("/{person_id}")
def delete_person(
    person_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    db = db_firestore
    doc_ref = db.collection("persons").document(person_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Person not found")

    person_data = doc.to_dict()

    # Delete associated criminal records
    records = db.collection("criminal_records").where("person_id", "==", person_id).stream()
    for rec in records:
        rec.reference.delete()

    # Delete photo
    if person_data.get("image_path"):
        try:
            photo_path = os.path.join(os.path.dirname(__file__), "..", person_data["image_path"].lstrip("/"))
            if os.path.exists(photo_path):
                os.remove(photo_path)
        except Exception:
            pass

    db.collection("audit_log").add({
        "officer_id": current_user.get("officer_id"),
        "officer_name": current_user.get("full_name", "Unknown"),
        "action_type": "Delete",
        "person_id": person_id,
        "details": f"Deleted person: {person_data.get('full_name', '')}",
        "timestamp": datetime.utcnow().isoformat(),
    })

    doc_ref.delete()
    return {"message": "Person deleted"}


from pydantic import BaseModel

class BulkDeleteRequest(BaseModel):
    person_ids: List[str]

@router.post("/bulk-delete")
def bulk_delete_persons(
    request: BulkDeleteRequest,
    current_user: dict = Depends(require_role("admin", "officer")),
):
    db = db_firestore
    person_ids = request.person_ids
    if not person_ids:
        raise HTTPException(status_code=400, detail="No person IDs provided")

    deleted = 0
    names = []
    for pid in person_ids:
        doc_ref = db.collection("persons").document(pid)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            names.append(data.get("full_name", "Unknown"))

            # Delete criminal records
            records = db.collection("criminal_records").where("person_id", "==", pid).stream()
            for rec in records:
                rec.reference.delete()

            # Delete photo
            if data.get("image_path"):
                try:
                    photo_path = os.path.join(os.path.dirname(__file__), "..", data["image_path"].lstrip("/"))
                    if os.path.exists(photo_path):
                        os.remove(photo_path)
                except Exception:
                    pass

            db.collection("audit_log").add({
                "officer_id": current_user.get("officer_id"),
                "officer_name": current_user.get("full_name", "Unknown"),
                "action_type": "Delete",
                "person_id": pid,
                "details": f"Bulk deleted person: {data.get('full_name', '')}",
                "timestamp": datetime.utcnow().isoformat(),
            })

            doc_ref.delete()
            deleted += 1

    return {
        "message": f"{deleted} person(s) deleted successfully",
        "deleted_count": deleted,
        "deleted_names": names,
    }
