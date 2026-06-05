# backend/auth.py
import os
from datetime import datetime, timedelta
from typing import Optional



from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase

# load env values
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Pydantic models
class UserIn(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, int((expire - datetime.utcnow()).total_seconds())

# Dependency to get DB (you can import your db object instead)
async def get_db(request: Request):
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection not initialized")
    return db

# register endpoint
@router.post("/register", response_model=UserOut)
async def register(user: UserIn, db: AsyncIOMotorDatabase = Depends(get_db)):
    users_col = db.users
    # check existing
    existing = await users_col.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user.password)
    doc = {"email": user.email, "password": hashed, "full_name": user.full_name}
    await users_col.insert_one(doc)
    return {"email": user.email, "full_name": user.full_name}

# login endpoint (OAuth2PasswordRequestForm compatible)
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_db)):
    users_col = db.users
    user_doc = await users_col.find_one({"email": form_data.username})
    if not user_doc:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not verify_password(form_data.password, user_doc.get("password")):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    token_payload = {"sub": user_doc["email"]}
    token, expires_seconds = create_access_token(token_payload, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_seconds}

# helper to get current user
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncIOMotorDatabase = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user_doc = await db.users.find_one({"email": email})
    if user_doc is None:
        raise credentials_exception
    # return simple dict or Pydantic model
    return user_doc

# change password request model
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/change-password")
async def change_password(req_data: ChangePasswordRequest, current_user: dict = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)):
    user_with_pw = await db.users.find_one({"email": current_user["email"]})
    if not user_with_pw or not verify_password(req_data.old_password, user_with_pw.get("password")):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    new_hashed = get_password_hash(req_data.new_password)
    await db.users.update_one(
        {"email": current_user["email"]},
        {"$set": {"password": new_hashed}}
    )
    return {"message": "Password updated successfully"}

