import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from ..models.job import Job, JobType, ExperienceLevel, Location, Salary, Benefit
from ..core.config import settings

logger = logging.getLogger(__name__)

class RiseAPIService:
    def __init__(self):
        self.base_url = "https://api.joinrise.io/api/v1/jobs/public"
        self.timeout = 30.0
        
    async def fetch_jobs(
        self, 
        page: int = 1, 
        limit: int = 20, 
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch jobs from Rise API"""
        try:
            params = {
                "page": page,
                "limit": limit,
                "sort": "desc",
                "sortedBy": "createdAt"
            }
            
            if location:
                params["jobLoc"] = location
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching from Rise API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching from Rise API: {e}")
            raise
    
    def map_rise_job_to_internal(self, rise_job: Dict[str, Any]) -> Job:
        """Map Rise API job structure to internal Job model"""
        try:
            # Extract basic job information
            job_id = rise_job.get("_id", "")
            title = rise_job.get("title", "")
            
            # Extract company information
            owner = rise_job.get("owner", {})
            company_name = owner.get("companyName", "Unknown Company")
            
            # Extract location information
            location_address = rise_job.get("locationAddress", "")
            location_coords = rise_job.get("locationCoordinates", {})
            
            # Parse location
            location = self._parse_location(location_address, location_coords)
            
            # Extract job type and experience level
            job_type = self._map_employment_type(rise_job.get("employmentType", "full-time"))
            experience_level = self._map_seniority(rise_job.get("seniority", "mid-level"))
            
            # Extract salary information
            salary = self._extract_salary(rise_job)
            
            # Extract benefits
            benefits = self._extract_benefits(owner.get("benefits", {}))
            
            # Extract skills and requirements
            required_skills = rise_job.get("skillRequirements", [])
            skills_suggest = rise_job.get("skills_suggest", [])
            
            # Combine all skills
            all_skills = list(set(required_skills + skills_suggest))
            
            # Extract description
            description_breakdown = rise_job.get("descriptionBreakdown", {})
            description = description_breakdown.get("oneSentenceJobSummary", "")
            
            # Extract work model
            work_model = rise_job.get("workModel", "onsite")
            remote_allowed = work_model.lower() in ["remote", "hybrid"]
            
            # Extract dates
            created_at = rise_job.get("createdAt", "")
            posted_date = self._parse_datetime(created_at)
            
            # Extract source URL and apply URL
            source_url = rise_job.get("url", "")
            apply_url = rise_job.get("applyUrl", source_url)  # Use applyUrl if available, fallback to source_url
            
            return Job(
                id=job_id,
                title=title,
                description=description,
                company_name=company_name,
                location=location,
                job_type=job_type,
                experience_level=experience_level,
                salary=salary,
                benefits=benefits,
                required_skills=all_skills,
                preferred_skills=[],  # Rise doesn't distinguish between required/preferred
                responsibilities=[],  # Not available in Rise API
                requirements=required_skills,
                posted_date=posted_date,
                application_deadline=None,  # Not available in Rise API
                remote_allowed=remote_allowed,
                visa_sponsorship=False,  # Not available in Rise API
                source_url=source_url,
                apply_url=apply_url
            )
            
        except Exception as e:
            logger.error(f"Error mapping Rise job {rise_job.get('_id', 'unknown')}: {e}")
            raise
    
    def _parse_location(self, address: str, coords: Dict[str, Any]) -> Location:
        """Parse location from Rise API format"""
        try:
            # Simple parsing - in production, you'd want more sophisticated parsing
            parts = address.split(", ")
            city = parts[0] if parts else "Unknown"
            state = parts[1] if len(parts) > 1 else "Unknown"
            
            coordinates = None
            if coords and "lat" in coords and "lon" in coords:
                coordinates = {
                    "latitude": float(coords["lat"]),
                    "longitude": float(coords["lon"])
                }
            
            return Location(
                city=city,
                state=state,
                country="USA",
                coordinates=coordinates
            )
        except Exception as e:
            logger.warning(f"Error parsing location '{address}': {e}")
            return Location(city="Unknown", state="Unknown", country="USA")
    
    def _map_employment_type(self, employment_type: str) -> JobType:
        """Map Rise employment type to internal JobType"""
        mapping = {
            "full-time": JobType.FULL_TIME,
            "part-time": JobType.PART_TIME,
            "contract": JobType.CONTRACT,
            "internship": JobType.INTERNSHIP
        }
        return mapping.get(employment_type.lower(), JobType.FULL_TIME)
    
    def _map_seniority(self, seniority: str) -> ExperienceLevel:
        """Map Rise seniority to internal ExperienceLevel"""
        mapping = {
            "entry-level": ExperienceLevel.ENTRY,
            "mid-level": ExperienceLevel.MID,
            "senior-level": ExperienceLevel.SENIOR,
            "executive": ExperienceLevel.EXECUTIVE
        }
        return mapping.get(seniority.lower(), ExperienceLevel.MID)
    
    def _extract_salary(self, rise_job: Dict[str, Any]) -> Optional[Salary]:
        """Extract salary information from Rise job"""
        try:
            min_salary = rise_job.get("salaryRangeMinYearly")
            max_salary = rise_job.get("salaryRangeMaxYearly")
            
            if min_salary or max_salary:
                return Salary(
                    min_salary=min_salary,
                    max_salary=max_salary,
                    currency="USD",
                    period="yearly"
                )
            return None
        except Exception as e:
            logger.warning(f"Error extracting salary: {e}")
            return None
    
    def _extract_benefits(self, benefits_data: Dict[str, Any]) -> List[Benefit]:
        """Extract benefits from Rise job"""
        try:
            benefits = []
            benefits_list = benefits_data.get("benefits", [])
            
            for benefit_name in benefits_list:
                if benefit_name:
                    # Map benefit names to categories
                    category = self._categorize_benefit(benefit_name)
                    benefits.append(Benefit(
                        name=benefit_name,
                        category=category
                    ))
            
            return benefits
        except Exception as e:
            logger.warning(f"Error extracting benefits: {e}")
            return []
    
    def _categorize_benefit(self, benefit_name: str) -> str:
        """Categorize benefit based on name"""
        benefit_lower = benefit_name.lower()
        
        if any(word in benefit_lower for word in ["health", "medical", "dental", "vision"]):
            return "health"
        elif any(word in benefit_lower for word in ["retirement", "401k", "pension"]):
            return "retirement"
        elif any(word in benefit_lower for word in ["time", "vacation", "holiday", "leave"]):
            return "time_off"
        elif any(word in benefit_lower for word in ["life", "disability", "insurance"]):
            return "insurance"
        else:
            return "other"
    
    def _parse_datetime(self, date_string: str) -> datetime:
        """Parse datetime from Rise API format"""
        try:
            if date_string:
                # Rise API uses ISO format
                return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return datetime.now()
        except Exception as e:
            logger.warning(f"Error parsing datetime '{date_string}': {e}")
            return datetime.now()
    
    async def fetch_and_map_jobs(
        self, 
        page: int = 1, 
        limit: int = 20, 
        location: Optional[str] = None
    ) -> List[Job]:
        """Fetch jobs from Rise API and map them to internal format"""
        try:
            # Fetch data from Rise API
            response_data = await self.fetch_jobs(page, limit, location)
            
            if not response_data.get("success"):
                logger.error("Rise API returned unsuccessful response")
                return []
            
            jobs_data = response_data.get("result", {}).get("jobs", [])
            
            # Map each job to internal format
            mapped_jobs = []
            for job_data in jobs_data:
                try:
                    job = self.map_rise_job_to_internal(job_data)
                    mapped_jobs.append(job)
                except Exception as e:
                    logger.error(f"Error mapping job {job_data.get('_id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully mapped {len(mapped_jobs)} jobs from Rise API")
            return mapped_jobs
            
        except Exception as e:
            logger.error(f"Error fetching and mapping jobs from Rise API: {e}")
            raise

