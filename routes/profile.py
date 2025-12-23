from fastapi import APIRouter, HTTPException
from db import profile_collection
from schemas.models import Profile  # make sure the class name starts with capital 'P'
from bson import ObjectId

router = APIRouter(prefix="/profile", tags=["Profile Operations"])

# Route to insert profile data
@router.post("/Profile")
def create_profile(profile: Profile):
    data = {
        "name": profile.name,
        "age": profile.age
    }

    result = profile_collection.insert_one(data)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to insert data")

    return {"message": "Profile added successfully", "id": str(result.inserted_id)}
