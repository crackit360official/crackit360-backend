# judge.py
import httpx
import os

JUDGE0_URL = "https://judge0-ce.p.rapidapi.com/submissions?base64_encoded=false&wait=true"

HEADERS = {
    "x-rapidapi-host": "judge0-ce.p.rapidapi.com",
    "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
    "content-type": "application/json"
}

LANGUAGE_MAP = {
    "Python": 71,
    "C": 50,
    "C++": 54,
    "Java": 62
}

async def run_code(language: str, code: str, stdin: str = ""):
    lang_id = LANGUAGE_MAP.get(language, 71)

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            JUDGE0_URL,
            headers=HEADERS,
            json={
                "language_id": lang_id,
                "source_code": code,
                "stdin": stdin,
                "cpu_time_limit": 3,
                "memory_limit": 512000,
            }
        )
        data = res.json()

        return {
            "stdout": (data.get("stdout") or "").strip(),
            "stderr": (data.get("stderr") or "").strip(),
            "compile_output": (data.get("compile_output") or "").strip(),
            "time": float(data.get("time") or 0),
            "memory": float(data.get("memory") or 0),
            "status": data.get("status", {}).get("description", "")
        }
