from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Body, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
import logging
from pydantic import BaseModel, ValidationError
from ...models.job import JobSearchQuery, JobSearchResult
from ...models.candidate import CandidateProfile
from ...models.reranking import (
    RerankingRequest, RerankingResponse, RerankingWeightsUpdate, 
    RerankingStatistics, RerankingExplanation
)
from ...services.hybrid_search_service import HybridSearchService
from ...services.resume_service import ResumeService
from ...services.reranking_service import RerankingService
from ...services.feature_engineering_service import FeatureEngineeringService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
hybrid_search_service = HybridSearchService()
resume_service = ResumeService()
reranking_service = RerankingService()
feature_service = FeatureEngineeringService()

class SelectedKeywords(BaseModel):
    """Model for selected keywords for reranking"""
    job_titles: List[str] = []
    skills: List[str] = []
    salary: Optional[Dict[str, int]] = None
    locations: List[str] = []


class RerankedSearchRequest(BaseModel):
    """Request model for reranked search (without keyword reranking)"""
    search_query: JobSearchQuery


@router.post("/search-reranked", response_model=JobSearchResult)
async def search_jobs_with_reranking(
    request: RerankedSearchRequest,
    user_description: Optional[str] = Query(None, description="User's specific job description or preferences"),
    include_explanations: bool = Query(False, description="Include detailed explanations for rankings")
):
    """
    Search for jobs with personalized reranking based on user description
    
    This endpoint performs a hybrid search and then reranks the results based on:
    - User's specific job description/preferences
    - Skill matching
    - Experience level compatibility
    - Location preferences
    - Salary expectations
    - Semantic similarity
    - Company preferences
    
    NOTE: Keyword-based reranking is NOT applied here. Use /rerank-with-keywords endpoint separately.
    """
    try:
        logger.info(f"Reranked search request received: query={request.search_query.query}")
        logger.debug(f"Full search query: {request.search_query}")
        
        # Perform regular reranked search (NO keyword-based reranking)
        results = hybrid_search_service.search_jobs_with_reranking(
            query=request.search_query,
            user_description=user_description,
            candidate_profile=None,
            reranking_factors=None,
            include_explanations=include_explanations
        )
        
        # Do NOT apply keyword-based reranking here - it's a separate service
        # Keyword reranking should only be called via /rerank-with-keywords endpoint
        
        return results
        
    except Exception as e:
        logger.error(f"Error in reranked search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error performing reranked search: {str(e)}")

@router.post("/search-reranked-with-resume", response_model=JobSearchResult)
async def search_jobs_with_reranking_and_resume(
    resume_file: UploadFile = File(...),
    query: str = Form(...),
    location: Optional[str] = Form(None),
    min_salary: Optional[int] = Form(None),
    job_type: Optional[str] = Form(None),
    experience_level: Optional[str] = Form(None),
    remote_allowed: Optional[bool] = Form(None),
    visa_sponsorship: Optional[bool] = Form(None),
    page: int = Form(1),
    page_size: int = Form(20),
    user_description: Optional[str] = Form(None),
    include_explanations: bool = Form(False),
    selected_keywords: Optional[str] = Form(None, description="JSON string of selected keywords")
):
    """
    Search for jobs with personalized reranking using uploaded resume
    
    This endpoint:
    1. Processes the uploaded resume to extract candidate profile
    2. Performs hybrid search
    3. Reranks results based on resume content and user description
    4. Returns personalized job recommendations
    """
    try:
        logger.info(f"Reranked search with resume: {query}")
        
        # Create JobSearchQuery from form parameters
        search_query = JobSearchQuery(
            query=query,
            location=location,
            min_salary=min_salary,
            job_type=job_type,
            experience_level=experience_level,
            remote_allowed=remote_allowed,
            visa_sponsorship=visa_sponsorship,
            page=page,
            page_size=page_size
        )
        
        # Process the uploaded resume
        candidate_id = f"temp_{hash(resume_file.filename)}"
        
        # Save uploaded file
        file_content = await resume_file.read()
        upload_record = await resume_service.save_uploaded_file(
            file_content, resume_file.filename, candidate_id
        )
        
        # Process resume to extract candidate profile
        file_path = f"{resume_service.upload_dir}/{upload_record.file_name}"
        candidate_profile = await resume_service.process_resume_file(
            file_path, candidate_id
        )
        
        # Perform reranked search
        results = hybrid_search_service.search_jobs_with_reranking(
            query=search_query,
            user_description=user_description,
            candidate_profile=candidate_profile,
            reranking_factors=None,
            include_explanations=include_explanations
        )
        
        # Apply keyword-based reranking if keywords are provided
        if selected_keywords:
            try:
                import json
                keyword_dict = json.loads(selected_keywords)
                results = reranking_service.rerank_with_keywords(
                    search_results=results,
                    selected_keywords=keyword_dict,
                    base_rerank_score=None
                )
            except Exception as e:
                logger.warning(f"Error parsing selected_keywords: {e}")
        
        logger.info(f"Extracted candidate: {candidate_profile.candidate.name}")
        logger.info(f"Found {len(results.jobs)} reranked jobs")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in reranked search with resume: {e}")
        raise HTTPException(status_code=500, detail="Error processing resume or performing reranked search")

