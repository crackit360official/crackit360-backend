# db.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI
from dotenv import load_dotenv
import certifi
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "crackit360")

# ----------------------------------------------------
# ✅ CORRECT MongoDB Atlas connection (NO TLS OVERRIDES)
# ----------------------------------------------------
client = AsyncIOMotorClient(
    MONGO_URL,
    tls=True,
    tlsCAFile=certifi.where(),   # ⭐ CRITICAL FIX
    serverSelectionTimeoutMS=30000
)

db = client[DB_NAME]

# ----------------------------------------------------
# ✅ Collections
# ----------------------------------------------------
user_collection = db["User_details"]
quiz_collection = db["DailyQuizQuestions"]
quiz_student_collection = db["DailyQuizStudent"]
profile_collection = db["profile"]
technical_questions = db["TechnicalQuestions"]
technical_submissions = db["TechnicalSubmissions"]
discussion_col = db["Discussion"]
reply_col = db["Discussion_replies"]
vote_col=db['vote_col']
# 👉 Your speed test + quantitative collections
quantitative_collection = db["QuantitativeQuestions"]
speedtest_submissions = db["SpeedTestSubmissions"]  # FIXED NAME (your version was wrong)


# ----------------------------------------------------
# ✅ Test MongoDB connection
# ----------------------------------------------------
async def test_mongo_connection():
    try:
        await db.command("ping")
        print("✅ MongoDB ping successful!")
    except Exception as e:
        print("❌ MongoDB ping failed:", e)
        raise e


# ----------------------------------------------------
# ✅ Create indexes
# ----------------------------------------------------
async def create_indexes():
    await user_collection.create_index("email", unique=True)
    await quiz_collection.create_index("type")
    await quiz_student_collection.create_index("user_id")

    print("✅ MongoDB indexes created successfully.")


# ----------------------------------------------------
# ✅ Setup DB lifecycle events
# ----------------------------------------------------
def setup_db_events(app: FastAPI):
    @app.on_event("startup")
    async def startup_event():
        await test_mongo_connection()
        await create_indexes()
        print("🚀 MongoDB connected and indexes ready.")

    @app.on_event("shutdown")
    async def shutdown_event():
        client.close()
        print("🛑 MongoDB connection closed.")
