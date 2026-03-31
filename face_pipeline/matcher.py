"""
Face matching engine — compares query embedding against stored embeddings in Firestore.
Uses cosine similarity with proper thresholds for SFace embeddings.
"""
import numpy as np
from typing import List, Dict
from database.encryption import decrypt_embedding


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    dot = np.dot(a_arr, b_arr)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def euclidean_distance(a, b):
    """Compute Euclidean distance between two vectors."""
    return float(np.linalg.norm(np.array(a) - np.array(b)))


def search_matches(
    query_embedding,
    db,
    threshold=0.4,
    max_results=10
):
    """
    Search Firestore for matching faces.
    Returns ranked list of matches above threshold.
    """
    persons_ref = db.collection("persons")
    all_persons = persons_ref.stream()

    results = []
    for doc in all_persons:
        data = doc.to_dict()
        encrypted = data.get("face_embedding_encrypted")
        if not encrypted:
            continue

        try:
            stored_embedding = decrypt_embedding(encrypted)
        except Exception:
            continue

        if len(stored_embedding) != len(query_embedding):
            continue

        cos_sim = cosine_similarity(query_embedding, stored_embedding)
        euc_dist = euclidean_distance(query_embedding, stored_embedding)

        # Convert similarity to confidence score
        if cos_sim < 0.20:
            confidence = 0.0
        elif cos_sim < 0.363:
            confidence = ((cos_sim - 0.20) / 0.163) * 59.9
        else:
            confidence = 60.0 + ((cos_sim - 0.363) / 0.637) * 40.0

        confidence = max(0.0, min(100.0, confidence))

        if cos_sim >= threshold:
            # Fetch criminal records for this person
            records_ref = db.collection("criminal_records").where("person_id", "==", doc.id)
            crime_records = []
            for rec_doc in records_ref.stream():
                rec_data = rec_doc.to_dict()
                crime_records.append({
                    "crime_type": rec_data.get("crime_type"),
                    "case_number": rec_data.get("case_number"),
                    "conviction_status": rec_data.get("conviction_status"),
                    "date_of_offense": rec_data.get("date_of_offense"),
                })

            results.append({
                "person_id": doc.id,
                "full_name": data.get("full_name", ""),
                "confidence": round(confidence, 2),
                "cosine_similarity": round(cos_sim, 4),
                "euclidean_distance": round(euc_dist, 4),
                "record_status": data.get("record_status"),
                "risk_level": data.get("risk_level"),
                "date_of_birth": data.get("date_of_birth"),
                "gender": data.get("gender"),
                "nationality": data.get("nationality"),
                "image_path": data.get("image_path"),
                "last_seen_location": data.get("last_seen_location"),
                "criminal_records": crime_records,
            })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:max_results]
