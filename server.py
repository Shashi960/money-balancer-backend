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

    # ✅ Date range has TOP priority
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}

    # ✅ Quick filters
    elif filter:
        now = datetime.now(timezone.utc)

        if filter == "day":
            today = now.strftime("%Y-%m-%d")
            query["date"] = {"$gte": today, "$lte": today}

        elif filter == "week":
            start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
            query["date"] = {"$gte": start}

        elif filter == "month":
            start = now.replace(day=1).strftime("%Y-%m-%d")
            query["date"] = {"$gte": start}

    docs = await db.expenses.find(query, {"_id": 0}).to_list(10000)
    docs.sort(key=lambda x: x["date"], reverse=True)
    return docs

@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str):
    result = await db.expenses.delete_one({"id": expense_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"message": "Deleted"}

# ---------------- MIDDLEWARE ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
