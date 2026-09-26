# backend/server.py
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
import os
import re
import hashlib
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta

try:
    from backend.auth import get_current_user, router as auth_router
except ImportError:
    from auth import get_current_user, router as auth_router

ROOT_DIR = Path(__file__).parent
# load_dotenv(ROOT_DIR / ".env")   # disable for Render

# Indian Standard Time (UTC+5:30) for accurate daily/weekly/monthly boundaries
IST = timezone(timedelta(hours=5, minutes=30))

# Configuration from .env (safe defaults)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
DB_NAME = os.getenv("DB_NAME", "money_balancer")
CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "*")

# Prepare CORS origins list
if CORS_ORIGINS_STR.strip() == "*" or CORS_ORIGINS_STR.strip() == "":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_STR.split(",") if o.strip()]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# MongoDB client will be created on startup
client: Optional[AsyncIOMotorClient] = None
db = None

app = FastAPI(title="Money Balancer API")

# Router with /api prefix
api_router = APIRouter(prefix="/api")


# ---------- Models ----------
class Expense(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    amount: float
    date: str  # store as "YYYY-MM-DD" string (UI selected date)
    category: str
    payment_mode: Optional[str] = "UPI"
    notes: Optional[str] = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_email: Optional[str] = None

class ExpenseCreate(BaseModel):
    title: str
    amount: float
    date: str
    category: str
    payment_mode: Optional[str] = "UPI"
    notes: Optional[str] = ""

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
    user_email: Optional[str] = None

class DebtCreate(BaseModel):
    name: str
    amount: float
    reason: str
    date: str
    status: str = "pending"
    debt_type: str

class DebtUpdate(BaseModel):
    status: Optional[str] = None
    name: Optional[str] = None
    amount: Optional[float] = None
    reason: Optional[str] = None
    date: Optional[str] = None
    debt_type: Optional[str] = None

class Limit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = "limit_settings"
    weekly_limit: float
    monthly_limit: float
    reminder_enabled: Optional[bool] = True
    reminder_time: Optional[str] = "21:00"

class LimitCreate(BaseModel):
    weekly_limit: float
    monthly_limit: float
    reminder_enabled: Optional[bool] = True
    reminder_time: Optional[str] = "21:00"

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

class MonthlyBreakdownItem(BaseModel):
    month: str  # "YYYY-MM"
    total: float
    count: int
    top_category: str
    categories: Dict[str, float]


# ---------- Startup / Shutdown ----------
@app.on_event("startup")
async def startup_db_client():
    global client, db
    logger.info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    app.state.db = db  # Store db in app state for dependencies
    try:
        await db.expenses.create_index("id", unique=True)
        await db.debts.create_index("id", unique=True)
        await db.limits.create_index("id", unique=True)
    except Exception as e:
        logger.info("Index creation skipped or failed: %s", e)
    
    # Create default user if not exists
    try:
        try:
            from backend.auth import get_password_hash
        except ImportError:
            from auth import get_password_hash
        
        users_col = db.users
        existing = await users_col.find_one({"email": "shashi789"})
        if not existing:
            hashed = get_password_hash("8050563255")
            await users_col.insert_one({
                "email": "shashi789",
                "password": hashed,
                "full_name": "Shashi"
            })
            logger.info("Created default user shashi789")

        existing_shashi68 = await users_col.find_one({"email": "Shashi68"})
        if not existing_shashi68:
            hashed_68 = get_password_hash("Shashi474232")
            await users_col.insert_one({
                "email": "Shashi68",
                "password": hashed_68,
                "full_name": "Shashi"
            })
            logger.info("Created default user Shashi68")
    except Exception as user_e:
        logger.error("Failed to create default user on startup: %s", user_e)
        
    logger.info("Connected to MongoDB: %s (db=%s)", MONGO_URI.split("@")[-1], DB_NAME)

@app.on_event("shutdown")
async def shutdown_db_client():
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed.")


# ---------- Expense Routes ----------
@api_router.post("/expenses", response_model=Expense)
async def create_expense(input: ExpenseCreate, current_user: dict = Depends(get_current_user)):
    expense_dict = input.model_dump()
    expense_obj = Expense(**expense_dict, user_email=current_user["email"])

    # store timestamp as datetime (UTC)
    doc = expense_obj.model_dump()
    if isinstance(doc.get("timestamp"), str):
        doc["timestamp"] = datetime.fromisoformat(doc["timestamp"])
    await db.expenses.insert_one(doc)
    return expense_obj

@api_router.get("/expenses", response_model=List[Expense])
async def get_expenses(
    filter: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    month: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query: Dict[str, Any] = {
        "$or": [
            {"user_email": current_user["email"]},
            {"user_email": {"$exists": False}}
        ]
    }
    # 1. Custom Date range filter (highest priority)
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}

    # 2. Specific Month filter (YYYY-MM)
    elif month:
        query["date"] = {"$gte": f"{month}-01", "$lte": f"{month}-31"}

    # 3. Quick filter
    elif filter and filter != "all":
        now = datetime.now(IST)
        if filter == "day":
            today_str = now.strftime("%Y-%m-%d")
            query["date"] = {"$gte": today_str, "$lte": today_str}
        elif filter == "week":
            start_date = now - timedelta(days=now.weekday())
            start_str = start_date.strftime("%Y-%m-%d")
            query["date"] = {"$gte": start_str}
        elif filter == "month":
            start_date = now.replace(day=1)
            start_str = start_date.strftime("%Y-%m-%d")
            query["date"] = {"$gte": start_str}
        elif filter == "last_month":
            first_this_month = now.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            query["date"] = {
                "$gte": last_month_start.strftime("%Y-%m-%d"),
                "$lte": last_month_end.strftime("%Y-%m-%d")
            }

    docs = await db.expenses.find(query, {"_id": 0}).to_list(length=10000)

    for d in docs:
        if isinstance(d.get("timestamp"), str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])

    docs.sort(key=lambda x: (x.get("date", ""), str(x.get("timestamp", ""))), reverse=True)
    return docs

