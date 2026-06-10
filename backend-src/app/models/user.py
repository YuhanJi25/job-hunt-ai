from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    JOB_SEEKER = "job_seeker"
    RECRUITER = "recruiter"
    ADMIN = "admin"

class UserRegistration(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.JOB_SEEKER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    hashed_password: str
    role: UserRole
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserProfile(BaseModel):
    user: User
    skills: List[str] = []
    experience: List[str] = []
    applied_jobs: List[str] = []  # List of job IDs
    resume_file_path: Optional[str] = None
    preferences: Dict[str, Any] = {}

class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class UserApplication(BaseModel):
    user_id: str
    job_id: str
    application_data: Dict[str, Any] = {}
    applied_at: datetime
    status: str = "submitted"  # submitted, under_review, accepted, rejected
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
