from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
router = APIRouter(prefix="/api/technical")
# ----------------------------
#  MongoDB Connection
# ----------------------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.crackit360
technical_questions = db["TechnicalQuestions"]
def add_cors(app):
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
# ----------------------------
#  GET ALL TECHNICAL QUESTIONS
# ----------------------------
@router.get("/questions/")
async def get_questions():
    try:
        questions = []
        cursor = technical_questions.find({})
       
        async for q in cursor:
            q["_id"] = str(q["_id"])
            questions.append(q)

        return {"questions": questions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.options("/questions/")
async def preflight_questions():
    return JSONResponse(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )