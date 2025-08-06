from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from ..database import get_database
from ..utils.security import get_password_hash, create_access_token, verify_password
from ..services.email_service import send_email
import secrets
import requests
import os
from dotenv import load_dotenv
from starlette.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

load_dotenv()

router = APIRouter(tags=["auth"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

async def get_user_by_email(db: AsyncIOMotorDatabase, email: str):
    user_data = await db.users.find_one({"email": email})
    return user_data

async def get_user_by_google_id(db: AsyncIOMotorDatabase, google_id: str):
    user_data = await db.users.find_one({"google_id": google_id})
    return user_data

@router.post("/signup")
async def signup(user_data: UserCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    db_user = await get_user_by_email(db, user_data.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    new_user = {
        "email": user_data.email,
        "hashed_password": hashed_password,
        "name": None,
        "google_id": None
    }
    result = await db.users.insert_one(new_user)
    return {"message": "User created successfully", "id": str(result.inserted_id)}

@router.post("/login")
async def login(user_data: UserLogin, db: AsyncIOMotorDatabase = Depends(get_database)):
    user = await get_user_by_email(db, user_data.email)
    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["email"]})
    return {"message": "Login successful", "token": access_token}

# Google OAuth2
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

@router.get("/auth/google")
async def google_auth():
    # ... (code remains the same as it's not database-related)
    scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile openid"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={google_client_id}"
        f"&redirect_uri={google_redirect_uri}&scope={scope}"
    )
    return RedirectResponse(auth_url)

@router.get("/auth/google/callback")
async def google_callback(code: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "code": code,
        "redirect_uri": google_redirect_uri,
        "grant_type": "authorization_code",
    }
    
    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()
    access_token = token_json.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get access token")

    user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info_response = requests.get(user_info_url, headers=headers)
    user_info_json = user_info_response.json()

    user_email = user_info_json.get("email")
    user_name = user_info_json.get("name")
    google_id = user_info_json.get("sub")
    
    db_user = await get_user_by_email(db, user_email)
    
    if not db_user:
        # Generate a random password for the user
        random_password = secrets.token_urlsafe(16)
        hashed_password = get_password_hash(random_password)

        new_user = {
            "email": user_email,
            "hashed_password": hashed_password,
            "name": user_name,
            "google_id": google_id
        }
        await db.users.insert_one(new_user)

        # Send an email with the temporary password
        email_body = f"Hello {user_name},\n\nYour account has been created with Google.\n\nYour temporary password is: {random_password}\n\nPlease change it after you log in.\n\nThanks,\nThe Team"
        send_email(user_email, "Welcome to Our Platform!", email_body)
    
    # After successful login, generate a JWT token
    jwt_token = create_access_token(data={"sub": user_email})
    
    # Redirect to your React frontend with the token
    return RedirectResponse(url=f"http://localhost:3000/dashboard?token={jwt_token}")