@router.post("/personalized-recommendations", response_model=JobSearchResult)
async def get_personalized_recommendations(
    resume_file: UploadFile = File(...),
    user_description: Optional[str] = Form(None),
    limit: int = Form(10),
    include_explanations: bool = Form(True)
):
    """
    Get personalized job recommendations based on resume analysis
    
    This endpoint:
    1. Analyzes the uploaded resume
    2. Creates a personalized search query based on candidate skills
    3. Performs reranked search with candidate profile
    4. Returns top personalized job recommendations
    """
    try:
        logger.info(f"Personalized recommendations request for: {resume_file.filename}")
        
        # Process the uploaded resume
        candidate_id = f"temp_{hash(resume_file.filename)}"
        
        # Save uploaded file
        file_content = await resume_file.read()
        upload_record = await resume_service.save_uploaded_file(
            file_content, resume_file.filename, candidate_id
        )
        
        # Process resume to extract candidate profile
        file_path = f"{resume_service.upload_dir}/{upload_record.file_name}"
        candidate_profile = await resume_service.process_resume_file(
            file_path, candidate_id
        )
        
        # Get personalized recommendations
        results = hybrid_search_service.get_personalized_recommendations(
            candidate_profile=candidate_profile,
            user_description=user_description,
            limit=limit,
            reranking_factors=None
        )
        
        # Add explanations if requested
        if include_explanations and results.jobs:
            explanations = {}
            for job in results.jobs[:5]:  # Explain top 5 jobs
                explanations[job.id] = reranking_service.get_reranking_explanation(
                    job, user_description, candidate_profile
                )
            results.explanations = explanations
        
        logger.info(f"Generated {len(results.jobs)} personalized recommendations for {candidate_profile.candidate.name}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error generating personalized recommendations: {e}")
        raise HTTPException(status_code=500, detail="Error generating personalized recommendations")

@router.post("/reranking-explanation/{job_id}", response_model=RerankingExplanation)
async def get_reranking_explanation(
    job_id: str,
    search_query: Optional[str] = Query(None, description="Original search query text"),
    user_description: Optional[str] = Query(None, description="User's specific job description or preferences"),
    resume_file: Optional[UploadFile] = File(None)
):
    """
    Get detailed explanation of why a specific job was ranked as it was
    
    This endpoint provides detailed breakdown of the reranking factors
    that influenced the ranking of a specific job. Requires POST to support 
    file upload for resume-based personalized explanations.
    """
    try:
        # Get job details
        job = hybrid_search_service.es_service.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if search_query:
            job.feature_vector = feature_service.build_feature_vector(
                query_text=search_query,
                job=job
            )
        
        candidate_profile = None
        
        # Process resume if provided
        if resume_file:
            candidate_id = f"temp_{hash(resume_file.filename)}"
            
            # Save uploaded file
            file_content = await resume_file.read()
            upload_record = await resume_service.save_uploaded_file(
                file_content, resume_file.filename, candidate_id
            )
            
            # Process resume to extract candidate profile
            file_path = f"{resume_service.upload_dir}/{upload_record.file_name}"
            candidate_profile = await resume_service.process_resume_file(
                file_path, candidate_id
            )
        
        # Get reranking explanation
        explanation = reranking_service.get_reranking_explanation(
            job=job,
            user_description=user_description,
            candidate_profile=candidate_profile
        )
        
        return explanation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reranking explanation: {e}")
        raise HTTPException(status_code=500, detail="Error getting reranking explanation")

@router.put("/reranking-weights", response_model=Dict[str, str])
async def update_reranking_weights(weights_update: RerankingWeightsUpdate):
    """
    Update the weights used for reranking factors
    
    This endpoint allows customization of how different factors
    are weighted in the reranking algorithm.
    """
    try:
        weights_dict = weights_update.to_dict()
        
        if not weights_dict:
            raise HTTPException(status_code=400, detail="No weights provided")
        
        success = reranking_service.update_reranking_weights(weights_dict)
        
        if success:
            return {
                "message": "Reranking weights updated successfully",
                "new_weights": reranking_service.weights
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid weights provided")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reranking weights: {e}")
        raise HTTPException(status_code=500, detail="Error updating reranking weights")

