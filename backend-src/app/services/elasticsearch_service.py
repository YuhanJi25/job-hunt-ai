from elasticsearch import Elasticsearch
from elasticsearch import helpers
from typing import List, Dict, Any, Optional
import logging
from ..core.database import get_elasticsearch
from ..models.job import Job, JobSearchQuery, JobSearchResult
from ..core.config import settings

logger = logging.getLogger(__name__)

class ElasticsearchService:
    def __init__(self):
        self.es = get_elasticsearch()
        self.index_name = "jobs"
        self.disabled = self.es is None
        if self.disabled:
            logger.warning("ElasticsearchService disabled; skipping index initialization.")
        else:
            self.setup_index()
    
    def setup_index(self):
        """Create the jobs index with proper mapping"""
        if self.disabled:
            return
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "company_name": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "location": {
                        "properties": {
                            "city": {"type": "keyword"},
                            "state": {"type": "keyword"},
                            "country": {"type": "keyword"},
                            "coordinates": {"type": "geo_point"}
                        }
                    },
                    "job_type": {"type": "keyword"},
                    "experience_level": {"type": "keyword"},
                    "salary": {
                        "properties": {
                            "min_salary": {"type": "integer"},
                            "max_salary": {"type": "integer"},
                            "currency": {"type": "keyword"},
                            "period": {"type": "keyword"}
                        }
                    },
                    "benefits": {
                        "type": "nested",
                        "properties": {
                            "name": {"type": "keyword"},
                            "description": {"type": "text"},
                            "category": {"type": "keyword"}
                        }
                    },
                    "required_skills": {
                        "type": "keyword"
                    },
                    "preferred_skills": {
                        "type": "keyword"
                    },
                    "responsibilities": {
                        "type": "text"
                    },
                    "requirements": {
                        "type": "text"
                    },
                    "posted_date": {"type": "date"},
                    "application_deadline": {"type": "date"},
                    "remote_allowed": {"type": "boolean"},
                    "visa_sponsorship": {"type": "boolean"},
                    "source_url": {"type": "keyword"},
                    "skills_text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "all_text": {
                        "type": "text",
                        "analyzer": "standard"
                    }
                }
            }
        }
        
        try:
            if not self.es.indices.exists(index=self.index_name):
                self.es.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created index: {self.index_name}")
            else:
                logger.info(f"Index {self.index_name} already exists")
        except Exception as e:
            logger.error(f"Error setting up index: {e}")
    
    def index_job(self, job: Job) -> bool:
        """Index a single job document"""
        if self.disabled or not self.es:
            logger.debug("Skipping Elasticsearch indexing for job %s (disabled).", job.id)
            return False
        try:
            # Prepare document for indexing
            doc = job.dict()
            doc["skills_text"] = " ".join(job.required_skills + job.preferred_skills)
            doc["all_text"] = f"{job.title} {job.description} {' '.join(job.required_skills)} {' '.join(job.preferred_skills)}"
            
            # Fix geo_point format for Elasticsearch
            if doc.get("location", {}).get("coordinates"):
                coords = doc["location"]["coordinates"]
                if isinstance(coords, dict) and "latitude" in coords and "longitude" in coords:
                    # Convert to proper geo_point format
                    doc["location"]["coordinates"] = f"{coords['longitude']},{coords['latitude']}"
                elif isinstance(coords, list) and len(coords) == 2:
                    # Convert [lat, lon] to "lon,lat" format
                    doc["location"]["coordinates"] = f"{coords[1]},{coords[0]}"
            
            response = self.es.index(
                index=self.index_name,
                id=job.id,
                body=doc
            )
            return response["result"] in ["created", "updated"]
        except Exception as e:
            logger.error(f"Error indexing job {job.id}: {e}")
            return False
    
    def bulk_index_jobs(self, jobs: List[Job]) -> Dict[str, Any]:
        """Bulk index multiple jobs"""
        if self.disabled or not self.es:
            logger.debug("Skipping bulk Elasticsearch indexing (disabled).")
            return {"indexed": [], "errors": ["elasticsearch disabled"]}
        try:
            actions = []
            for job in jobs:
                doc = job.dict()
                doc["skills_text"] = " ".join(job.required_skills + job.preferred_skills)
                doc["all_text"] = f"{job.title} {job.description} {' '.join(job.required_skills)} {' '.join(job.preferred_skills)}"
                if doc.get("location", {}).get("coordinates"):
                    coords = doc["location"]["coordinates"]
                    if isinstance(coords, dict) and "latitude" in coords and "longitude" in coords:
                        doc["location"]["coordinates"] = f"{coords['longitude']},{coords['latitude']}"
                    elif isinstance(coords, list) and len(coords) == 2:
                        doc["location"]["coordinates"] = f"{coords[1]},{coords[0]}"

                actions.append({
                    "_op_type": "index",
                    "_index": self.index_name,
                    "_id": job.id,
                    "_source": doc
                })

            success, errors = helpers.bulk(self.es, actions)
            return {
                "indexed": success,
                "errors": errors
            }
        except Exception as e:
            logger.error(f"Error bulk indexing jobs: {e}")
            return {"error": str(e)}
    
    def search_jobs(self, query: JobSearchQuery) -> JobSearchResult:
        """Search for jobs using Elasticsearch"""
        if self.disabled or not self.es:
            raise RuntimeError("Elasticsearch is disabled; search is unavailable.")
        try:
            # Build the search query
            search_body = self._build_search_query(query)
            
            # Execute search
            response = self.es.search(
                index=self.index_name,
                body=search_body,
                size=query.page_size,
                from_=(query.page - 1) * query.page_size
            )
            
            # Process results
            jobs = []
            explanations = {}
            for hit in response["hits"]["hits"]:
                job_data = hit["_source"]
                job_data["id"] = hit["_id"]
                job_data["search_metadata"] = {
                    "es_score": hit.get("_score"),
                    "index": hit.get("_index")
                }
                
                # Fix coordinates format for Job model
                if job_data.get("location", {}).get("coordinates"):
                    coords_str = job_data["location"]["coordinates"]
                    if isinstance(coords_str, str) and "," in coords_str:
                        # Convert "lon,lat" string back to dict format
                        try:
                            lon, lat = coords_str.split(",")
                            job_data["location"]["coordinates"] = {
                                "latitude": float(lat.strip()),
                                "longitude": float(lon.strip())
                            }
                        except (ValueError, IndexError):
                            job_data["location"]["coordinates"] = None
                job = Job(**job_data)
                jobs.append(job)
                explanations[job.id] = job_data["search_metadata"]
            
            total_count = response["hits"]["total"]["value"]
            total_pages = (total_count + query.page_size - 1) // query.page_size
            
            return JobSearchResult(
                jobs=jobs,
                total_count=total_count,
                page=query.page,
                page_size=query.page_size,
                total_pages=total_pages,
                search_time_ms=response["took"],
                explanations=explanations or None
            )
            
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return JobSearchResult(
                jobs=[],
                total_count=0,
                page=query.page,
                page_size=query.page_size,
                total_pages=0,
                search_time_ms=0
            )

    def get_jobs_by_ids(self, job_ids: List[str]) -> List[Job]:
        if self.disabled or not self.es or not job_ids:
            return []
        try:
            response = self.es.mget(index=self.index_name, ids=job_ids)
            jobs = []
            for doc in response.get("docs", []):
                if not doc.get("found"):
                    continue
                source = doc["_source"]
                source["id"] = doc["_id"]
                jobs.append(Job(**source))
            return jobs
        except Exception as exc:
            logger.error(f"Error fetching jobs by ids: {exc}")
            return []
    
    def _build_search_query(self, query: JobSearchQuery) -> Dict[str, Any]:
        """Build Elasticsearch query from search parameters"""
        must_clauses = []
        should_clauses = []
        filter_clauses = []
        
        # Text search
        if query.query:
            should_clauses.extend([
                {
                    "multi_match": {
                        "query": query.query,
                        "fields": ["title^3", "description^2", "all_text"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                },
                {
                    "match": {
                        "skills_text": {
                            "query": query.query,
                            "boost": 2
                        }
                    }
                }
            ])
        
        # Location filter
        if query.location:
            filter_clauses.append({
                "bool": {
                    "should": [
                        {"term": {"location.state": query.location}},
                        {"term": {"location.city": query.location}},
                        {"match": {"location.state": query.location}}
                    ]
                }
            })
        
        # Salary range
        if query.min_salary or query.max_salary:
            salary_range = {}
            if query.min_salary:
                salary_range["gte"] = query.min_salary
            if query.max_salary:
                salary_range["lte"] = query.max_salary
            
            filter_clauses.append({
                "range": {
                    "salary.min_salary": salary_range
                }
            })
        
        # Job type filter
        if query.job_type:
            filter_clauses.append({"term": {"job_type": query.job_type}})
        
        # Experience level filter
        if query.experience_level:
            filter_clauses.append({"term": {"experience_level": query.experience_level}})
        
        # Remote allowed filter
        if query.remote_allowed is not None:
            filter_clauses.append({"term": {"remote_allowed": query.remote_allowed}})
        
        # Visa sponsorship filter
        if query.visa_sponsorship is not None:
            filter_clauses.append({"term": {"visa_sponsorship": query.visa_sponsorship}})
        
        # Skills filters
        if query.required_skills:
            for skill in query.required_skills:
                should_clauses.append({
                    "term": {"required_skills": skill}
                })
        
        if query.preferred_skills:
            for skill in query.preferred_skills:
                should_clauses.append({
                    "term": {"preferred_skills": skill}
                })
        
        # Build final query
        search_query = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "should": should_clauses,
                    "filter": filter_clauses,
                    "minimum_should_match": 1 if should_clauses else 0
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"posted_date": {"order": "desc"}}
            ]
        }
        
        return search_query
    
    def get_job_by_id(self, job_id: str) -> Optional[Job]:
        """Get a specific job by ID"""
        try:
            response = self.es.get(index=self.index_name, id=job_id)
            job_data = response["_source"]
            job_data["id"] = response["_id"]
            return Job(**job_data)
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job from the index"""
        try:
            response = self.es.delete(index=self.index_name, id=job_id)
            return response["result"] == "deleted"
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e}")
            return False
    
    def get_similar_jobs(self, job_id: str, limit: int = 10) -> List[Job]:
        """Get similar jobs based on content"""
        try:
            # Get the original job
            original_job = self.get_job_by_id(job_id)
            if not original_job:
                return []
            
            # Build more like this query
            query = {
                "query": {
                    "more_like_this": {
                        "fields": ["title", "description", "skills_text"],
                        "like": [
                            {"_index": self.index_name, "_id": job_id}
                        ],
                        "min_term_freq": 1,
                        "max_query_terms": 12
                    }
                },
                "size": limit
            }
            
            response = self.es.search(index=self.index_name, body=query)
            
            jobs = []
            for hit in response["hits"]["hits"]:
                if hit["_id"] != job_id:  # Exclude the original job
                    job_data = hit["_source"]
                    job_data["id"] = hit["_id"]
                    jobs.append(Job(**job_data))
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting similar jobs: {e}")
            return []
