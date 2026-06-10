from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional, Dict, Any
import logging
from ...services.data_ingestion_service import DataIngestionService
from ...core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize the data ingestion service
ingestion_service = DataIngestionService()

@router.post("/ingest/rise")
async def ingest_rise_jobs(
    background_tasks: BackgroundTasks,
    page: int = Query(1, ge=1, description="Page number to fetch from Rise API"),
    limit: int = Query(20, ge=1, le=100, description="Number of jobs per page"),
    location: Optional[str] = Query(None, description="Location filter for jobs"),
    async_processing: bool = Query(False, description="Process in background")
) -> Dict[str, Any]:
    """
    Ingest jobs from Rise API
    
    This endpoint fetches jobs from the Rise API and processes them through the complete pipeline:
    1. Fetch jobs from Rise API
    2. Process with NLP (extract entities, skills)
    3. Index to Elasticsearch
    4. Create nodes and relationships in Neo4j
    
    Args:
        page: Page number to fetch (default: 1)
        limit: Number of jobs per page (default: 20, max: 100)
        location: Optional location filter
        async_processing: If True, process in background and return immediately
    
    Returns:
        Dict containing ingestion results and statistics
    """
    try:
        if async_processing:
            # Process in background
            background_tasks.add_task(
                ingestion_service.ingest_rise_jobs,
                page=page,
                limit=limit,
                location=location
            )
            return {
                "message": "Job ingestion started in background",
                "page": page,
                "limit": limit,
                "location": location,
                "status": "processing"
            }
        else:
            # Process synchronously
            result = await ingestion_service.ingest_rise_jobs(
                page=page,
                limit=limit,
                location=location
            )
            return result
            
    except Exception as e:
        logger.error(f"Error in Rise job ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error ingesting jobs: {str(e)}")

@router.post("/ingest/rise/bulk")
async def bulk_ingest_rise_jobs(
    background_tasks: BackgroundTasks,
    total_pages: int = Query(5, ge=1, le=20, description="Total pages to process"),
    jobs_per_page: int = Query(20, ge=1, le=50, description="Jobs per page"),
    location: Optional[str] = Query(None, description="Location filter for jobs"),
    async_processing: bool = Query(True, description="Process in background")
) -> Dict[str, Any]:
    """
    Bulk ingest jobs from multiple pages of Rise API
    
    This endpoint processes multiple pages of jobs from Rise API in sequence.
    Recommended for initial data population or large-scale updates.
    
    Args:
        total_pages: Number of pages to process (default: 5, max: 20)
        jobs_per_page: Number of jobs per page (default: 20, max: 50)
        location: Optional location filter
        async_processing: If True, process in background (recommended for bulk operations)
    
    Returns:
        Dict containing bulk ingestion results and statistics
    """
    try:
        if async_processing:
            # Process in background
            background_tasks.add_task(
                ingestion_service.bulk_ingest_rise_jobs,
                total_pages=total_pages,
                jobs_per_page=jobs_per_page,
                location=location
            )
            return {
                "message": f"Bulk job ingestion started in background for {total_pages} pages",
                "total_pages": total_pages,
                "jobs_per_page": jobs_per_page,
                "location": location,
                "status": "processing"
            }
        else:
            # Process synchronously
            result = await ingestion_service.bulk_ingest_rise_jobs(
                total_pages=total_pages,
                jobs_per_page=jobs_per_page,
                location=location
            )
            return result
            
    except Exception as e:
        logger.error(f"Error in bulk Rise job ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error in bulk job ingestion: {str(e)}")

@router.get("/ingest/status")
async def get_ingestion_status() -> Dict[str, Any]:
    """
    Get current status of data ingestion
    
    Returns the current count of jobs in Elasticsearch and Neo4j databases.
    Useful for monitoring the ingestion process and database state.
    
    Returns:
        Dict containing current job counts and timestamp
    """
    try:
        status = await ingestion_service.get_ingestion_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

@router.post("/ingest/rise/test")
async def test_rise_integration(
    limit: int = Query(5, ge=1, le=10, description="Number of jobs to test with")
) -> Dict[str, Any]:
    """
    Test Rise API integration with a small sample
    
    This endpoint fetches a small number of jobs to test the integration
    without affecting the main database. Useful for testing and debugging.
    
    Args:
        limit: Number of jobs to fetch for testing (default: 5, max: 10)
    
    Returns:
        Dict containing test results and sample job data
    """
    try:
        # Fetch jobs without indexing to databases
        jobs = await ingestion_service.rise_service.fetch_and_map_jobs(
            page=1,
            limit=limit
        )
        
        # Return sample data without processing
        sample_jobs = []
        for job in jobs[:3]:  # Return first 3 jobs as samples
            sample_jobs.append({
                "id": job.id,
                "title": job.title,
                "company_name": job.company_name,
                "location": {
                    "city": job.location.city,
                    "state": job.location.state,
                    "country": job.location.country
                },
                "job_type": job.job_type,
                "experience_level": job.experience_level,
                "required_skills": job.required_skills[:5],  # First 5 skills
                "salary": {
                    "min_salary": job.salary.min_salary if job.salary else None,
                    "max_salary": job.salary.max_salary if job.salary else None
                } if job.salary else None,
                "source_url": job.source_url
            })
        
        return {
            "success": True,
            "message": f"Successfully fetched {len(jobs)} jobs from Rise API",
            "total_fetched": len(jobs),
            "sample_jobs": sample_jobs,
            "test_timestamp": ingestion_service.rise_service._parse_datetime("").isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in Rise integration test: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing Rise integration: {str(e)}")

@router.delete("/ingest/clear")
async def clear_ingestion_data(
    clear_elasticsearch: bool = Query(True, description="Clear Elasticsearch data"),
    clear_neo4j: bool = Query(True, description="Clear Neo4j data"),
    confirm: bool = Query(False, description="Confirmation required for data deletion")
) -> Dict[str, Any]:
    """
    Clear ingested data from databases
    
    WARNING: This will delete all job data from the specified databases.
    Use with caution and only for testing/development purposes.
    
    Args:
        clear_elasticsearch: Whether to clear Elasticsearch data
        clear_neo4j: Whether to clear Neo4j data
        confirm: Confirmation flag (must be True to proceed)
    
    Returns:
        Dict containing deletion results
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Confirmation required. Set confirm=true to proceed with data deletion."
        )
    
    try:
        results = {
            "elasticsearch_cleared": False,
            "neo4j_cleared": False,
            "message": "Data clearing completed"
        }
        
        if clear_elasticsearch:
            # Clear Elasticsearch index
            success = await ingestion_service.es_service.clear_jobs_index()
            results["elasticsearch_cleared"] = success
        
        if clear_neo4j:
            # Clear Neo4j data
            success = ingestion_service.kg_service.clear_all_data()
            results["neo4j_cleared"] = success
        
        return results
        
    except Exception as e:
        logger.error(f"Error clearing ingestion data: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")