@router.get("/reranking-weights", response_model=Dict[str, float])
async def get_reranking_weights():
    """
    Get current reranking weights
    
    Returns the current weights used for different reranking factors.
    """
    try:
        return reranking_service.weights
        
    except Exception as e:
        logger.error(f"Error getting reranking weights: {e}")
        raise HTTPException(status_code=500, detail="Error getting reranking weights")

@router.get("/reranking-statistics", response_model=Dict[str, Any])
async def get_reranking_statistics():
    """
    Get reranking service statistics and performance metrics
    
    Returns statistics about the reranking service performance
    and current configuration.
    """
    try:
        stats = {
            "current_weights": reranking_service.weights,
            "service_status": "active",
            "supported_factors": list(reranking_service.weights.keys()),
            "factor_descriptions": {
                "skill_match": "Technical skills alignment between job and candidate",
                "experience_match": "Experience level compatibility",
                "location_preference": "Location preferences alignment",
                "salary_expectation": "Salary expectation compatibility",
                "semantic_similarity": "Semantic content similarity",
                "company_preference": "Company/industry preferences"
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting reranking statistics: {e}")
        raise HTTPException(status_code=500, detail="Error getting reranking statistics")

@router.post("/rerank-with-keywords", response_model=JobSearchResult)
async def rerank_with_keywords(
    request: Dict[str, Any] = Body(..., description="Request containing search_results and selected_keywords")
):
    """
    Rerank existing search results based on selected keywords with weighted scoring
    
    This is a separate reranking service specifically for keyword-based reranking.
    It takes existing search results and reranks them based on user-selected keywords
    with configurable weights for each keyword category.
    
    Request body:
    {
        "search_results": JobSearchResult,
        "selected_keywords": {
            "job_titles": List[str],
            "skills": List[str],
            "salary": Optional[Dict[str, int]],
            "locations": List[str]
        },
        "keyword_weights": Optional[Dict[str, float]]  # Custom weights (optional)
    }
    """
    try:
        search_results_dict = request.get("search_results")
        selected_keywords_dict = request.get("selected_keywords", {})
        keyword_weights = request.get("keyword_weights")
        
        if not search_results_dict:
            raise HTTPException(status_code=400, detail="search_results is required")
        
        # Convert dict to JobSearchResult model
        from ...models.job import Job
        # Handle job conversion if needed
        if "jobs" in search_results_dict and search_results_dict["jobs"]:
            # Jobs might be dicts, convert them
            jobs_list = []
            for job_dict in search_results_dict["jobs"]:
                if isinstance(job_dict, dict):
                    jobs_list.append(Job(**job_dict))
                else:
                    jobs_list.append(job_dict)
            search_results_dict["jobs"] = jobs_list
        
        search_results = JobSearchResult(**search_results_dict)
        
        logger.info(f"Reranking {len(search_results.jobs)} jobs with keywords: {selected_keywords_dict}")
        
        # Apply keyword-based reranking with custom weights if provided
        results = reranking_service.rerank_with_keywords(
            search_results=search_results,
            selected_keywords=selected_keywords_dict,
            base_rerank_score=None,
            keyword_weights=keyword_weights
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in keyword-based reranking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error performing keyword-based reranking: {str(e)}")


@router.post("/test-reranking", response_model=Dict[str, Any])
async def test_reranking_service():
    """
    Test the reranking service with sample data
    
    This endpoint tests the reranking service with sample data
    to verify it's working correctly.
    """
    try:
        # Create sample data for testing
        from ...models.job import Job, Location, Salary, JobType, ExperienceLevel
        from datetime import datetime
        
        sample_job = Job(
            id="test_job_1",
            title="Senior Software Engineer",
            description="We are looking for a senior software engineer with Python and React experience.",
            company_name="TechCorp",
            location=Location(city="San Francisco", state="CA", country="USA"),
            job_type=JobType.FULL_TIME,
            experience_level=ExperienceLevel.SENIOR,
            salary=Salary(min_salary=120000, max_salary=150000),
            required_skills=["Python", "React", "JavaScript", "AWS"],
            posted_date=datetime.now()
        )
        
        # Test reranking with sample data
        test_result = reranking_service.get_reranking_explanation(
            job=sample_job,
            user_description="Looking for a senior software engineering role with Python and React",
            candidate_profile=None
        )
        
        return {
            "status": "success",
            "message": "Reranking service is working correctly",
            "test_result": test_result,
            "current_weights": reranking_service.weights
        }
        
    except Exception as e:
        logger.error(f"Error testing reranking service: {e}")
        raise HTTPException(status_code=500, detail="Error testing reranking service")