@api_router.get("/monthly-summary", response_model=List[MonthlyBreakdownItem])
async def get_monthly_summary(current_user: dict = Depends(get_current_user)):
    query = {
        "$or": [
            {"user_email": current_user["email"]},
            {"user_email": {"$exists": False}}
        ]
    }
    docs = await db.expenses.find(query, {"_id": 0}).to_list(length=10000)
    monthly_map: Dict[str, Dict[str, Any]] = {}

    for d in docs:
        date_str = d.get("date", "")
        if len(date_str) >= 7:
            ym = date_str[:7]  # "YYYY-MM"
            amt = float(d.get("amount", 0))
            cat = d.get("category", "Other")
            if ym not in monthly_map:
                monthly_map[ym] = {"total": 0.0, "count": 0, "categories": {}}
            monthly_map[ym]["total"] += amt
            monthly_map[ym]["count"] += 1
            monthly_map[ym]["categories"][cat] = monthly_map[ym]["categories"].get(cat, 0.0) + amt

    result = []
    for ym, data in sorted(monthly_map.items(), key=lambda x: x[0], reverse=True):
        cats = data["categories"]
        top_cat = max(cats.items(), key=lambda x: x[1])[0] if cats else "None"
        result.append(
            MonthlyBreakdownItem(
                month=ym,
                total=round(data["total"], 2),
                count=data["count"],
                top_category=top_cat,
                categories={k: round(v, 2) for k, v in cats.items()}
            )
        )
    return result

@api_router.patch("/expenses/{expense_id}", response_model=Expense)
async def update_expense(expense_id: str, input: ExpenseCreate, current_user: dict = Depends(get_current_user)):
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.get("user_email") and expense.get("user_email") != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this expense")

    expense_dict = input.model_dump()
    expense_dict["user_email"] = current_user["email"]
    
    result = await db.expenses.find_one_and_update(
        {"id": expense_id},
        {"$set": expense_dict},
        return_document=ReturnDocument.AFTER
    )

    if not result:
        raise HTTPException(status_code=404, detail="Expense not found")

    result.pop("_id", None)
    if isinstance(result.get("timestamp"), str):
        result["timestamp"] = datetime.fromisoformat(result["timestamp"])
    return result

