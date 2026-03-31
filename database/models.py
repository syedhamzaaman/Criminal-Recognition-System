"""
Data model helpers for Firestore documents.
Replaces SQLAlchemy ORM models.
"""
from datetime import datetime


def person_to_dict(doc_id, data):
    """Convert a Firestore person document to a dict."""
    return {
        "id": doc_id,
        "full_name": data.get("full_name", ""),
        "date_of_birth": data.get("date_of_birth"),
        "gender": data.get("gender"),
        "nationality": data.get("nationality"),
        "address": data.get("address"),
        "government_id_number": data.get("government_id_number"),
        "record_status": data.get("record_status", "Clean"),
        "risk_level": data.get("risk_level", "Low"),
        "last_seen_location": data.get("last_seen_location"),
        "image_path": data.get("image_path"),
        "has_embedding": data.get("face_embedding_encrypted") is not None,
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }


def record_to_dict(doc_id, data):
    """Convert a Firestore criminal record document to a dict."""
    return {
        "id": doc_id,
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


def audit_to_dict(doc_id, data):
    """Convert a Firestore audit log document to a dict."""
    return {
        "id": doc_id,
        "officer_id": data.get("officer_id"),
        "officer_name": data.get("officer_name", "Unknown"),
        "action_type": data.get("action_type"),
        "timestamp": data.get("timestamp"),
        "person_id": data.get("person_id"),
        "details": data.get("details"),
        "ip_address": data.get("ip_address"),
    }
