# routers/quiz.py
from fastapi import APIRouter, HTTPException , Request
from db import quiz_collection, quiz_student_collection, user_collection
from schemas.models import QuizSubmissionPayload, DailyQuizStudent
from datetime import datetime
import random, time
from bson import ObjectId, errors as bson_errors
router = APIRouter(prefix="/api/quiz", tags=["quiz"])

# -----------------------------
# ✅ Helper: Format Question
# -----------------------------
def format_question(q):
    return {
        "id": str(q.get("_id", "")),
        "question": q.get("question", ""),
        "options": q.get("options", []),
        "correctAnswer": q.get("correctAnswer", 0),
        "explanation": q.get("explanation", ""),
        "difficulty": q.get("difficulty", "Easy"),
        "topic": q.get("topic", "General"),
    }


# -----------------------------
# ✅ Fetch Questions (random / ordered)
# -----------------------------
@router.get("/questions/{user_id}")
async def get_quiz_questions(user_id: str, mode: str = "random", limit: int = 5):
    from fastapi.responses import JSONResponse
    user_id = user_id.strip()
    print("✅ DEBUG: Route hit successfully")
    print("✅ DEBUG: user_id =", user_id)

# Count all questions
    total_questions = await quiz_collection.count_documents({})
    print("✅ DEBUG: Total questions in DB =", total_questions)

# Fetch one sample document
    sample = await quiz_collection.find_one({})
    print("✅ DEBUG: One sample question document =", sample)

   
    print("Incoming user_id:", user_id)
    def safe_objectid_list(ids):
        valid = []
        for i in ids:
            try:
                valid.append(ObjectId(i))
            except bson_errors.InvalidId:
                continue
        return valid

    try:
        student_record = await quiz_student_collection.find_one({"user_id": user_id})
        attempted_ids = student_record.get("attempted_ids", []) if student_record else []

        # 🧠 Safe ObjectId filtering
        available_questions = await quiz_collection.find({
        "_id": {"$nin": safe_objectid_list(attempted_ids)}
        }).to_list(length=None)
        if not available_questions:
            return JSONResponse(
                status_code=404,
                content={"questions": [], "message": "No new questions available for this user."}
            )
        # Select random or ordered questions
        if mode == "random":
            selected = random.sample(available_questions, min(limit, len(available_questions)))
        else:
            selected = available_questions[:limit]

        # Update attempted IDs
        new_ids = attempted_ids + [str(q["_id"]) for q in selected]
        await quiz_student_collection.update_one(
            {"user_id": user_id},
            {"$set": {"attempted_ids": new_ids}},
            upsert=True
        )

        return {"questions": [format_question(q) for q in selected]}

    except Exception as e:
        print("❌ Error fetching quiz questions:", e)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch quiz questions", "details": str(e)}
        )


# -----------------------------
# ✅ Submit Quiz
# -----------------------------
@router.post("/submit_quiz")
async def submit_quiz(request: Request):
    try:
        data = await request.json()
        user_id = data.get("student_id")
        answers = data.get("answers")
        start_time = data.get("start_time")

        if not user_id or not answers or not start_time:
            raise HTTPException(status_code=400, detail="Missing data fields")

        end_time = time.time()
        time_taken = end_time - start_time

        # ✅ Fetch only required fields
        all_questions = await quiz_collection.find(
            {}, {"_id": 1, "correctAnswer": 1}
        ).to_list(length=None)

        question_map = {str(q["_id"]): q["correctAnswer"] for q in all_questions}

        correct_count = 0
        for ans in answers:
            qid = ans.get("question_id")
            selected = ans.get("selected")

            if qid in question_map and selected == question_map[qid]:
                correct_count += 1

        quiz_score = correct_count

        # ✅ Bonus calculation (align with frontend)
        pct = max(0, 100 - ((time_taken / 300) * 100))  # 5 minutes → 300 sec

        bonus_score = (
            5 if pct >= 80 else
            4 if pct >= 60 else
            3 if pct >= 40 else
            2 if pct >= 20 else 1
        )

        total_score = quiz_score + bonus_score
        accuracy = (correct_count / len(answers)) * 100

        await quiz_student_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "quiz_score": quiz_score,
                "bonus_score": bonus_score,
                "total_score": total_score,
                "accuracy": accuracy,
                "time_taken": round(time_taken, 2),
                "date": datetime.utcnow()
            }},
            upsert=True
        )

        return {
            "message": "Quiz submitted successfully",
            "quiz_score": quiz_score,
            "bonus_score": bonus_score,
            "total_score": total_score,
            "accuracy": accuracy,
            "time_taken": round(time_taken, 2)
        }

    except Exception as e:
        print("❌ Error submitting quiz:", e)
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------
# ✅ Get Quiz Results
# -----------------------------
@router.get("/results/{user_id}")
async def get_results(user_id: str):
    try:
        query = {"user_id": user_id}

        cursor = quiz_student_collection.find(query).sort("date", -1)
        results = await cursor.to_list(length=50)
        formatted = []
        for r in results:
            formatted.append({
                "id": str(r["_id"]),
                "track": r.get("track", "General"),
                "score": r.get("quiz_score", 0),
                "bonus": r.get("bonus_score", 0),
                "total": r.get("total_score", 0),
                "accuracy": r.get("accuracy", 0),
                "timeTaken": r.get("time_taken", 0),
                "date": r.get("date", datetime.utcnow()).isoformat()
            })

        return {"results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# ✅ User Stats Overview
# -----------------------------
@router.get("/stats/{user_id}")
async def get_stats(user_id: str):
    try:
        cursor = quiz_student_collection.find({"user_id": user_id})
        attempts = await cursor.to_list(length=None)

        if not attempts:
            return {
                "totalAttempts": 0, "averageScore": 0, "averageAccuracy": 0,
                "totalTimeTaken": 0, "trackStats": {}
            }

        total_score = sum(a.get("quiz_score", 0) for a in attempts)
        total_accuracy = sum(a.get("accuracy", 0) for a in attempts)
        total_time = sum(a.get("time_taken", 0) for a in attempts)

        track_stats = {}
        for a in attempts:
            t = a.get("track", "General")
            s = track_stats.setdefault(t, {"attempts": 0, "totalScore": 0,
                                           "totalAccuracy": 0, "bestScore": 0})
            s["attempts"] += 1
            s["totalScore"] += a.get("quiz_score", 0)
            s["totalAccuracy"] += a.get("accuracy", 0)
            s["bestScore"] = max(s["bestScore"], a.get("quiz_score", 0))

        for t in track_stats:
            cnt = track_stats[t]["attempts"]
            track_stats[t]["averageScore"] = round(track_stats[t]["totalScore"] / cnt, 2)
            track_stats[t]["averageAccuracy"] = round(track_stats[t]["totalAccuracy"] / cnt, 2)

        return {
            "totalAttempts": len(attempts),
            "averageScore": round(total_score / len(attempts), 2),
            "averageAccuracy": round(total_accuracy / len(attempts), 2),
            "totalTimeTaken": total_time,
            "trackStats": track_stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
