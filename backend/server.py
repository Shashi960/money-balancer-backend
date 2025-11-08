from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class Expense(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    amount: float
    date: str
    category: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExpenseCreate(BaseModel):
    title: str
    amount: float
    date: str
    category: str

class Debt(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    amount: float
    reason: str
    date: str
    status: str  # "pending" or "paid"
    debt_type: str  # "gave" or "owe"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DebtCreate(BaseModel):
    name: str
    amount: float
    reason: str
    date: str
    status: str = "pending"
    debt_type: str

class DebtUpdate(BaseModel):
    status: str

class Limit(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = "limit_settings"
    weekly_limit: float
    monthly_limit: float

class LimitCreate(BaseModel):
    weekly_limit: float
    monthly_limit: float

class Summary(BaseModel):
    total_today: float
    total_week: float
    total_month: float
    weekly_limit: float
    monthly_limit: float
    remaining_week: float
    remaining_month: float
    money_gave: float
    money_owe: float
    weekly_warning: str  # "none", "yellow", "red"
    monthly_warning: str  # "none", "yellow", "red"


# Expense Routes
@api_router.post("/expenses", response_model=Expense)
async def create_expense(input: ExpenseCreate):
    expense_dict = input.model_dump()
    expense_obj = Expense(**expense_dict)
    
    doc = expense_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    await db.expenses.insert_one(doc)
    return expense_obj

@api_router.get("/expenses", response_model=List[Expense])
async def get_expenses(filter: Optional[str] = None):
    query = {}
    
    if filter:
        now = datetime.now(timezone.utc)
        if filter == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter == "week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = None
        
        if start_date:
            # Filter by date field (user-selected date) instead of timestamp
            query['date'] = {"$gte": start_date.strftime("%Y-%m-%d")}
    
    expenses = await db.expenses.find(query, {"_id": 0}).to_list(10000)
    
    for expense in expenses:
        if isinstance(expense['timestamp'], str):
            expense['timestamp'] = datetime.fromisoformat(expense['timestamp'])
    
    # Sort by date descending
    expenses.sort(key=lambda x: x['date'], reverse=True)
    
    return expenses

@api_router.patch("/expenses/{expense_id}", response_model=Expense)
async def update_expense(expense_id: str, input: ExpenseCreate):
    expense_dict = input.model_dump()
    
    result = await db.expenses.find_one_and_update(
        {"id": expense_id},
        {"$set": expense_dict},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Remove _id for response
    result.pop('_id', None)
    
    # Convert timestamp
    if isinstance(result['timestamp'], str):
        result['timestamp'] = datetime.fromisoformat(result['timestamp'])
    
    return Expense(**result)

@api_router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str):
    result = await db.expenses.delete_one({"id": expense_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted successfully"}


# Debt Routes
@api_router.post("/debts", response_model=Debt)
async def create_debt(input: DebtCreate):
    debt_dict = input.model_dump()
    debt_obj = Debt(**debt_dict)
    
    doc = debt_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    await db.debts.insert_one(doc)
    return debt_obj

@api_router.get("/debts", response_model=List[Debt])
async def get_debts():
    debts = await db.debts.find({}, {"_id": 0}).to_list(10000)
    
    for debt in debts:
        if isinstance(debt['timestamp'], str):
            debt['timestamp'] = datetime.fromisoformat(debt['timestamp'])
    
    # Sort by date descending
    debts.sort(key=lambda x: x['date'], reverse=True)
    
    return debts

@api_router.patch("/debts/{debt_id}", response_model=Debt)
async def update_debt(debt_id: str, input: DebtUpdate):
    result = await db.debts.find_one_and_update(
        {"id": debt_id},
        {"$set": {"status": input.status}},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Debt not found")
    
    # Remove _id for response
    result.pop('_id', None)
    
    # Convert timestamp
    if isinstance(result['timestamp'], str):
        result['timestamp'] = datetime.fromisoformat(result['timestamp'])
    
    return Debt(**result)

@api_router.delete("/debts/{debt_id}")
async def delete_debt(debt_id: str):
    result = await db.debts.delete_one({"id": debt_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Debt not found")
    return {"message": "Debt deleted successfully"}


# Limit Routes
@api_router.post("/limit", response_model=Limit)
async def create_or_update_limit(input: LimitCreate):
    limit_obj = Limit(id="limit_settings", **input.model_dump())
    
    doc = limit_obj.model_dump()
    
    # Upsert (update or insert)
    await db.limits.update_one(
        {"id": "limit_settings"},
        {"$set": doc},
        upsert=True
    )
    
    return limit_obj

@api_router.get("/limit", response_model=Optional[Limit])
async def get_limit():
    limit = await db.limits.find_one({"id": "limit_settings"}, {"_id": 0})
    
    if not limit:
        # Return default limits
        return Limit(id="limit_settings", weekly_limit=0, monthly_limit=0)
    
    return Limit(**limit)


# Summary Route
@api_router.get("/summary", response_model=Summary)
async def get_summary():
    now = datetime.now(timezone.utc)
    
    # Get today's date
    today_date = now.strftime("%Y-%m-%d")
    
    # Get week start date
    week_start = now - timedelta(days=now.weekday())
    week_start_date = week_start.strftime("%Y-%m-%d")
    
    # Get month start date
    month_start = now.replace(day=1)
    month_start_date = month_start.strftime("%Y-%m-%d")
    
    # Get expenses
    all_expenses = await db.expenses.find({}, {"_id": 0}).to_list(10000)
    
    total_today = sum(e['amount'] for e in all_expenses if e['date'] == today_date)
    total_week = sum(e['amount'] for e in all_expenses if e['date'] >= week_start_date)
    total_month = sum(e['amount'] for e in all_expenses if e['date'] >= month_start_date)
    
    # Get limits
    limit = await db.limits.find_one({"id": "limit_settings"}, {"_id": 0})
    if not limit:
        weekly_limit = 0
        monthly_limit = 0
    else:
        weekly_limit = limit['weekly_limit']
        monthly_limit = limit['monthly_limit']
    
    # Calculate remaining
    remaining_week = weekly_limit - total_week
    remaining_month = monthly_limit - total_month
    
    # Calculate warnings
    weekly_warning = "none"
    if weekly_limit > 0:
        weekly_percent = (total_week / weekly_limit) * 100
        if weekly_percent >= 100:
            weekly_warning = "red"
        elif weekly_percent >= 80:
            weekly_warning = "yellow"
    
    monthly_warning = "none"
    if monthly_limit > 0:
        monthly_percent = (total_month / monthly_limit) * 100
        if monthly_percent >= 100:
            monthly_warning = "red"
        elif monthly_percent >= 80:
            monthly_warning = "yellow"
    
    # Get debts
    all_debts = await db.debts.find({}, {"_id": 0}).to_list(10000)
    money_gave = sum(d['amount'] for d in all_debts if d['debt_type'] == 'gave' and d['status'] == 'pending')
    money_owe = sum(d['amount'] for d in all_debts if d['debt_type'] == 'owe' and d['status'] == 'pending')
    
    return Summary(
        total_today=total_today,
        total_week=total_week,
        total_month=total_month,
        weekly_limit=weekly_limit,
        monthly_limit=monthly_limit,
        remaining_week=remaining_week,
        remaining_month=remaining_month,
        money_gave=money_gave,
        money_owe=money_owe,
        weekly_warning=weekly_warning,
        monthly_warning=monthly_warning
    )


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()