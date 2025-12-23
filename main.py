from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import time
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
# Import internal modules
from db import setup_db_events
from routes import quiz, auth
from schemas.models import Profile
from routes.technical.technical import router as technical_router, add_cors as technical_cors
import logging
from routes.discussion_router import router as discussion_router
# =========================================================
# ✅ Load Environment Variables
# =========================================================
logger = logging.getLogger("CrackIt360")
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")




# =========================================================
# ✅ Initialize FastAPI App
# =========================================================
app = FastAPI(
    title="CrackIt360 Backend",
    description="FastAPI backend powering CrackIt360 (Email + Google Auth, Quizzes, Technical Modules)",
    version="1.0",
)
# ===============================
# 422 VALIDATION ERROR DEBUGGER
# ===============================
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print("\n==================== 422 ERROR FOUND ====================")
    print("❌ BODY VALIDATION FAILED")
    print("➡ PATH:", request.url.path)
    print("➡ ERROR DETAILS:", exc.errors())

    try:
        body = await request.body()
        print("➡ RECEIVED BODY:", body.decode() if body else "EMPTY BODY")
    except Exception as e:
        print("➡ BODY READ FAILED:", str(e))

    print("=========================================================\n")

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# =========================================================
# ✅ CORS Configuration (Allow Frontend Requests)
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or your frontend domain
    allow_credentials=True,
    allow_methods=["*"],  # IMPORTANT
    allow_headers=["*"],
)


# =========================================================
# ✅ MongoDB Connection
# =========================================================
try:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.crackit360
    print("✅ MongoDB connected successfully:", MONGO_URL)
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    db = None


# =========================================================
# ✅ Include API Routers (With /api Prefix)
# =========================================================
app.include_router(auth.router)        # /api/auth/*
app.include_router(quiz.router)
technical_cors(app)
app.include_router(technical_router)
app.include_router(discussion_router)
# =========================================================
# ✅ Simple Profile API Example
# =========================================================
@app.post("/api/profile")
async def create_profile(profile: Profile):
    """
    Example endpoint to test MongoDB connectivity.
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")

    data = {"name": profile.name, "age": profile.age}
    result = await db.profile.insert_one(data)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to insert profile")

    return {"message": "Profile added successfully", "id": str(result.inserted_id)}


# =========================================================
# ✅ Serve React Frontend Build (if exists)
# =========================================================
frontend_dir = os.path.join(os.path.dirname(__file__), "../frontend/build")

if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    @app.get("/app/{path_name:path}")
    async def serve_react_app(path_name: str):
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "React build not found"}


# =========================================================
# ✅ Root Route (Health Check)
# =========================================================
@app.get("/")
async def root():
    return {
        "message": "🚀 CrackIt360 Backend Running Successfully",
        "frontend_connected": FRONTEND_URL,
        "database_connected": db is not None,
        "secret_loaded": bool(SECRET_KEY),
    }

@app.middleware("http")
async def logging_middleware(request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(
            f"❌ ERROR | {request.method} {request.url.path} | {process_time:.2f}ms | {str(e)}"
        )
        raise

    process_time = (time.time() - start_time) * 1000

    logger.info(
        f"➡ REQUEST | {request.method} {request.url.path} "
        f"| {response.status_code} | {process_time:.2f}ms"
    )

    return response

logging.basicConfig(
    filename="crackit360.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# =========================================================
# ✅ Register MongoDB Lifecycle Events
# =========================================================
setup_db_events(app)
