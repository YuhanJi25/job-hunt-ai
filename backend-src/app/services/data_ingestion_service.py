import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from ..models.job import Job
from .rise_api_service import RiseAPIService
from .elasticsearch_service import ElasticsearchService
from .knowledge_graph_service import KnowledgeGraphService
from .nlp_service import NLPService
from ..core.config import settings

logger = logging.getLogger(__name__)

class DataIngestionService:
    def __init__(self):
        self.rise_service = RiseAPIService()
        self.es_service = ElasticsearchService()
        self.kg_service = KnowledgeGraphService()
        self.nlp_service = NLPService()
        
    async def ingest_rise_jobs(
        self, 
        page: int = 1, 
        limit: int = 50, 
        location: Optional[str] = None,
        index_to_elasticsearch: bool = True,
        create_neo4j_nodes: bool = True
    ) -> Dict[str, Any]:
        """Complete pipeline to ingest jobs from Rise API"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting Rise job ingestion - page: {page}, limit: {limit}, location: {location}")
            
            # Step 1: Fetch jobs from Rise API
            jobs = await self.rise_service.fetch_and_map_jobs(page, limit, location)
            
            if not jobs:
                logger.warning("No jobs fetched from Rise API")
                return {
                    "success": False,
                    "message": "No jobs fetched from Rise API",
                    "jobs_processed": 0,
                    "elasticsearch_indexed": 0,
                    "neo4j_created": 0,
                    "processing_time_seconds": 0
                }
            
            logger.info(f"Fetched {len(jobs)} jobs from Rise API")
            
            # Step 2: Process jobs with NLP (extract entities, enhance descriptions)
            processed_jobs = await self._process_jobs_with_nlp(jobs)
            logger.info(f"Processed {len(processed_jobs)} jobs with NLP")
            # print 
            for job in processed_jobs[:10]:
                logger.info(f"Job {job.id} with NLP: {job.description}")
            
            # Step 3: Index to Elasticsearch
            elasticsearch_count = 0
            if index_to_elasticsearch:
                elasticsearch_count = await self._index_jobs_to_elasticsearch(processed_jobs)
                logger.info(f"Indexed {elasticsearch_count} jobs to Elasticsearch")
            
            # Step 4: Create Neo4j nodes and relationships
            neo4j_count = 0
            if create_neo4j_nodes:
                neo4j_count = await self._create_neo4j_nodes(processed_jobs)
                logger.info(f"Created {neo4j_count} job nodes in Neo4j")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "success": True,
                "message": f"Successfully processed {len(jobs)} jobs from Rise API",
                "jobs_processed": len(jobs),
                "elasticsearch_indexed": elasticsearch_count,
                "neo4j_created": neo4j_count,
                "processing_time_seconds": processing_time,
                "source": "rise_api",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Rise job ingestion completed successfully: {result}")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error in Rise job ingestion: {e}")
            return {
                "success": False,
                "message": f"Error ingesting jobs: {str(e)}",
                "jobs_processed": 0,
                "elasticsearch_indexed": 0,
                "neo4j_created": 0,
                "processing_time_seconds": processing_time
            }
    
    async def _process_jobs_with_nlp(self, jobs: List[Job]) -> List[Job]:
        """Process jobs with NLP to extract entities and enhance data"""
        try:
            processed_jobs = []
            
            for job in jobs:
                try:
                    # Extract entities from job description
                    entities = self.nlp_service.extract_entities_from_text(job.description)
                    
                    # Extract skills from description
                    extracted_skills = self.nlp_service.extract_skills_from_text(job.description)
                    
                    # Combine with existing skills
                    all_skills = list(set(job.required_skills + extracted_skills))
                    job.required_skills = all_skills
                    
                    # Enhance description with extracted keywords
                    if entities:
                        keywords = [entity.text for entity in entities if entity.label_ in ["ORG", "PERSON", "GPE"]]
                        if keywords:
                            job.description += f" Keywords: {', '.join(keywords[:5])}"
                    
                    processed_jobs.append(job)
                    
                except Exception as e:
                    logger.warning(f"Error processing job {job.id} with NLP: {e}")
                    processed_jobs.append(job)  # Add unprocessed job
            
            return processed_jobs
            
        except Exception as e:
            logger.error(f"Error in NLP processing: {e}")
            return jobs  # Return original jobs if NLP processing fails

    async def process_jobs_with_pipeline(
        self,
        jobs: List[Job],
        index_to_elasticsearch: bool = False,
        create_neo4j_nodes: bool = False
    ) -> Dict[str, Any]:
        """Reusable pipeline step for custom job sources."""
        processed_jobs = await self._process_jobs_with_nlp(jobs)
        
        es_count = 0
        if index_to_elasticsearch and processed_jobs:
            es_count = await self._index_jobs_to_elasticsearch(processed_jobs)
        
        neo4j_count = 0
        if create_neo4j_nodes and processed_jobs:
            neo4j_count = await self._create_neo4j_nodes(processed_jobs)
        
        return {
            "jobs": processed_jobs,
            "elasticsearch_indexed": es_count,
            "neo4j_created": neo4j_count
        }
    
    async def _index_jobs_to_elasticsearch(self, jobs: List[Job]) -> int:
        """Index jobs to Elasticsearch"""
        try:
            indexed_count = 0
            
            for job in jobs:
                try:
                    success = self.es_service.index_job(job)
                    if success:
                        indexed_count += 1
                except Exception as e:
                    logger.warning(f"Error indexing job {job.id} to Elasticsearch: {e}")
                    continue
            
            return indexed_count
            
        except Exception as e:
            logger.error(f"Error indexing jobs to Elasticsearch: {e}")
            return 0
    
    async def _create_neo4j_nodes(self, jobs: List[Job]) -> int:
        """Create Neo4j nodes and relationships for jobs"""
        try:
            created_count = 0
            
            for job in jobs:
                try:
                    # Create job node
                    success = self.kg_service.create_job_node(job)
                    if success:
                        created_count += 1
                        
                        # Create related nodes (company, location, skills)
                        self.kg_service.create_company_node(job.company_name, {})
                        self.kg_service.create_location_node(job.location)
                        
                        # Create skill nodes and relationships
                        for skill in job.required_skills:
                            self.kg_service.create_skill_node(skill)
                            self.kg_service.create_job_skill_relationship(job.id, skill)
                        
                        # Create company relationship
                        self.kg_service.create_job_company_relationship(job.id, job.company_name)
                        
                        # Create location relationship
                        location_id = f"{job.location.city}_{job.location.state}_{job.location.country}"
                        self.kg_service.create_job_location_relationship(job.id, location_id)
                        
                except Exception as e:
                    logger.warning(f"Error creating Neo4j nodes for job {job.id}: {e}")
                    continue
            
            return created_count
            
        except Exception as e:
            logger.error(f"Error creating Neo4j nodes: {e}")
            return 0
    
    async def bulk_ingest_rise_jobs(
        self, 
        total_pages: int = 5, 
        jobs_per_page: int = 20,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """Bulk ingest jobs from multiple pages"""
        start_time = datetime.now()
        total_results = {
            "success": True,
            "total_jobs_processed": 0,
            "total_elasticsearch_indexed": 0,
            "total_neo4j_created": 0,
            "pages_processed": 0,
            "errors": [],
            "processing_time_seconds": 0
        }
        
        try:
            logger.info(f"Starting bulk ingestion of {total_pages} pages with {jobs_per_page} jobs per page")
            
            for page in range(1, total_pages + 1):
                try:
                    logger.info(f"Processing page {page}/{total_pages}")
                    
                    result = await self.ingest_rise_jobs(
                        page=page,
                        limit=jobs_per_page,
                        location=location
                    )
                    
                    if result["success"]:
                        total_results["total_jobs_processed"] += result["jobs_processed"]
                        total_results["total_elasticsearch_indexed"] += result["elasticsearch_indexed"]
                        total_results["total_neo4j_created"] += result["neo4j_created"]
                        total_results["pages_processed"] += 1
                    else:
                        total_results["errors"].append(f"Page {page}: {result['message']}")
                    
                    # Add delay between requests to be respectful to the API
                    if page < total_pages:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    error_msg = f"Page {page}: {str(e)}"
                    total_results["errors"].append(error_msg)
                    logger.error(error_msg)
                    continue
            
            total_results["processing_time_seconds"] = (datetime.now() - start_time).total_seconds()
            
            if total_results["errors"]:
                total_results["success"] = False
                total_results["message"] = f"Completed with {len(total_results['errors'])} errors"
            else:
                total_results["message"] = "Bulk ingestion completed successfully"
            
            logger.info(f"Bulk ingestion completed: {total_results}")
            return total_results
            
        except Exception as e:
            total_results["success"] = False
            total_results["message"] = f"Bulk ingestion failed: {str(e)}"
            total_results["processing_time_seconds"] = (datetime.now() - start_time).total_seconds()
            logger.error(f"Bulk ingestion error: {e}")
            return total_results
    
    async def get_ingestion_status(self) -> Dict[str, Any]:
        """Get current status of data ingestion"""
        try:
            # Get Elasticsearch job count
            es_count = await self.es_service.get_job_count()
            
            # Get Neo4j job count
            kg_count = self.kg_service.get_job_count()
            
            return {
                "elasticsearch_jobs": es_count,
                "neo4j_jobs": kg_count,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting ingestion status: {e}")
            return {
                "elasticsearch_jobs": 0,
                "neo4j_jobs": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
