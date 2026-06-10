from typing import List, Dict, Any, Optional, Tuple
import logging
import math
import time
from ..models.job import Job, JobSearchQuery, JobSearchResult
from ..models.candidate import Candidate, CandidateJobMatch, CandidateProfile
from ..models.knowledge_graph import GraphSearchResult
from .elasticsearch_service import ElasticsearchService
from .knowledge_graph_service import KnowledgeGraphService
from .nlp_service import NLPService
from .reranking_service import RerankingService
from .feature_engineering_service import FeatureEngineeringService
from .candidate_generation_service import CandidateGenerationService

logger = logging.getLogger(__name__)

class HybridSearchService:
    def __init__(self):
        self.es_service = ElasticsearchService()
        self.kg_service = KnowledgeGraphService()
        self.nlp_service = NLPService()
        self.reranking_service = RerankingService()
        self.feature_service = FeatureEngineeringService()
        self.candidate_service = CandidateGenerationService()
        self.job_static_cache: Dict[str, Dict[str, float]] = {}
    
    def search_jobs_with_semantic_matching(
        self, 
        query: JobSearchQuery, 
        candidate: Optional[Candidate] = None
    ) -> JobSearchResult:
        """Perform hybrid search combining Elasticsearch and knowledge graph"""
        start_time = time.time()
        
        try:
            # Step 1: Parse and enrich the query using NLP and KG
            enriched_query = self._enrich_query(query.query)
            query_skills = enriched_query.get("all_skills") or enriched_query.get("skills") or []
            query_locations = (enriched_query.get("entities") or {}).get("GPE", [])
            
            # Step 2: Generate candidate pool from multiple sources
            kg_results = self.kg_service.find_semantic_matches(query.query)
            candidate_result = self.candidate_service.generate_candidates(
                query,
                lexical_k=200,
                semantic_k=200,
                kg_k=100,
                max_candidates=400,
            )
            
            # Cache query-independent job features
            for job in candidate_result.jobs:
                self._ensure_job_static_features(job)

            # Step 3: Apply feature engineering (query-aware)
            self.feature_service.build_features_for_jobs(
                query_text=query.query,
                jobs=candidate_result.jobs,
                query_skills=query_skills,
                query_locations=query_locations,
            )
            
            # Step 3.5: Apply hard-constraint filtering before reranking (if candidate provided)
            if candidate:
                filtered_jobs, filtered_reasons, prompts = self._filter_jobs_by_hard_constraints(candidate_result.jobs, candidate)
            else:
                filtered_jobs, filtered_reasons, prompts = candidate_result.jobs, {}, []

            # Step 4: Combine and re-rank results
            if candidate:
                final_results = self._rerank_with_candidate_profile(
                    filtered_jobs, 
                    candidate, 
                    kg_results
                )
            else:
                final_results = self._rerank_with_semantic_similarity(
                    filtered_jobs, 
                    kg_results,
                    query.query
                )
            
            # Step 5: Calculate final metrics
            search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            total_count = candidate_result.lexical_total_hits or len(candidate_result.jobs)
            total_pages = math.ceil(total_count / max(1, query.page_size))
            
            return JobSearchResult(
                jobs=final_results,
                total_count=total_count,
                page=query.page,
                page_size=query.page_size,
                total_pages=total_pages,
                search_time_ms=search_time,
                filtered_out_reasons=filtered_reasons if filtered_reasons else None,
                prompts=prompts or None,
                explanations={"candidate_sources": candidate_result.source_breakdown} if candidate_result.source_breakdown else None
            )
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return JobSearchResult(
                jobs=[],
                total_count=0,
                page=query.page,
                page_size=query.page_size,
                total_pages=0,
                search_time_ms=0
            )

    def _filter_jobs_by_hard_constraints(self, jobs: List[Job], candidate: Optional[Candidate]) -> Tuple[List[Job], Dict[str, str], List[str]]:
        """Filter out jobs that violate hard eligibility constraints for the candidate.

        Returns (filtered_jobs, filtered_out_reasons, prompts).
        """
        if not candidate:
            return jobs, {}, []

        filtered: List[Job] = []
        filtered_out_reasons: Dict[str, str] = {}
        prompts: List[str] = []

        # Normalize candidate info
        candidate_certs = set((candidate.certifications or []))
        candidate_langs = set((candidate.languages or []))
        candidate_visa = (candidate.visa_status or "").lower()
        candidate_degrees = [edu.degree.lower() for edu in (candidate.education or []) if getattr(edu, 'degree', None)]

        # Estimate years experience (fallback to skills years if dates missing)
        total_years = 0
        try:
            from datetime import datetime
            for exp in (candidate.experience or []):
                start = getattr(exp, 'start_date', None)
                end = getattr(exp, 'end_date', None) or datetime.utcnow()
                if start:
                    total_years += max(0, (end - start).days) / 365.25
        except Exception:
            pass
        if total_years == 0:
            total_years = sum((s.years_experience or 0) for s in (candidate.skills or []))

        def degree_level_value(d: str) -> int:
            mapping = {"high_school": 0, "associate": 1, "bachelor": 2, "master": 3, "doctorate": 4}
            for k, v in mapping.items():
                if k in d:
                    return v
            return -1

        candidate_degree_val = max([degree_level_value(d) for d in candidate_degrees], default=-1)

        for job in jobs:
            constraints = self.nlp_service.extract_hard_constraints(job.description or "")

            # Visa/work auth
            if constraints.get("requires_us_work_auth") and ("sponsor" in candidate_visa or "h1b" in candidate_visa):
                if constraints.get("no_visa_sponsorship", False):
                    filtered_out_reasons[job.id] = "Requires US work authorization; no sponsorship available"
                    continue  # candidate needs sponsorship but job cannot sponsor

            if constraints.get("no_visa_sponsorship") and ("sponsor" in candidate_visa or "h1b" in candidate_visa):
                filtered_out_reasons[job.id] = "Employer does not sponsor visas"
                continue

            # Remote/location – if job explicitly requires on-site in a location, lightweight check
            if constraints.get("remote_allowed") is False and job.remote_allowed is False:
                # If candidate has preferred_locations and none match job state/city, we still allow but keep job
                pass

            # Certifications (must-have)
            must_certs = set(constraints.get("must_have_certifications", []))
            if must_certs:
                # crude normalization upper-case compare
                cand_up = set(c.upper() for c in candidate_certs)
                if not must_certs.issubset(cand_up):
                    filtered_out_reasons[job.id] = "Missing required certification(s)"
                    if not candidate_certs:
                        prompts.append("Do you hold any of the required certifications (e.g., AWS, PMP, CISSP)?")
                    continue

            # Minimum degree
            min_deg = constraints.get("min_degree")
            if min_deg is not None:
                required_val = degree_level_value(min_deg)
                if candidate_degree_val < required_val:
                    filtered_out_reasons[job.id] = "Minimum degree requirement not met"
                    continue

            # Minimum years experience
            min_years = constraints.get("min_years_experience")
            if isinstance(min_years, int) and total_years < min_years:
                filtered_out_reasons[job.id] = "Minimum years of relevant experience not met"
                continue

            # Language requirements (must-have)
            req_langs = set(l.lower() for l in constraints.get("language_requirements", []))
            if req_langs:
                cand_langs = set(l.lower() for l in candidate_langs)
                if not req_langs.issubset(cand_langs):
                    filtered_out_reasons[job.id] = "Language fluency requirement not met"
                    if not candidate_langs:
                        prompts.append("Which languages are you fluent in (spoken and written)?")
                    continue
            # Security clearance and licensure are treated as non-trivial; prompt if required
            if constraints.get("security_clearance"):
                prompts.append("Do you currently hold an active security clearance (e.g., Secret, TS/SCI)?")
            if constraints.get("licensure_requirements"):
                prompts.append("Do you hold any required professional licenses (e.g., CPA, PE, RN)?")
            filtered.append(job)

        # Deduplicate prompts
        prompts = list(dict.fromkeys(prompts))
        return filtered, filtered_out_reasons, prompts
    
    def _enrich_query(self, query_text: str) -> Dict[str, Any]:
        """Enrich query using NLP and knowledge graph"""
        try:
            # Extract entities from query
            entities = self.nlp_service.extract_entities_from_text(query_text)
            
            # Extract skills from query
            skills = self.nlp_service.extract_skills_from_text(query_text)
            
            # Find related skills using knowledge graph
            related_skills = self.kg_service.find_related_skills(skills)
            
            # Get semantic embeddings
            embeddings = self.nlp_service.get_sentence_embeddings([query_text])
            
            return {
                "original_query": query_text,
                "entities": entities,
                "skills": skills,
                "related_skills": related_skills,
                "all_skills": list(set(skills + related_skills)),
                "embeddings": embeddings[0] if embeddings else [],
                "keywords": self.nlp_service.extract_keywords(query_text)
            }
            
        except Exception as e:
            logger.error(f"Error enriching query: {e}")
            return {"original_query": query_text, "skills": [], "related_skills": []}
    
    def _rerank_with_candidate_profile(
        self, 
        jobs: List[Job], 
        candidate: Candidate, 
        kg_results: GraphSearchResult
    ) -> List[Job]:
        """Re-rank jobs based on candidate profile matching"""
        try:
            job_scores = []
            
            for job in jobs:
                # Calculate match score using knowledge graph
                match_data = self.kg_service.calculate_job_candidate_match(job.id, candidate.id)
                
                # Fallback: Calculate skill match directly if KG returns empty/no data
                if not match_data or match_data.get("skill_match_ratio", 0.0) == 0.0:
                    match_data = self._calculate_direct_skill_match(job, candidate)
                
                # Calculate semantic similarity (includes job description + title)
                job_text = f"{job.title} {job.description}"
                candidate_text = f"{candidate.summary or ''} {' '.join([skill.name for skill in candidate.skills])}"
                semantic_similarity = self.nlp_service.calculate_semantic_similarity(
                    job_text, candidate_text
                )
                
                # Calculate location match
                location_match = self._calculate_location_match(job, candidate)
                
                # Calculate salary match
                salary_match = self._calculate_salary_match(job, candidate)
                
                # Calculate visa match
                visa_match = self._calculate_visa_match(job, candidate)
                
                # Calculate overall score with explanation
                overall_score, score_explanation = self._calculate_overall_score(
                    match_data, semantic_similarity, location_match, 
                    salary_match, visa_match, candidate, job
                )
                
                # Set the rerank_score and explanation on the job object
                job_with_score = job.copy()
                job_with_score.rerank_score = overall_score
                
                # Add match explanation to search_metadata for tooltip
                if not job_with_score.search_metadata:
                    job_with_score.search_metadata = {}
                job_with_score.search_metadata["match_explanation"] = score_explanation
                
                job_scores.append((job_with_score, overall_score))
            
            # Sort by score (descending)
            job_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Log top scores for debugging
            if job_scores:
                top_jobs_info = []
                for job, score in job_scores[:3]:
                    top_jobs_info.append(f"{job.title}: {score:.3f}")
                logger.info(f"Top 3 job matches: {', '.join(top_jobs_info)}")
            
            return [job for job, score in job_scores]
            
        except Exception as e:
            logger.error(f"Error re-ranking with candidate profile: {e}")
            return jobs
    
    def _rerank_with_semantic_similarity(
        self, 
        jobs: List[Job], 
        kg_results: GraphSearchResult,
        query_text: str
    ) -> List[Job]:
        """Re-rank jobs based on semantic similarity to query"""
        try:
            job_scores = []
            
            for job in jobs:
                # Calculate semantic similarity to original query
                job_text = f"{job.title} {job.description}"
                
                similarity = self.nlp_service.calculate_semantic_similarity(
                    job_text, query_text
                ) if query_text else 0.0
                
                # Boost score if job appears in KG results
                kg_boost = 1.0
                for node in kg_results.nodes:
                    if node.type.value == "Job" and node.id == job.id:
                        kg_boost = 1.5
                        break
                
                final_score = similarity * kg_boost
                
                # Set the rerank_score on the job object
                job_with_score = job.copy()
                job_with_score.rerank_score = final_score
                job_scores.append((job_with_score, final_score))
            
            # Sort by score (descending)
            job_scores.sort(key=lambda x: x[1], reverse=True)
            
            return [job for job, score in job_scores]
            
        except Exception as e:
            logger.error(f"Error re-ranking with semantic similarity: {e}")
            return jobs

    def _ensure_job_static_features(self, job: Job) -> None:
        if job.id in self.job_static_cache:
            job.search_metadata = job.search_metadata or {}
            job.search_metadata["static_features"] = self.job_static_cache[job.id]
            return
        static_features = {
            "skill_count": float(len(job.required_skills or [])),
            "preferred_skill_count": float(len(job.preferred_skills or [])),
        }
        try:
            static_features["kg_required_skill_1hop"] = float(
                self.kg_service.count_job_skill_matches(job.id, job.required_skills, hops=1)
            )
            static_features["kg_required_skill_2hop"] = float(
                self.kg_service.count_job_skill_matches(job.id, job.required_skills, hops=2)
            )
        except Exception as exc:
            logger.warning(f"Static KG feature failed for job {job.id}: {exc}")
        self.job_static_cache[job.id] = static_features
        job.search_metadata = job.search_metadata or {}
        job.search_metadata["static_features"] = static_features
    
    def _calculate_direct_skill_match(self, job: Job, candidate: Candidate) -> Dict[str, Any]:
        """
        Calculate skill match directly without Knowledge Graph (fallback method)
        This provides more robust scoring when KG is unavailable
        """
        try:
            # Get candidate skills
            candidate_skills = set()
            if candidate.skills:
                candidate_skills = {skill.name.lower() for skill in candidate.skills}
            
            # Get job skills (required + preferred)
            job_skills = set()
            if job.required_skills:
                job_skills.update(skill.lower() for skill in job.required_skills)
            if job.preferred_skills:
                job_skills.update(skill.lower() for skill in job.preferred_skills)
            
            # Calculate matches
            if not job_skills:
                # If job has no skills listed, use neutral score
                return {
                    "skill_match_ratio": 0.5,
                    "matching_skills": 0,
                    "total_job_skills": 0,
                    "total_candidate_skills": len(candidate_skills),
                    "matched_skill_names": []
                }
            
            matching_skills = candidate_skills.intersection(job_skills)
            skill_match_ratio = len(matching_skills) / len(job_skills) if job_skills else 0.0
            
            logger.debug(f"Direct skill match: {len(matching_skills)}/{len(job_skills)} = {skill_match_ratio:.2f}")
            logger.debug(f"Matching skills: {matching_skills}")
            
            return {
                "skill_match_ratio": skill_match_ratio,
                "matching_skills": len(matching_skills),
                "total_job_skills": len(job_skills),
                "total_candidate_skills": len(candidate_skills),
                "matched_skill_names": list(matching_skills)
            }
            
        except Exception as e:
            logger.error(f"Error in direct skill match calculation: {e}")
            return {
                "skill_match_ratio": 0.5,  # Neutral fallback
                "matching_skills": 0,
                "total_job_skills": 0,
                "total_candidate_skills": 0,
                "matched_skill_names": []
            }
    
    def _calculate_location_match(self, job: Job, candidate: Candidate) -> float:
        """Calculate location match score"""
        if not candidate.location or not job.location:
            return 0.5  # Neutral score if no location info
        
        # Simple location matching (can be enhanced with geographic distance)
        job_location = f"{job.location.city}, {job.location.state}".lower()
        candidate_location = candidate.location.lower()
        
        if candidate_location in job_location or job_location in candidate_location:
            return 1.0
        
        # Check if both are in the same state
        if job.location.state.lower() in candidate_location:
            return 0.8
        
        return 0.3
    
    def _calculate_salary_match(self, job: Job, candidate: Candidate) -> float:
        """Calculate salary match score"""
        if not candidate.salary_expectation or not job.salary:
            return 0.5  # Neutral score if no salary info
        
        candidate_salary = candidate.salary_expectation
        job_min = job.salary.min_salary or 0
        job_max = job.salary.max_salary or job_min
        
        # Check if candidate expectation is within job range
        if job_min <= candidate_salary <= job_max:
            return 1.0
        
        # Check if candidate expectation is close to job range
        if candidate_salary < job_min:
            # Candidate expects less than minimum - might be underqualified
            return 0.3
        else:
            # Candidate expects more than maximum - might be overqualified
            return 0.7
    
    def _calculate_visa_match(self, job: Job, candidate: Candidate) -> float:
        """Calculate visa sponsorship match score"""
        if not candidate.visa_status:
            return 0.5  # Neutral if no visa info
        
        # If candidate needs visa sponsorship
        if "h1b" in candidate.visa_status.lower() or "sponsor" in candidate.visa_status.lower():
            if job.visa_sponsorship:
                return 1.0
            else:
                return 0.0
        
        # If candidate doesn't need visa sponsorship
        return 0.8
    
    def _calculate_overall_score(
        self, 
        match_data: Dict[str, Any], 
        semantic_similarity: float, 
        location_match: float, 
        salary_match: float, 
        visa_match: float,
        candidate: Candidate = None,
        job: Job = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate overall match score with improved weights and logging
        
        Returns both the score and an explanation dictionary for tooltip
        
        Semantic similarity now includes job description matching (increased weight)
        """
        # Adjusted weights - increased semantic similarity since it includes job description
        weights = {
            "skill_match": 0.35,           # Reduced from 0.4
            "semantic_similarity": 0.30,   # Increased from 0.2 (includes job description!)
            "location_match": 0.15,
            "salary_match": 0.12,          # Slightly reduced
            "visa_match": 0.08             # Slightly reduced
        }
        
        # Get skill match ratio from match data (from KG or direct calculation)
        skill_match = match_data.get("skill_match_ratio", 0.0)
        
        # Calculate individual weighted scores
        weighted_scores = {
            "skill_match": weights["skill_match"] * skill_match,
            "semantic_similarity": weights["semantic_similarity"] * semantic_similarity,
            "location_match": weights["location_match"] * location_match,
            "salary_match": weights["salary_match"] * salary_match,
            "visa_match": weights["visa_match"] * visa_match
        }
        
        # Calculate overall weighted score
        overall_score = sum(weighted_scores.values())
        
        # Build explanation for tooltip
        explanation = {
            "total_score": overall_score,
            "components": {
                "Skill Match": {
                    "score": skill_match,
                    "weight": weights["skill_match"],
                    "contribution": weighted_scores["skill_match"],
                    "percentage": int(skill_match * 100),
                    "details": {
                        "matched_skills": match_data.get("matched_skill_names", []),
                        "matching_count": match_data.get("matching_skills", 0),
                        "total_required": match_data.get("total_job_skills", 0)
                    }
                },
                "Job Description Match": {
                    "score": semantic_similarity,
                    "weight": weights["semantic_similarity"],
                    "contribution": weighted_scores["semantic_similarity"],
                    "percentage": int(semantic_similarity * 100)
                },
                "Location Match": {
                    "score": location_match,
                    "weight": weights["location_match"],
                    "contribution": weighted_scores["location_match"],
                    "percentage": int(location_match * 100)
                },
                "Salary Match": {
                    "score": salary_match,
                    "weight": weights["salary_match"],
                    "contribution": weighted_scores["salary_match"],
                    "percentage": int(salary_match * 100)
                },
                "Visa Sponsorship": {
                    "score": visa_match,
                    "weight": weights["visa_match"],
                    "contribution": weighted_scores["visa_match"],
                    "percentage": int(visa_match * 100)
                }
            }
        }
        
        # Sort components by contribution (for "top 3 features")
        sorted_components = sorted(
            explanation["components"].items(),
            key=lambda x: x[1]["contribution"],
            reverse=True
        )
        explanation["top_features"] = [
            {
                "name": name,
                "percentage": comp["percentage"],
                "details": comp.get("details")
            }
            for name, comp in sorted_components[:3]
        ]
        
        # Detailed logging for debugging (only log top matches to avoid spam)
        if job and overall_score >= 0.5:  # Only log matches above 50%
            logger.info(f"High match score for '{job.title}': {overall_score:.3f} ({overall_score*100:.1f}%)")
            logger.info(f"  Breakdown: Skills={skill_match:.2f}, Semantic={semantic_similarity:.2f}, Location={location_match:.2f}, Salary={salary_match:.2f}, Visa={visa_match:.2f}")
            
            if match_data.get("matched_skill_names"):
                logger.info(f"  Matched skills: {', '.join(match_data.get('matched_skill_names', []))}")
        
        return overall_score, explanation
    
    def get_job_recommendations(
        self, 
        candidate: Candidate, 
        limit: int = 10
    ) -> List[CandidateJobMatch]:
        """Get personalized job recommendations for a candidate using intelligent resume decomposition"""
        try:
            logger.info(f"Getting intelligent recommendations for candidate: {candidate.name}")
            
            # Step 1: Intelligent query decomposition from resume
            decomposed_query = self._decompose_resume_to_query(candidate)
            logger.info(f"Decomposed query: {decomposed_query}")
            
            # Step 2: Create comprehensive search query
            query = JobSearchQuery(
                query=decomposed_query["query"],
                location=decomposed_query.get("location"),
                min_salary=decomposed_query.get("min_salary"),
                max_salary=decomposed_query.get("max_salary"),
                job_type=decomposed_query.get("job_type"),
                experience_level=decomposed_query.get("experience_level"),
                remote_allowed=decomposed_query.get("remote_allowed"),
                visa_sponsorship=decomposed_query.get("visa_sponsorship"),
                required_skills=decomposed_query.get("required_skills", []),
                preferred_skills=decomposed_query.get("preferred_skills", []),
                page_size=limit * 2  # Get more results for better matching
            )
            
            # Step 3: Perform intelligent search with candidate context
            logger.info(f"Searching with query: {query.query}")
            search_results = self.search_jobs_with_semantic_matching(query, candidate)
            logger.info(f"Found {len(search_results.jobs)} jobs from intelligent search")
            
            # If no results from semantic search, try direct Elasticsearch search
            if len(search_results.jobs) == 0:
                logger.info("No results from semantic search, trying direct Elasticsearch search")
                search_results = self.es_service.search_jobs(query)
                logger.info(f"Found {len(search_results.jobs)} jobs from direct Elasticsearch search")
            
            # Step 4: Advanced candidate-job matching with multiple factors
            matches = []
            for job in search_results.jobs:
                match_analysis = self._analyze_job_candidate_match(job, candidate)
                
                match = CandidateJobMatch(
                    job_id=job.id,
                    candidate_id=candidate.id,
                    match_score=match_analysis["overall_score"],
                    matching_skills=match_analysis["matching_skills"],
                    missing_skills=match_analysis["missing_skills"],
                    experience_match=match_analysis["experience_match"],
                    location_match=match_analysis["location_match"],
                    salary_match=match_analysis["salary_match"],
                    visa_match=match_analysis["visa_match"],
                    overall_fit=match_analysis["overall_fit"]
                )
                
                matches.append(match)
            
            # Step 5: Sort by comprehensive match score and return top matches
            matches.sort(key=lambda x: x.match_score, reverse=True)
            logger.info(f"Created {len(matches)} intelligent matches, returning top {min(limit, len(matches))}")
            return matches[:limit]
            
        except Exception as e:
            logger.error(f"Error getting intelligent job recommendations: {e}")
            return []
    
    def _decompose_resume_to_query(self, candidate: Candidate) -> Dict[str, Any]:
        """Intelligently decompose resume into comprehensive search query"""
        try:
            # Extract skills and create skill-based query
            candidate_skills = [skill.name for skill in candidate.skills]
            skill_query = " ".join(candidate_skills)
            
            # Extract experience keywords
            experience_keywords = []
            for exp in candidate.experience:
                if hasattr(exp, 'position') and exp.position:
                    experience_keywords.append(exp.position)
                if hasattr(exp, 'company') and exp.company:
                    experience_keywords.append(exp.company)
            
            # Extract education keywords
            education_keywords = []
            for edu in candidate.education:
                if hasattr(edu, 'degree') and edu.degree:
                    education_keywords.append(edu.degree)
                if hasattr(edu, 'field_of_study') and edu.field_of_study:
                    education_keywords.append(edu.field_of_study)
            
            # Create comprehensive query
            query_parts = []
            if candidate.summary:
                query_parts.append(candidate.summary)
            if skill_query:
                query_parts.append(skill_query)
            if experience_keywords:
                query_parts.extend(experience_keywords[:3])  # Top 3 experience keywords
            if education_keywords:
                query_parts.extend(education_keywords[:2])  # Top 2 education keywords
            
            comprehensive_query = " ".join(query_parts)
            
            # Determine experience level based on years of experience
            total_years = sum(skill.years_experience or 0 for skill in candidate.skills)
            if total_years >= 5:
                experience_level = "senior"
            elif total_years >= 2:
                experience_level = "mid"
            else:
                experience_level = "entry"
            
            # Determine job type preferences
            job_type = "full_time"  # Default
            
            # Determine salary expectations based on experience
            if experience_level == "senior":
                min_salary = 80000
            elif experience_level == "mid":
                min_salary = 60000
            else:
                min_salary = 40000
            
            return {
                "query": comprehensive_query,
                "location": candidate.location,
                "min_salary": min_salary,
                "job_type": job_type,
                "experience_level": experience_level,
                "remote_allowed": True,  # Default to flexible
                "visa_sponsorship": candidate.visa_status is not None,
                "required_skills": candidate_skills[:5],  # Top 5 skills
                "preferred_skills": candidate_skills[5:10] if len(candidate_skills) > 5 else []
            }
            
        except Exception as e:
            logger.error(f"Error decomposing resume to query: {e}")
            # Fallback to simple query
            candidate_skills = [skill.name for skill in candidate.skills]
            return {
                "query": f"{candidate.summary or ''} {' '.join(candidate_skills)}",
                "location": candidate.location,
                "min_salary": None,
                "job_type": None,
                "experience_level": None,
                "remote_allowed": None,
                "visa_sponsorship": None,
                "required_skills": candidate_skills,
                "preferred_skills": []
            }
    
    def _analyze_job_candidate_match(self, job: Job, candidate: Candidate) -> Dict[str, Any]:
        """Analyze comprehensive match between job and candidate"""
        try:
            # Extract job skills
            job_skills = []
            for skill in job.required_skills + job.preferred_skills:
                if isinstance(skill, str):
                    job_skills.append(skill.lower())
            
            # Extract candidate skills
            candidate_skills = [skill.name.lower() for skill in candidate.skills]
            
            # Advanced skill matching with fuzzy matching
            matching_skills = []
            missing_skills = []
            
            for job_skill in job_skills:
                matched = False
                for candidate_skill in candidate_skills:
                    # Check for exact match
                    if candidate_skill == job_skill:
                        matching_skills.append(candidate_skill)
                        matched = True
                        break
                    # Check for partial match
                    elif candidate_skill in job_skill or job_skill in candidate_skill:
                        matching_skills.append(candidate_skill)
                        matched = True
                        break
                    # Check for keyword overlap
                    elif any(word in job_skill for word in candidate_skill.split()):
                        matching_skills.append(candidate_skill)
                        matched = True
                        break
                
                if not matched:
                    missing_skills.append(job_skill)
            
            # Calculate skill match ratio
            skill_match_ratio = len(matching_skills) / max(len(job_skills), 1) if job_skills else 0.0
            
            # Calculate other match components
            location_match = self._calculate_location_match(job, candidate)
            salary_match = self._calculate_salary_match(job, candidate)
            visa_match = self._calculate_visa_match(job, candidate)
            
            # Calculate experience match
            experience_match = self._calculate_experience_match(job, candidate)
            
            # Calculate overall score with weights
            overall_score = (
                skill_match_ratio * 0.4 +
                experience_match * 0.3 +
                location_match * 0.15 +
                salary_match * 0.1 +
                visa_match * 0.05
            )
            
            # Determine overall fit
            if overall_score >= 0.8:
                overall_fit = "excellent"
            elif overall_score >= 0.6:
                overall_fit = "good"
            elif overall_score >= 0.4:
                overall_fit = "fair"
            else:
                overall_fit = "poor"
            
            return {
                "overall_score": overall_score,
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "experience_match": experience_match,
                "location_match": location_match > 0.5,
                "salary_match": salary_match > 0.5,
                "visa_match": visa_match > 0.5,
                "overall_fit": overall_fit
            }
            
        except Exception as e:
            logger.error(f"Error analyzing job-candidate match: {e}")
            return {
                "overall_score": 0.0,
                "matching_skills": [],
                "missing_skills": [],
                "experience_match": 0.0,
                "location_match": False,
                "salary_match": False,
                "visa_match": False,
                "overall_fit": "poor"
            }
    
    def _calculate_experience_match(self, job: Job, candidate: Candidate) -> float:
        """Calculate experience level match between job and candidate"""
        try:
            # Get candidate's total experience
            total_years = sum(skill.years_experience or 0 for skill in candidate.skills)
            
            # Map job experience level to years
            job_level = job.experience_level
            if job_level == "entry":
                required_years = 0
            elif job_level == "mid":
                required_years = 2
            elif job_level == "senior":
                required_years = 5
            else:
                required_years = 2  # Default
            
            # Calculate match ratio
            if total_years >= required_years:
                return 1.0
            elif total_years > 0:
                return total_years / max(required_years, 1)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating experience match: {e}")
            return 0.0

    def _determine_overall_fit(
        self, 
        skill_match: float, 
        location_match: float, 
        salary_match: float, 
        visa_match: float
    ) -> str:
        """Determine overall fit category"""
        avg_score = (skill_match + location_match + salary_match + visa_match) / 4
        
        if avg_score >= 0.8:
            return "excellent"
        elif avg_score >= 0.6:
            return "good"
        elif avg_score >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def analyze_job_market_trends(self, skills: List[str]) -> Dict[str, Any]:
        """Analyze job market trends for given skills"""
        try:
            trends = {
                "skill_demand": {},
                "related_skills": {},
                "salary_ranges": {},
                "locations": {},
                "companies": {}
            }
            
            for skill in skills:
                # Find related skills
                related = self.kg_service.find_related_skills([skill])
                trends["related_skills"][skill] = related
                
                # Get skill relationships
                relationships = self.kg_service.get_skill_relationships(skill)
                trends["skill_demand"][skill] = len(relationships)
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing job market trends: {e}")
            return {}
    
    def search_jobs_with_reranking(
        self,
        query: JobSearchQuery,
        user_description: Optional[str] = None,
        candidate_profile: Optional[CandidateProfile] = None,
        reranking_factors: Optional[Dict[str, float]] = None,
        include_explanations: bool = False
    ) -> JobSearchResult:
        """
        Search for jobs with personalized reranking based on user description and candidate profile
        
        Args:
            query: Job search query
            user_description: User's specific job description or preferences
            candidate_profile: Candidate's resume/profile information
            reranking_factors: Custom weights for different reranking factors
            include_explanations: Whether to include detailed explanations
        
        Returns:
            Reranked JobSearchResult with personalized job recommendations
        """
        try:
            start_time = time.time()
            
            # First, perform regular hybrid search
            search_results = self.search_jobs_with_semantic_matching(query, candidate_profile.candidate if candidate_profile else None)
            
            if not search_results.jobs:
                logger.warning("No jobs found for reranking")
                return search_results
            
            # Perform reranking
            reranking_start = time.time()
            reranked_results = self.reranking_service.rerank_search_results(
                search_results=search_results,
                user_description=user_description,
                candidate_profile=candidate_profile,
                reranking_factors=reranking_factors
            )
            reranking_time = (time.time() - reranking_start) * 1000
            
            # Add reranking metadata
            reranked_results.reranking_time_ms = reranking_time
            
            # Get reranking statistics
            reranking_stats = self.reranking_service.get_reranking_statistics(reranked_results)
            reranked_results.reranking_statistics = reranking_stats
            
            # Add explanations if requested
            if include_explanations:
                explanations = {}
                for job in reranked_results.jobs[:5]:  # Explain top 5 jobs
                    explanations[job.id] = self.reranking_service.get_reranking_explanation(
                        job, user_description, candidate_profile
                    )
                reranked_results.explanations = explanations
            
            total_time = (time.time() - start_time) * 1000
            logger.info(f"Reranked search completed in {total_time:.2f}ms (reranking: {reranking_time:.2f}ms)")
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"Error in reranked search: {e}")
            # Fallback to regular search
            return self.search_jobs_with_semantic_matching(query, candidate_profile.candidate if candidate_profile else None)
    
    def get_personalized_recommendations(
        self,
        candidate_profile: CandidateProfile,
        user_description: Optional[str] = None,
        limit: int = 10,
        reranking_factors: Optional[Dict[str, float]] = None
    ) -> JobSearchResult:
        """
        Get personalized job recommendations based on candidate profile
        
        Args:
            candidate_profile: Candidate's resume/profile information
            user_description: User's specific job description or preferences
            limit: Maximum number of recommendations
            reranking_factors: Custom weights for different reranking factors
        
        Returns:
            Personalized job recommendations with reranking
        """
        try:
            # Create a broad search query based on candidate skills
            candidate_skills = candidate_profile.extracted_skills[:5]  # Top 5 skills
            query_text = " ".join(candidate_skills) if candidate_skills else "software engineer"
            
            # Create search query
            search_query = JobSearchQuery(
                query=query_text,
                page=1,
                page_size=limit * 2  # Get more results for better reranking
            )
            
            # Add location preference if available
            if candidate_profile.candidate.preferred_locations:
                search_query.location = candidate_profile.candidate.preferred_locations[0]
            
            # Perform reranked search
            results = self.search_jobs_with_reranking(
                query=search_query,
                user_description=user_description,
                candidate_profile=candidate_profile,
                reranking_factors=reranking_factors,
                include_explanations=True
            )
            
            # Limit results
            results.jobs = results.jobs[:limit]
            results.page_size = limit
            
            logger.info(f"Generated {len(results.jobs)} personalized recommendations")
            return results
            
        except Exception as e:
            logger.error(f"Error generating personalized recommendations: {e}")
            return JobSearchResult(
                jobs=[],
                total_count=0,
                page=1,
                page_size=limit,
                total_pages=0,
                search_time_ms=0
            )
