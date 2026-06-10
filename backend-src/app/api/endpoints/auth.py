from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime
import logging
from ...models.user import UserRegistration, UserLogin, UserResponse, Token, UserApplication
from ...services.auth_service import auth_service
from ...services.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Initialize knowledge graph service
kg_service = KnowledgeGraphService()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(token)
    return auth_service.create_user_response(user)

@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserRegistration):
    """Register a new user"""
    try:
        # Register user in auth service
        user = auth_service.register_user(user_data)
        
        # Create user node in knowledge graph
        kg_service.create_user_node(user)
        
        logger.info(f"User registered successfully: {user.email}")
        return auth_service.create_user_response(user)
        
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user"
        )

@router.post("/login", response_model=Token)
async def login_user(login_data: UserLogin):
    """Login user and return access token"""
    try:
        token = auth_service.login_user(login_data)
        logger.info(f"User logged in: {login_data.email}")
        return token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error logging in user"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/apply/{job_id}")
async def apply_to_job(
    job_id: str,
    application_data: dict,
    current_user: UserResponse = Depends(get_current_user)
):
    """Apply to a job"""
    try:
        # Create application record
        application = UserApplication(
            user_id=current_user.id,
            job_id=job_id,
            application_data=application_data,
            applied_at=datetime.utcnow()
        )
        
        # Update knowledge graph with application relationship
        kg_service.create_application_relationship(current_user.id, job_id, application_data)
        
        logger.info(f"User {current_user.email} applied to job {job_id}")
        return {"message": "Application submitted successfully", "application_id": f"{current_user.id}_{job_id}"}
        
    except Exception as e:
        logger.error(f"Error applying to job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error submitting application"
        )

@router.get("/applications")
async def get_user_applications(current_user: UserResponse = Depends(get_current_user)):
    """Get user's job applications"""
    try:
        applications = kg_service.get_user_applications(current_user.id)
        return {"applications": applications}
        
    except Exception as e:
        logger.error(f"Error getting user applications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving applications"
        )
