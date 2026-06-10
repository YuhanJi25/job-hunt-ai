import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import json
import time
from ..models.job import Job, JobType, ExperienceLevel, Location, Salary, Benefit
from ..core.config import settings

logger = logging.getLogger(__name__)

class JobSourceAdapter(ABC):
    """Abstract base class for job source adapters"""
    
    def __init__(self, api_key: str = None, rate_limit: int = 100):
        self.api_key = api_key
        self.rate_limit = rate_limit
        self.last_request_time = 0
    
    async def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60 / self.rate_limit  # requests per minute
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    @abstractmethod
    async def fetch_jobs(self, query: str, location: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch jobs from the source"""
        pass
    
    @abstractmethod
    def normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        """Convert raw job data to our Job model"""
        pass

class LinkedInJobsAdapter(JobSourceAdapter):
    """LinkedIn Jobs API adapter"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, rate_limit=100)
        self.base_url = "https://api.linkedin.com/v2"
    
    async def fetch_jobs(self, query: str, location: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch jobs from LinkedIn Jobs API"""
        await self._rate_limit()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        params = {
            "keywords": query,
            "count": min(limit, 100),
            "start": 0
        }
        
        if location:
            params["locationName"] = location
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/jobSearch",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("elements", [])
                    else:
                        logger.error(f"LinkedIn API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching LinkedIn jobs: {e}")
            return []
    
    def normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        """Convert LinkedIn job to our Job model"""
        try:
            # Extract basic information
            job_id = f"linkedin_{raw_job.get('dashEntityUrn', '').split(':')[-1]}"
            title = raw_job.get("title", "Unknown Title")
            description = raw_job.get("description", {}).get("text", "")
            company_name = raw_job.get("companyDetails", {}).get("company", {}).get("name", "Unknown Company")
            
            # Extract location
            location_data = raw_job.get("formattedLocation", {})
            location = Location(
                city=location_data.get("city", ""),
                state=location_data.get("state", ""),
                country=location_data.get("country", ""),
                coordinates={"lat": 0, "lng": 0}  # LinkedIn doesn't provide coordinates
            )
            
            # Extract job type and experience level
            job_type = self._map_job_type(raw_job.get("jobType", ""))
            experience_level = self._map_experience_level(raw_job.get("experienceLevel", ""))
            
            # Extract salary if available
            salary = None
            salary_data = raw_job.get("salaryRange", {})
            if salary_data:
                salary = Salary(
                    min_salary=salary_data.get("start", 0),
                    max_salary=salary_data.get("end", 0),
                    currency=salary_data.get("currency", "USD"),
                    period="yearly"
                )
            
            # Extract skills from description
            required_skills = self._extract_skills(description)
            
            # Extract URLs
            source_url = raw_job.get("jobPostingUrl", "")
            apply_url = raw_job.get("applyUrl", source_url)  # Use applyUrl if available, fallback to source_url
            
            return Job(
                id=job_id,
                title=title,
                description=description,
                company_name=company_name,
                location=location,
                job_type=job_type,
                experience_level=experience_level,
                salary=salary,
                benefits=[],  # LinkedIn doesn't provide detailed benefits
                required_skills=required_skills,
                preferred_skills=[],
                responsibilities=[],
                requirements=[],
                posted_date=datetime.now(),
                remote_allowed="remote" in description.lower(),
                visa_sponsorship=False,  # Not available in LinkedIn API
                source_url=source_url,
                apply_url=apply_url
            )
        except Exception as e:
            logger.error(f"Error normalizing LinkedIn job: {e}")
            raise
    
    def _map_job_type(self, linkedin_type: str) -> JobType:
        """Map LinkedIn job type to our JobType enum"""
        type_mapping = {
            "FULL_TIME": JobType.FULL_TIME,
            "PART_TIME": JobType.PART_TIME,
            "CONTRACT": JobType.CONTRACT,
            "INTERNSHIP": JobType.INTERNSHIP,
            "TEMPORARY": JobType.CONTRACT
        }
        return type_mapping.get(linkedin_type.upper(), JobType.FULL_TIME)
    
    def _map_experience_level(self, linkedin_level: str) -> ExperienceLevel:
        """Map LinkedIn experience level to our ExperienceLevel enum"""
        level_mapping = {
            "ENTRY_LEVEL": ExperienceLevel.JUNIOR,
            "ASSOCIATE": ExperienceLevel.JUNIOR,
            "MID_SENIOR_LEVEL": ExperienceLevel.MID,
            "SENIOR_LEVEL": ExperienceLevel.SENIOR,
            "EXECUTIVE": ExperienceLevel.SENIOR,
            "DIRECTOR": ExperienceLevel.SENIOR
        }
        return level_mapping.get(linkedin_level.upper(), ExperienceLevel.MID)
    
    def _extract_skills(self, description: str) -> List[str]:
        """Extract skills from job description (simplified)"""
        # This is a simplified skill extraction
        # In production, you'd use your NLP service
        common_skills = [
            "Python", "JavaScript", "Java", "C++", "C#", "Go", "Rust",
            "React", "Angular", "Vue", "Node.js", "Django", "Flask",
            "AWS", "Azure", "GCP", "Docker", "Kubernetes",
            "Machine Learning", "AI", "Data Science", "SQL", "MongoDB"
        ]
        
        found_skills = []
        description_lower = description.lower()
        
        for skill in common_skills:
            if skill.lower() in description_lower:
                found_skills.append(skill)
        
        return found_skills

class IndeedJobsAdapter(JobSourceAdapter):
    """Indeed Jobs API adapter (using web scraping as Indeed doesn't have public API)"""
    
    def __init__(self):
        super().__init__(rate_limit=10)  # Be respectful with scraping
        self.base_url = "https://www.indeed.com"
    
    async def fetch_jobs(self, query: str, location: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch jobs from Indeed (web scraping)"""
        await self._rate_limit()
        
        # Note: This is a simplified example. In production, you'd need to handle
        # Indeed's anti-bot measures, use proper headers, and respect robots.txt
        
        params = {
            "q": query,
            "l": location or "",
            "limit": min(limit, 50)  # Indeed limits results
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/jobs",
                    params=params,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_indeed_html(html)
                    else:
                        logger.error(f"Indeed scraping error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error scraping Indeed jobs: {e}")
            return []
    
    def _parse_indeed_html(self, html: str) -> List[Dict[str, Any]]:
        """Parse Indeed HTML to extract job data"""
        # This is a simplified parser. In production, you'd use BeautifulSoup
        # and handle Indeed's dynamic content loading
        
        jobs = []
        # Implementation would go here
        # For now, return empty list
        return jobs
    
    def normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        """Convert Indeed job to our Job model"""
        # Implementation similar to LinkedIn adapter
        pass

class JobScraperService:
    """Main service for scraping jobs from multiple sources"""
    
    def __init__(self):
        self.adapters = {}
        self.setup_adapters()
    
    def setup_adapters(self):
        """Initialize job source adapters"""
        # LinkedIn adapter (requires API key)
        linkedin_key = getattr(settings, 'LINKEDIN_API_KEY', None)
        if linkedin_key:
            self.adapters['linkedin'] = LinkedInJobsAdapter(linkedin_key)
        
        # Indeed adapter (web scraping)
        self.adapters['indeed'] = IndeedJobsAdapter()
        
        # Add more adapters as needed
        # self.adapters['glassdoor'] = GlassdoorJobsAdapter()
        # self.adapters['ziprecruiter'] = ZipRecruiterJobsAdapter()
    
    async def fetch_jobs_from_all_sources(
        self, 
        query: str, 
        location: str = None, 
        limit_per_source: int = 50
    ) -> List[Job]:
        """Fetch jobs from all configured sources"""
        all_jobs = []
        
        # Fetch jobs from all sources concurrently
        tasks = []
        for source_name, adapter in self.adapters.items():
            task = self._fetch_from_source(adapter, query, location, limit_per_source)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            source_name = list(self.adapters.keys())[i]
            
            if isinstance(result, Exception):
                logger.error(f"Error fetching from {source_name}: {result}")
                continue
            
            if isinstance(result, list):
                all_jobs.extend(result)
                logger.info(f"Fetched {len(result)} jobs from {source_name}")
        
        # Remove duplicates based on title and company
        unique_jobs = self._remove_duplicates(all_jobs)
        
        logger.info(f"Total unique jobs fetched: {len(unique_jobs)}")
        return unique_jobs
    
    async def _fetch_from_source(
        self, 
        adapter: JobSourceAdapter, 
        query: str, 
        location: str, 
        limit: int
    ) -> List[Job]:
        """Fetch jobs from a single source"""
        try:
            raw_jobs = await adapter.fetch_jobs(query, location, limit)
            normalized_jobs = []
            
            for raw_job in raw_jobs:
                try:
                    job = adapter.normalize_job(raw_job)
                    normalized_jobs.append(job)
                except Exception as e:
                    logger.error(f"Error normalizing job: {e}")
                    continue
            
            return normalized_jobs
            
        except Exception as e:
            logger.error(f"Error fetching from source: {e}")
            return []
    
    def _remove_duplicates(self, jobs: List[Job]) -> List[Job]:
        """Remove duplicate jobs based on title and company"""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create a key based on title and company
            key = f"{job.title.lower().strip()}_{job.company_name.lower().strip()}"
            
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        return unique_jobs
    
    async def fetch_and_store_jobs(
        self, 
        query: str, 
        location: str = None,
        limit_per_source: int = 50
    ) -> Dict[str, Any]:
        """Fetch jobs and store them in both Elasticsearch and Neo4j"""
        from .elasticsearch_service import ElasticsearchService
        from .knowledge_graph_service import KnowledgeGraphService
        
        # Fetch jobs from all sources
        jobs = await self.fetch_jobs_from_all_sources(query, location, limit_per_source)
        
        if not jobs:
            return {"message": "No jobs found", "stored": 0}
        
        # Store in Elasticsearch
        es_service = ElasticsearchService()
        es_result = es_service.bulk_index_jobs(jobs)
        
        # Store in Neo4j
        kg_service = KnowledgeGraphService()
        kg_success_count = 0
        
        for job in jobs:
            if kg_service.create_job_node(job):
                kg_success_count += 1
        
        return {
            "message": f"Successfully processed {len(jobs)} jobs",
            "elasticsearch_indexed": len(es_result.get("indexed", [])),
            "neo4j_stored": kg_success_count,
            "total_jobs": len(jobs)
        }
