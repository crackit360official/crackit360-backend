from fastapi import APIRouter, HTTPException
from db import db
from typing import List, Optional
from datetime import datetime
from db import QuantitativeQuestions,SpeedTestSubmissions 
from backend.schemas.models import SpeedTestQuestion,SubmitRequest
# ----------------------------------------------------------------------------
# Router Setup
# ----------------------------------------------------------------------------
router = APIRouter(
    prefix="/api/speed-test",
    tags=["Speed Test"]
)
# ----------------------------------------------------------------------------
# GET: Fetch Speed Test Questions (15 Questions)
# ----------------------------------------------------------------------------
@router.get("/questions", response_model=List[SpeedTestQuestion])
async def get_speed_test_questions(topic: str, level: str, limit: int = 15):

    try:
        cursor = QuantitativeQuestions.find(
            {"topic": topic, "level": level},
            {"_id": 0}  # remove mongo internal id
        ).limit(limit)

        questions = await cursor.to_list(length=limit)

        if not questions:
            raise HTTPException(
                status_code=404,
                detail="No questions found for this topic and level"
            )

        return questions

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# GET: Time Limit Calculation (Dynamic)
# ----------------------------------------------------------------------------
@router.get("/time-limit")
async def get_speed_test_time_limit(level: str, questions: int = 15):

    level_map = {
        "easy": 45,      # seconds per question
        "medium": 60,
        "hard": 90
    }

    time_per_q = level_map.get(level.lower())
    if not time_per_q:
        raise HTTPException(status_code=400, detail="Invalid level")

    return {"timeLimit": time_per_q * questions}


# ----------------------------------------------------------------------------
# POST: Submit Speed Test
# ----------------------------------------------------------------------------
@router.post("/submit")
async def submit_speed_test(data: SubmitRequest):

    try:
        # Fetch same 15 questions again to verify correctness
        cursor = QuantitativeQuestions.find(
            {"topic": data.topic, "level": data.level},
            {"_id": 0}
        ).limit(15)

        questions = await cursor.to_list(length=15)

        if not questions:
            raise HTTPException(status_code=404, detail="No questions found")

        total_questions = len(questions)
        score = 0
        results = []

        # Compare answers
        for i, q in enumerate(questions):
            user_answer_index = data.answers[i] if i < len(data.answers) else None
            correct_answer = q["correctAnswer"]

            is_correct = False
            if user_answer_index is not None:
                if q["options"][user_answer_index] == correct_answer:
                    is_correct = True
                    score += 1

            results.append({
                "question_id": q["id"],
                "user_answer_index": user_answer_index,
                "correct_answer": correct_answer,
                "is_correct": is_correct
            })

        # Save submission in DB
        submission_doc = {
            "user_id": data.user_id,
            "topic": data.topic,
            "level": data.level,
            "score": score,
            "total_questions": total_questions,
            "results": results,
            "submitted_at": datetime.utcnow()
        }

        await SpeedTestSubmissions.insert_one(submission_doc)

        return {
            "message": "Test submitted successfully",
            "score": score,
            "total": total_questions,
            "details": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
