from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel
from ..services.job_scraper_service import JobScraperService
from ..services.elasticsearch_service import ElasticsearchService
from ..services.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
job_scraper = JobScraperService()
es_service = ElasticsearchService()
kg_service = KnowledgeGraphService()

class JobIngestionRequest(BaseModel):
    """Request model for job ingestion"""
    query: str
    location: Optional[str] = None
    sources: Optional[List[str]] = None  # ['linkedin', 'indeed', 'glassdoor']
    limit_per_source: int = 50
    auto_process: bool = True  # Whether to automatically process and store jobs

class JobIngestionResponse(BaseModel):
    """Response model for job ingestion"""
    message: str
    total_jobs: int
    elasticsearch_indexed: int
    neo4j_stored: int
    sources_used: List[str]
    processing_time_seconds: float

@router.post("/fetch-jobs", response_model=JobIngestionResponse)
async def fetch_jobs_from_external_sources(
    request: JobIngestionRequest,
    background_tasks: BackgroundTasks
):
    """
    Fetch jobs from external sources and optionally store them
    
    This endpoint allows you to:
    1. Fetch jobs from multiple sources (LinkedIn, Indeed, etc.)
    2. Automatically process and store them in your databases
    3. Run the ingestion in the background for large datasets
    """
    try:
        import time
        start_time = time.time()
        
        # Filter sources if specified
        if request.sources:
            available_sources = list(job_scraper.adapters.keys())
            valid_sources = [s for s in request.sources if s in available_sources]
            if not valid_sources:
                raise HTTPException(
                    status_code=400, 
                    detail=f"No valid sources found. Available: {available_sources}"
                )
        
        # Fetch jobs from external sources
        if request.auto_process:
            # Fetch and store jobs
            result = await job_scraper.fetch_and_store_jobs(
                query=request.query,
                location=request.location,
                limit_per_source=request.limit_per_source
            )
        else:
            # Just fetch jobs without storing
            jobs = await job_scraper.fetch_jobs_from_all_sources(
                query=request.query,
                location=request.location,
                limit_per_source=request.limit_per_source
            )
            result = {
                "message": f"Fetched {len(jobs)} jobs (not stored)",
                "total_jobs": len(jobs),
                "elasticsearch_indexed": 0,
                "neo4j_stored": 0
            }
        
        processing_time = time.time() - start_time
        
        return JobIngestionResponse(
            message=result["message"],
            total_jobs=result["total_jobs"],
            elasticsearch_indexed=result.get("elasticsearch_indexed", 0),
            neo4j_stored=result.get("neo4j_stored", 0),
            sources_used=list(job_scraper.adapters.keys()),
            processing_time_seconds=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Error in job ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Job ingestion failed: {str(e)}")

@router.post("/fetch-jobs-background")
async def fetch_jobs_background(
    request: JobIngestionRequest,
    background_tasks: BackgroundTasks
):
    """
    Fetch jobs from external sources in the background
    
    Use this for large datasets or when you don't want to wait for the response.
    The job will be processed asynchronously.
    """
    try:
        # Add the job ingestion task to background tasks
        background_tasks.add_task(
            _background_job_ingestion,
            request.query,
            request.location,
            request.limit_per_source
        )
        
        return {
            "message": "Job ingestion started in background",
            "status": "processing",
            "query": request.query,
            "location": request.location
        }
        
    except Exception as e:
        logger.error(f"Error starting background job ingestion: {e}")
        raise HTTPException(status_code=500, detail="Failed to start background job ingestion")

async def _background_job_ingestion(query: str, location: str, limit_per_source: int):
    """Background task for job ingestion"""
    try:
        logger.info(f"Starting background job ingestion for query: {query}")
        
        result = await job_scraper.fetch_and_store_jobs(
            query=query,
            location=location,
            limit_per_source=limit_per_source
        )
        
        logger.info(f"Background job ingestion completed: {result}")
        
    except Exception as e:
        logger.error(f"Error in background job ingestion: {e}")

@router.get("/sources")
async def get_available_sources():
    """Get list of available job sources"""
    return {
        "available_sources": list(job_scraper.adapters.keys()),
        "source_details": {
            name: {
                "type": type(adapter).__name__,
                "rate_limit": adapter.rate_limit,
                "requires_api_key": hasattr(adapter, 'api_key') and adapter.api_key is not None
            }
            for name, adapter in job_scraper.adapters.items()
        }
    }

@router.get("/stats")
async def get_ingestion_stats():
    """Get statistics about job ingestion"""
    try:
        # Get total job count from Elasticsearch
        es_client = es_service.es
        es_stats = es_client.count(index=es_service.index_name)
        total_jobs_es = es_stats['count']
        
        # Get total job count from Neo4j
        with kg_service.neo4j.get_session() as session:
            result = session.run("MATCH (j:Job) RETURN count(j) as job_count")
            total_jobs_neo4j = result.single()["job_count"]
        
        return {
            "total_jobs_elasticsearch": total_jobs_es,
            "total_jobs_neo4j": total_jobs_neo4j,
            "available_sources": len(job_scraper.adapters),
            "sources": list(job_scraper.adapters.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting ingestion stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ingestion statistics")

@router.post("/bulk-ingest")
async def bulk_ingest_jobs(
    queries: List[str],
    location: Optional[str] = None,
    limit_per_source: int = 25,
    background_tasks: BackgroundTasks = None
):
    """
    Bulk ingest jobs for multiple queries
    
    Useful for populating your database with jobs from different categories
    """
    try:
        total_results = []
        
        for query in queries:
            if background_tasks:
                # Process in background
                background_tasks.add_task(
                    _background_job_ingestion,
                    query,
                    location,
                    limit_per_source
                )
                total_results.append({
                    "query": query,
                    "status": "queued_for_background_processing"
                })
            else:
                # Process synchronously
                result = await job_scraper.fetch_and_store_jobs(
                    query=query,
                    location=location,
                    limit_per_source=limit_per_source
                )
                total_results.append({
                    "query": query,
                    "status": "completed",
                    "jobs_fetched": result["total_jobs"]
                })
        
        return {
            "message": f"Bulk ingestion {'queued' if background_tasks else 'completed'} for {len(queries)} queries",
            "results": total_results
        }
        
    except Exception as e:
        logger.error(f"Error in bulk job ingestion: {e}")
        raise HTTPException(status_code=500, detail="Bulk job ingestion failed")

@router.delete("/cleanup-duplicates")
async def cleanup_duplicate_jobs():
    """
    Remove duplicate jobs from the database
    
    This endpoint identifies and removes duplicate jobs based on title and company
    """
    try:
        # Get all jobs from Elasticsearch
        es_client = es_service.es
        search_result = es_client.search(
            index=es_service.index_name,
            body={"query": {"match_all": {}}},
            size=10000  # Adjust based on your data size
        )
        
        jobs = []
        for hit in search_result["hits"]["hits"]:
            job_data = hit["_source"]
            job_data["id"] = hit["_id"]
            jobs.append(job_data)
        
        # Find duplicates
        seen = set()
        duplicates = []
        unique_jobs = []
        
        for job in jobs:
            key = f"{job['title'].lower().strip()}_{job['company_name'].lower().strip()}"
            if key in seen:
                duplicates.append(job["id"])
            else:
                seen.add(key)
                unique_jobs.append(job["id"])
        
        # Remove duplicates from Elasticsearch
        deleted_count = 0
        for job_id in duplicates:
            if es_service.delete_job(job_id):
                deleted_count += 1
        
        return {
            "message": f"Cleanup completed",
            "total_jobs": len(jobs),
            "duplicates_found": len(duplicates),
            "duplicates_removed": deleted_count,
            "unique_jobs_remaining": len(unique_jobs)
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up duplicates: {e}")
        raise HTTPException(status_code=500, detail="Duplicate cleanup failed")
