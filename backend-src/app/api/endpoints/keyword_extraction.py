from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import logging
from pydantic import BaseModel
from ...services.keyword_extraction_service import KeywordExtractionService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize service
keyword_extraction_service = KeywordExtractionService()


class KeywordExtractionRequest(BaseModel):
    """Request model for keyword extraction"""
    query: str


class KeywordExtractionResponse(BaseModel):
    """Response model for keyword extraction"""
    job_titles: List[str]
    skills: List[str]
    salary: Optional[Dict[str, int]] = None
    locations: List[str]


@router.post("/extract", response_model=KeywordExtractionResponse)
async def extract_keywords(request: KeywordExtractionRequest):
    """
    Extract structured keywords from user search query
    
    This endpoint analyzes the user's search query and extracts:
    - Job titles (e.g., "Software Engineer", "Data Scientist")
    - Skills (e.g., "React", "Python", "AWS")
    - Salary range (e.g., $80k - $100k)
    - Locations (e.g., "California", "San Francisco, CA")
    
    Args:
        request: KeywordExtractionRequest containing the query text
        
    Returns:
        KeywordExtractionResponse with extracted keywords organized by category
    """
    try:
        logger.info(f"Extracting keywords from query: {request.query[:100]}...")
        
        # Extract keywords using the service
        keywords = keyword_extraction_service.extract_keywords(request.query)
        
        return KeywordExtractionResponse(
            job_titles=keywords.get("job_titles", []),
            skills=keywords.get("skills", []),
            salary=keywords.get("salary"),
            locations=keywords.get("locations", [])
        )
        
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting keywords: {str(e)}"
        )

