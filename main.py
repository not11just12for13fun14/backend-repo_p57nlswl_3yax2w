import os
from datetime import datetime, date
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents
from schemas import Habit as HabitSchema, HabitEntry as HabitEntrySchema


app = FastAPI(title="Islamic Habit Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Utilities
# -----------------------------

def _serialize_doc(doc: dict):
    if not doc:
        return None
    out = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = str(v)
        elif isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _serialize_list(docs: List[dict]):
    return [_serialize_doc(d) for d in docs]


def _today_date() -> date:
    return datetime.utcnow().date()


# -----------------------------
# Health & Root
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Islamic Habit Tracker Backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# -----------------------------
# Habit Endpoints
# -----------------------------
class HabitCreate(BaseModel):
    title: str = Field(...)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field("sonstiges")
    frequency: str = Field("daily")
    goal_per_period: int = Field(1, ge=1)
    color: Optional[str] = Field(None)


@app.post("/api/habits")
async def create_habit(payload: HabitCreate):
    habit = HabitSchema(**payload.model_dump())
    new_id = create_document("habit", habit)
    return {"id": new_id}


@app.get("/api/habits")
async def list_habits():
    habits = get_documents("habit", {}, None)
    today = _today_date()
    result = []
    for h in habits:
        hid = str(h.get("_id"))
        entry = db["habitentry"].find_one(
            {"habit_id": hid, "entry_date": today}
        )
        data = _serialize_doc(h)
        data["today_completed"] = bool(entry and entry.get("completed", False))
        result.append(data)
    return result


@app.post("/api/habits/{habit_id}/complete_today")
async def complete_today(habit_id: str):
    today = _today_date()
    existing = db["habitentry"].find_one({"habit_id": habit_id, "entry_date": today})
    if existing and existing.get("completed"):
        return {"status": "already_completed"}

    entry = HabitEntrySchema(habit_id=habit_id, entry_date=today, completed=True)
    # Upsert behavior
    db["habitentry"].update_one(
        {"habit_id": habit_id, "entry_date": today},
        {"$set": entry.model_dump() | {"updated_at": datetime.utcnow()} , "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"status": "completed"}


@app.delete("/api/habits/{habit_id}/complete_today")
async def uncomplete_today(habit_id: str):
    today = _today_date()
    res = db["habitentry"].delete_one({"habit_id": habit_id, "entry_date": today})
    return {"status": "removed" if res.deleted_count else "not_found"}


# Optional: get entries for a habit
@app.get("/api/habits/{habit_id}/entries")
async def get_entries(habit_id: str, limit: int = 30):
    items = db["habitentry"].find({"habit_id": habit_id}).sort("entry_date", -1).limit(limit)
    return [
        {
            "entry_date": (i.get("entry_date").isoformat() if isinstance(i.get("entry_date"), (datetime, date)) else i.get("entry_date")),
            "completed": bool(i.get("completed", False)),
        }
        for i in items
    ]


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
