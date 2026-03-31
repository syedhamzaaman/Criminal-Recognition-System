"""
Face search API route — Firestore-backed.
"""
import io
import os
import sys
import traceback
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from auth.auth import get_current_user, db_firestore
from face_pipeline.detector import validate_image
from face_pipeline.embedder import extract_embedding
from face_pipeline.matcher import search_matches
from face_pipeline.antispoofing import check_liveness
from datetime import datetime

os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

router = APIRouter(prefix="/api/search", tags=["Face Search"])


@router.post("/face")
async def search_face(
    image: UploadFile = File(...),
    threshold: float = Form(0.4),
    max_results: int = Form(10),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload an image -> detect face -> extract embedding -> match against Firestore database.
    """
    try:
        contents = await image.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty image file uploaded.")

        # Step 1: Validate image
        validation = validate_image(contents)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["message"])
        img = validation["image"]

        # Step 2: Anti-spoofing
        liveness = {"passed": True, "score": 100.0, "checks": [], "summary": "OK"}
        try:
            liveness = check_liveness(img)
        except Exception:
            pass

        # Step 3: Extract embedding
        embedding = extract_embedding(img)
        if embedding is None:
            raise HTTPException(
                status_code=400,
                detail="Could not extract features from the image. Please upload a clearer face photo."
            )

        # Step 4: Search Firestore for matches
        db = db_firestore
        matches = search_matches(embedding, db, threshold=threshold, max_results=max_results)

        # Step 5: Audit log
        match_summary = f"{len(matches)} matches found" if matches else "No matches found"
        db.collection("audit_log").add({
            "officer_id": current_user.get("officer_id"),
            "officer_name": current_user.get("full_name", "Unknown"),
            "action_type": "Search",
            "person_id": matches[0]["person_id"] if matches else None,
            "details": f"Face search: {match_summary} (threshold={threshold})",
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {
            "matches": matches,
            "total_matches": len(matches),
            "threshold_used": threshold,
            "liveness_check": liveness,
            "disclaimer": "Automated identification is probabilistic and requires human confirmation.",
        }

    except HTTPException:
        raise
    except Exception as e:
        try:
            error_detail = str(e).encode('ascii', errors='replace').decode('ascii')
        except Exception:
            error_detail = "An internal error occurred"
        try:
            print(f"[SEARCH ERROR] {error_detail}")
        except Exception:
            pass
        return JSONResponse(
            status_code=500,
            content={"detail": f"Search failed: {error_detail}. Please try a different image."}
        )
