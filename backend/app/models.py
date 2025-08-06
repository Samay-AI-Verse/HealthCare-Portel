from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserInDB(BaseModel):
    id: Optional[str] = Field(alias='_id')
    email: EmailStr
    hashed_password: str
    name: Optional[str] = None
    google_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str