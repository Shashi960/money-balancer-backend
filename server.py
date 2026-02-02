from fastapi import FastAPI, APIRouter, HTTPException
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import os
import logging

# ---------------- CONFIG ----------------
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "money_balancer")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Money Balancer API")
router = APIRouter(prefix="/api")

client = None
db = None

# ---------------- MODELS ----------------
class Expense(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    amount: float
    date: str  # YYYY-MM-DD
    category: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExpenseCreate(BaseModel):
    title: str
    amount: float
    date: str
    category: str

# ---------------- STARTUP ----------------
@app.on_event("startup")
async def startup():
    global client, db
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    logger.info("MongoDB connected")

@app.on_event("shutdown")
async def shutdown():
    client.close()

# ---------------- EXPENSE APIs ----------------
@router.post("/expenses", response_model=Expense)
async def create_expense(expense: ExpenseCreate):
    obj = Expense(**expense.dict())
    await db.expenses.insert_one(obj.dict())
    return obj

@router.get("/expenses", response_model=List[Expense])
async def get_expenses(
    filter: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    query = {}

    # ✅ DATE RANGE (HIGHEST PRIORITY)
    if from_date and to_date:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )

        query["timestamp"] = {
            "$gte": from_dt,
            "$lte": to_dt
        }

    # ✅ QUICK FILTERS
    elif filter:
        now = datetime.now(timezone.utc)

        if filter == "day":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            query["timestamp"] = {"$gte": start, "$lt": end}

        elif filter == "week":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            query["timestamp"] = {"$gte": start}

        elif filter == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query["timestamp"] = {"$gte": start}

    docs = await db.expenses.find(query, {"_id": 0}).to_list(10000)
    docs.sort(key=lambda x: x["timestamp"], reverse=True)
    return docs


@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str):
    result = await db.expenses.delete_one({"id": expense_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"message": "Deleted"}

# 🔧 TEMP FIX – run once, then REMOVE
@router.post("/fix-expense-timestamps")
async def fix_expense_timestamps():
    expenses = await db.expenses.find({}).to_list(10000)

    updated = 0
    for e in expenses:
        date_str = e.get("date")
        if not date_str:
            continue

        correct_ts = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=12, tzinfo=timezone.utc
        )

        await db.expenses.update_one(
            {"id": e["id"]},
            {"$set": {"timestamp": correct_ts}}
        )
        updated += 1

    return {"status": "timestamps fixed", "updated": updated}




# ---------------- MIDDLEWARE ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