@api_router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str, current_user: dict = Depends(get_current_user)):
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.get("user_email") and expense.get("user_email") != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this expense")

    result = await db.expenses.delete_one({"id": expense_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted successfully"}


# ---------- Debt Routes ----------
@api_router.post("/debts", response_model=Debt)
async def create_debt(input: DebtCreate, current_user: dict = Depends(get_current_user)):
    debt_dict = input.model_dump()
    debt_obj = Debt(**debt_dict, user_email=current_user["email"])
    doc = debt_obj.model_dump()
    if isinstance(doc.get("timestamp"), str):
        doc["timestamp"] = datetime.fromisoformat(doc["timestamp"])
    await db.debts.insert_one(doc)
    return debt_obj

@api_router.get("/debts", response_model=List[Debt])
async def get_debts(current_user: dict = Depends(get_current_user)):
    query = {
        "$or": [
            {"user_email": current_user["email"]},
            {"user_email": {"$exists": False}}
        ]
    }
    docs = await db.debts.find(query, {"_id": 0}).to_list(length=10000)
    for d in docs:
        if isinstance(d.get("timestamp"), str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
    docs.sort(key=lambda x: x.get("date", ""), reverse=True)
    return docs

@api_router.patch("/debts/{debt_id}", response_model=Debt)
async def update_debt(debt_id: str, input: DebtUpdate, current_user: dict = Depends(get_current_user)):
    debt = await db.debts.find_one({"id": debt_id})
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    
    if debt.get("user_email") and debt.get("user_email") != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this debt")

    update_fields = {k: v for k, v in input.model_dump().items() if v is not None}
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    result = await db.debts.find_one_and_update(
        {"id": debt_id},
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER
    )
    if not result:
        raise HTTPException(status_code=404, detail="Debt not found")
    result.pop("_id", None)
    if isinstance(result.get("timestamp"), str):
        result["timestamp"] = datetime.fromisoformat(result["timestamp"])
    return result

@api_router.delete("/debts/{debt_id}")
async def delete_debt(debt_id: str, current_user: dict = Depends(get_current_user)):
    debt = await db.debts.find_one({"id": debt_id})
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    
    if debt.get("user_email") and debt.get("user_email") != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this debt")

    result = await db.debts.delete_one({"id": debt_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Debt not found")
    return {"message": "Debt deleted successfully"}


# ---------- Limit Routes ----------
@api_router.post("/limit", response_model=Limit)
async def create_or_update_limit(input: LimitCreate, current_user: dict = Depends(get_current_user)):
    limit_id = f"limit_{current_user['email']}"
    limit_obj = Limit(id=limit_id, **input.model_dump())
    doc = limit_obj.model_dump()
    await db.limits.update_one({"id": limit_id}, {"$set": doc}, upsert=True)
    return limit_obj

@api_router.get("/limit", response_model=Optional[Limit])
async def get_limit(current_user: dict = Depends(get_current_user)):
    limit_id = f"limit_{current_user['email']}"
    limit = await db.limits.find_one({"id": limit_id}, {"_id": 0})
    if not limit:
        legacy_limit = await db.limits.find_one({"id": "limit_settings"}, {"_id": 0})
        if legacy_limit:
            return Limit(
                id=limit_id,
                weekly_limit=legacy_limit.get("weekly_limit", 0),
                monthly_limit=legacy_limit.get("monthly_limit", 0),
                reminder_enabled=legacy_limit.get("reminder_enabled", True),
                reminder_time=legacy_limit.get("reminder_time", "21:00"),
            )
        return Limit(id=limit_id, weekly_limit=0, monthly_limit=0, reminder_enabled=True, reminder_time="21:00")
    return limit


# ---------- Summary Route ----------
@api_router.get("/summary", response_model=Summary)
async def get_summary(current_user: dict = Depends(get_current_user)):
    now = datetime.now(IST)

    today_date = now.strftime("%Y-%m-%d")
    week_start = now - timedelta(days=now.weekday())
    week_start_date = week_start.strftime("%Y-%m-%d")
    month_start = now.replace(day=1)
    month_start_date = month_start.strftime("%Y-%m-%d")

    expense_query = {
        "$or": [
            {"user_email": current_user["email"]},
            {"user_email": {"$exists": False}}
        ]
    }
    all_expenses = await db.expenses.find(expense_query, {"_id": 0}).to_list(length=10000)

    total_today = sum(e["amount"] for e in all_expenses if e.get("date") == today_date)
    total_week = sum(e["amount"] for e in all_expenses if e.get("date", "") >= week_start_date)
    total_month = sum(e["amount"] for e in all_expenses if e.get("date", "") >= month_start_date)

    limit_id = f"limit_{current_user['email']}"
    limit = await db.limits.find_one({"id": limit_id}, {"_id": 0})
    if not limit:
        limit = await db.limits.find_one({"id": "limit_settings"}, {"_id": 0})

    if not limit:
        weekly_limit = 0
        monthly_limit = 0
    else:
        weekly_limit = limit.get("weekly_limit", 0)
        monthly_limit = limit.get("monthly_limit", 0)

    remaining_week = weekly_limit - total_week
    remaining_month = monthly_limit - total_month

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

    debt_query = {
        "$or": [
            {"user_email": current_user["email"]},
            {"user_email": {"$exists": False}}
        ]
    }
    all_debts = await db.debts.find(debt_query, {"_id": 0}).to_list(length=10000)
    money_gave = sum(d["amount"] for d in all_debts if d.get("debt_type") == "gave" and d.get("status") == "pending")
    money_owe = sum(d["amount"] for d in all_debts if d.get("debt_type") == "owe" and d.get("status") == "pending")

    return Summary(
        total_today=round(total_today, 2),
        total_week=round(total_week, 2),
        total_month=round(total_month, 2),
        weekly_limit=round(weekly_limit, 2),
        monthly_limit=round(monthly_limit, 2),
        remaining_week=round(remaining_week, 2),
        remaining_month=round(remaining_month, 2),
        money_gave=round(money_gave, 2),
        money_owe=round(money_owe, 2),
        weekly_warning=weekly_warning,
        monthly_warning=monthly_warning,
    )


# ---------- Bank / UPI SMS Auto-Parser & Webhook Routes ----------
def make_user_sms_key(email: str) -> str:
    return hashlib.sha256(f"{email.lower().strip()}_mb_sms_webhook_v1".encode()).hexdigest()[:16]


def parse_indian_bank_sms(raw_text: str) -> Optional[Dict[str, Any]]:
    if not raw_text or not raw_text.strip():
        return None
    text = raw_text.strip()
    lower = text.lower()

    # Ignore OTP-only messages unless debit is explicitly mentioned
    if ("otp" in lower or "one time password" in lower or "verification code" in lower) and not any(
        w in lower for w in ["debited", "spent", "paid", "deducted", "sent"]
    ):
        return None

    # Check if debit/spend keywords exist
    debit_keywords = [
        "debited",
        "spent",
        "paid",
        "sent",
        "withdrawn",
        "purchase",
        "deducted",
        "txn of",
        "trf to",
        "transferred",
        "dr.",
        "dr ",
        "upi",
    ]
    is_credit_only = any(w in lower for w in ["credited", "received", "refund"]) and not any(
        w in lower for w in ["debited", "spent", "paid", "sent", "dr"]
    )
    if is_credit_only:
        return None

    if not any(k in lower for k in debit_keywords):
        return None

    # Extract amount: Rs. 450.00, INR 1,250.50, ₹85, debited by 210.00
    amount_patterns = [
        r"(?:rs\.?|inr|₹|amt)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        r"debited\s+(?:by|with|for)?\s*(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        r"spent\s+(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        r"paid\s+(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]
    amount = None
    for pat in amount_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1).replace(",", ""))
                if val > 0:
                    amount = round(val, 2)
                    break
            except ValueError:
                pass

    if not amount:
        return None

    # Extract merchant / payee
    payee = None
    payee_patterns = [
        r"(?:to\s+vpa|to|at|towards|trf\s+to|paid\s+to|sent\s+to)\s+([A-Za-z0-9_.\-@ &]{2,35}?)(?:\s+on\b|\s+ref\b|\s+upi\b|\s+via\b|\s+avl\b|\s+bal\b|\.|\,|$)",
        r"upi[\/\-][0-9]+[\/\-]([A-Za-z0-9_.\- ]{2,30}?)(?:[\/\-]|\.|\s|$)",
        r"info\s*:\s*([A-Za-z0-9_.\-\/ ]{3,35}?)(?:\.|\,|$)",
    ]
    for pat in payee_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip(" .,-:/")
            if candidate and not candidate.lower().startswith(("a/c", "ac ", "account", "xx", "card")):
                if "@" in candidate:
                    candidate = candidate.split("@")[0]
                candidate = re.sub(r"\s+", " ", candidate).strip()
                if len(candidate) >= 2:
                    payee = candidate.title()
                    break

    if not payee:
        payee = "Bank / UPI Debit"

    # Auto-detect category
    combined = f"{payee} {text}".lower()
    category = "Other"
    category_Keywords = {
        "Food": ["swiggy", "zomato", "food", "restaurant", "cafe", "coffee", "tea", "bakery", "hotel", "domino", "kfc", "mcdonald", "blinkit", "zepto", "bigbasket", "eatsure", "tiffin", "mess", "canteen", "milk"],
        "Travel": ["rapido", "uber", "ola", "irctc", "redbus", "bus", "metro", "bmtc", "petrol", "fuel", "hpcl", "bpcl", "iocl", "shell", "fastag", "toll", "auto", "cab", "train", "flight"],
        "Shopping": ["amazon", "flipkart", "myntra", "ajio", "meesho", "dmart", "reliance", "zudio", "decathlon", "mall", "store", "mart", "supermarket", "grocer"],
        "Bills": ["jio", "airtel", "vi ", "vodafone", "bsnl", "bescom", "electricity", "water", "gas", "broadband", "wifi", "recharge", "billdesk", "act fibernet", "tataplay", "bill"],
        "Entertainment": ["netflix", "spotify", "hotstar", "prime", "bookmyshow", "pvr", "inox", "youtube", "movie", "game"],
        "Healthcare": ["apollo", "medplus", "pharmacy", "hospital", "clinic", "doctor", "1mg", "pharmeasy", "medical", "health", "lab", "medicine"],
        "Education": ["udemy", "coursera", "college", "school", "fees", "book", "course", "tuition", "exam"],
    }
    for cat, words in category_Keywords.items():
        if any(w in combined for w in words):
            category = cat
            break

    today_ist = datetime.now(IST).strftime("%Y-%m-%d")
    return {
        "id": str(uuid.uuid4()),
        "title": payee,
        "amount": amount,
        "category": category,
        "date": today_ist,
        "raw_text": text[:500],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@api_router.get("/sms-webhook-info")
async def get_sms_webhook_info(current_user: dict = Depends(get_current_user)):
    key = make_user_sms_key(current_user["email"])
    await db.users.update_one(
        {"email": current_user["email"]},
        {"$set": {"sms_webhook_key": key}},
    )
    return {
        "webhook_key": key,
        "user_email": current_user["email"],
    }


@api_router.api_route("/sms-webhook/{webhook_key}", methods=["GET", "POST"])
async def receive_sms_webhook(
    webhook_key: str,
    request: Request,
    text: Optional[str] = Query(None),
    sender: Optional[str] = Query(None),
):
    # Find user by webhook_key or verify against default users
    user = await db.users.find_one({"sms_webhook_key": webhook_key})
    user_email = user["email"] if user else None

    if not user_email:
        all_users = await db.users.find({}, {"email": 1}).to_list(length=100)
        for u in all_users:
            if u.get("email") and make_user_sms_key(u["email"]) == webhook_key:
                user_email = u["email"]
                await db.users.update_one({"email": user_email}, {"$set": {"sms_webhook_key": webhook_key}})
                break

    if not user_email:
        raise HTTPException(status_code=404, detail="Invalid SMS webhook key")

    sms_text = text or ""
    if not sms_text and request.method == "POST":
        try:
            body = await request.json()
            sms_text = body.get("text") or body.get("message") or body.get("sms") or body.get("body") or ""
        except Exception:
            try:
                raw_bytes = await request.body()
                sms_text = raw_bytes.decode("utf-8", errors="ignore")
            except Exception:
                sms_text = ""

    parsed = parse_indian_bank_sms(sms_text)
    if not parsed:
        return {"status": "ignored", "reason": "Not a recognized debit SMS or no amount found"}

    parsed["user_email"] = user_email
    parsed["sender"] = sender or "Bank SMS"
    await db.pending_sms.insert_one(dict(parsed))
    return {"status": "queued", "item": parsed}


@api_router.get("/pending-sms")
async def get_pending_sms(current_user: dict = Depends(get_current_user)):
    query = {
        "status": "pending",
        "$or": [
            {"user_email": current_user["email"]},
            {"user_email": {"$exists": False}},
        ],
    }
    items = await db.pending_sms.find(query, {"_id": 0}).sort("created_at", -1).to_list(length=100)
    return items


@api_router.delete("/pending-sms/{sms_id}")
async def delete_pending_sms(sms_id: str, current_user: dict = Depends(get_current_user)):
    await db.pending_sms.delete_one({"id": sms_id})
    return {"message": "Pending SMS removed"}


# include router and middleware
app.include_router(api_router)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
