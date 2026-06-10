import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime
from ..models.job import Job, JobSearchResult
from ..models.candidate import Candidate, CandidateProfile
from .nlp_service import NLPService
from .knowledge_graph_service import KnowledgeGraphService
from .elasticsearch_service import ElasticsearchService
from .ai_scoring_service import AIScoringService

logger = logging.getLogger(__name__)

class RerankingService:
    def __init__(self):
        self.nlp_service = NLPService()
        self.kg_service = KnowledgeGraphService()
        self.es_service = ElasticsearchService()
        self.ai_scoring_service = AIScoringService()
        
        # Reranking weights (can be tuned based on performance)
        self.weights = {
            "skill_match": 0.35,      # Technical skills alignment
            "experience_match": 0.25,  # Experience level compatibility
            "location_preference": 0.15, # Location preferences
            "salary_expectation": 0.10,  # Salary alignment
            "semantic_similarity": 0.10, # Semantic content similarity
            "company_preference": 0.05   # Company/industry preferences
        }
        self.feature_labels = {
            "kg_skill_1hop_count": "SkillPath(Job→Requires→QuerySkill)",
            "kg_skill_2hop_count": "SkillPath(Job→RelatedSkill→QuerySkill)",
            "kg_skill_related_ratio": "RelatedSkillRatio",
            "kg_skill_shortest_path": "KGShortestPath(QuerySkill→Job)",
            "kg_location_shortest_path": "KGShortestPath(Location)",
            "kg_company_overlap_proxy": "CompanyOverlap",
            "lexical_es_score": "ElasticsearchScore",
            "lexical_title_exact": "TitleExactMatch",
            "lexical_skill_overlap_ratio": "SkillOverlap",
            "lexical_filter_location_match": "LocationMatch",
            "semantic_title": "SemanticSim(Title)",
            "semantic_description": "SemanticSim(Description)",
            "semantic_skills": "SemanticSim(Skills)",
            "skill_count": "RequiredSkillCount",
            "preferred_skill_count": "PreferredSkillCount",
            "kg_required_skill_1hop": "SkillPath(Job→Requires)",
            "kg_required_skill_2hop": "SkillPath(Job→RelatedSkill)"
        }
    
    def rerank_with_keywords(
        self,
        search_results: JobSearchResult,
        selected_keywords: Dict[str, Any],
        base_rerank_score: Optional[float] = None,
        keyword_weights: Optional[Dict[str, float]] = None
    ) -> JobSearchResult:
        """
        Rerank search results based on selected keywords from user query
        
        Args:
            search_results: Original search results
            selected_keywords: Dictionary with selected keywords:
                {
                    "job_titles": List[str],
                    "skills": List[str],
                    "salary": {"min": int, "max": int} or None,
                    "locations": List[str]
                }
            base_rerank_score: Optional base rerank score to combine with keyword scores
        
        Returns:
            Reranked JobSearchResult with updated scores
        """
        try:
            if not search_results.jobs:
                logger.warning("No jobs to rerank with keywords")
                return search_results
            
            logger.info(f"Reranking {len(search_results.jobs)} jobs with keywords")
            
            # Keyword-based weights (use provided weights or defaults)
            if keyword_weights is None:
                keyword_weights = {
                    "job_title": 0.30,
                    "skill": 0.25,
                    "location": 0.20,
                    "salary": 0.15,
                    "other": 0.10
                }
            
            reranked_jobs = []
            for job in search_results.jobs:
                # Calculate keyword match scores
                keyword_scores = self._calculate_keyword_match_scores(job, selected_keywords)
                
                # Calculate weighted keyword score
                keyword_score = (
                    keyword_scores["job_title"] * keyword_weights["job_title"] +
                    keyword_scores["skill"] * keyword_weights["skill"] +
                    keyword_scores["location"] * keyword_weights["location"] +
                    keyword_scores["salary"] * keyword_weights["salary"] +
                    keyword_scores["other"] * keyword_weights["other"]
                )
                
                # Combine with base rerank score if provided
                if base_rerank_score is not None and hasattr(job, 'rerank_score') and job.rerank_score:
                    # Weighted combination: 60% keyword score, 40% base rerank score
                    final_score = keyword_score * 0.6 + job.rerank_score * 0.4
                else:
                    final_score = keyword_score
                
                # Create job with updated rerank score
                job_with_score = job.copy()
                job_with_score.rerank_score = final_score
                reranked_jobs.append(job_with_score)
            
            # Sort by rerank score (descending)
            reranked_jobs.sort(key=lambda x: x.rerank_score, reverse=True)
            
            # Create new search result
            reranked_result = JobSearchResult(
                jobs=reranked_jobs,
                total_count=search_results.total_count,
                page=search_results.page,
                page_size=search_results.page_size,
                total_pages=search_results.total_pages,
                search_time_ms=search_results.search_time_ms
            )
            
            logger.info(f"Keyword-based reranking completed. Top job score: {reranked_jobs[0].rerank_score:.3f}")
            return reranked_result
            
        except Exception as e:
            logger.error(f"Error in keyword-based reranking: {e}")
            return search_results
    
    def _calculate_keyword_match_scores(
        self,
        job: Job,
        selected_keywords: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate match scores for each keyword category"""
        scores = {
            "job_title": 0.0,
            "skill": 0.0,
            "location": 0.0,
            "salary": 0.0,
            "other": 0.5  # Default neutral score
        }
        
        # Job title match
        selected_titles = selected_keywords.get("job_titles", [])
        if selected_titles:
            job_title_lower = job.title.lower()
            for title in selected_titles:
                if title.lower() in job_title_lower:
                    scores["job_title"] = 1.0
                    break
                # Partial match
                title_words = title.lower().split()
                if any(word in job_title_lower for word in title_words if len(word) > 3):
                    scores["job_title"] = max(scores["job_title"], 0.7)
        
        # Skill match
        selected_skills = selected_keywords.get("skills", [])
        if selected_skills:
            job_skills = set(skill.lower() for skill in (job.required_skills or []))
            job_skills.update(skill.lower() for skill in (job.preferred_skills or []))
            
            matching_skills = sum(
                1 for skill in selected_skills
                if skill.lower() in job_skills or any(
                    skill.lower() in job_skill for job_skill in job_skills
                )
            )
            
            if matching_skills > 0:
                scores["skill"] = min(matching_skills / len(selected_skills), 1.0)
        
        # Location match
        selected_locations = selected_keywords.get("locations", [])
        if selected_locations:
            job_location_str = f"{job.location.city}, {job.location.state}".lower()
            job_location_str += f" {job.location.city.lower()} {job.location.state.lower()}"
            
            for location in selected_locations:
                location_lower = location.lower()
                if location_lower in job_location_str:
                    scores["location"] = 1.0
                    break
                # Check for state match
                if job.location.state and location_lower in job.location.state.lower():
                    scores["location"] = max(scores["location"], 0.7)
                # Check for city match
                if job.location.city and location_lower in job.location.city.lower():
                    scores["location"] = max(scores["location"], 0.7)
                # Check for remote
                if "remote" in location_lower and job.remote_allowed:
                    scores["location"] = 1.0
        
        # Salary match
        selected_salary = selected_keywords.get("salary")
        if selected_salary and job.salary:
            job_min = job.salary.min_salary or 0
            job_max = job.salary.max_salary or job_min * 1.2
            
            selected_min = selected_salary.get("min", 0)
            selected_max = selected_salary.get("max", selected_min)
            
            # Check if salary ranges overlap
            if selected_max >= job_min and selected_min <= job_max:
                # Calculate overlap percentage
                overlap_min = max(selected_min, job_min)
                overlap_max = min(selected_max, job_max)
                overlap_range = overlap_max - overlap_min
                selected_range = selected_max - selected_min if selected_max > selected_min else 1
                scores["salary"] = min(overlap_range / selected_range, 1.0) if selected_range > 0 else 1.0
            else:
                # Check how close they are
                if selected_min > job_max:
                    gap = selected_min - job_max
                    scores["salary"] = max(0.0, 1.0 - (gap / selected_min))
                elif selected_max < job_min:
                    gap = job_min - selected_max
                    scores["salary"] = max(0.0, 1.0 - (gap / job_min))
        
        return scores
    
    def rerank_search_results(
        self,
        search_results: JobSearchResult,
        user_description: Optional[str] = None,
        candidate_profile: Optional[CandidateProfile] = None,
        reranking_factors: Optional[Dict[str, float]] = None
    ) -> JobSearchResult:
        """
        Rerank search results based on user description and candidate profile
        
        Args:
            search_results: Original search results from hybrid search
            user_description: User's specific job description/preferences
            candidate_profile: Candidate's resume/profile information
            reranking_factors: Custom weights for different factors
        
        Returns:
            Reranked JobSearchResult with updated scores and ordering
        """
        try:
            if not search_results.jobs:
                logger.warning("No jobs to rerank")
                return search_results
            
            logger.info(f"Reranking {len(search_results.jobs)} jobs")
            
            # Use custom weights if provided
            weights = reranking_factors if reranking_factors else self.weights
            
            # Calculate reranking scores for each job
            reranked_jobs = []
            for job in search_results.jobs:
                rerank_score = self._calculate_rerank_score(
                    job, user_description, candidate_profile, weights
                )
                
                # Create job with rerank score
                job_with_score = job.copy()
                job_with_score.rerank_score = rerank_score
                reranked_jobs.append(job_with_score)
            
            # Sort by rerank score (descending)
            reranked_jobs.sort(key=lambda x: x.rerank_score, reverse=True)
            
            # Create new search result with reranked jobs
            reranked_result = JobSearchResult(
                jobs=reranked_jobs,
                total_count=search_results.total_count,
                page=search_results.page,
                page_size=search_results.page_size,
                total_pages=search_results.total_pages,
                search_time_ms=search_results.search_time_ms
            )
            
            logger.info(f"Reranking completed. Top job score: {reranked_jobs[0].rerank_score:.3f}")
            return reranked_result
            
        except Exception as e:
            logger.error(f"Error in reranking: {e}")
            return search_results  # Return original results on error
    
    def _calculate_rerank_score(
        self,
        job: Job,
        user_description: Optional[str],
        candidate_profile: Optional[CandidateProfile],
        weights: Dict[str, float]
    ) -> float:
        """Calculate comprehensive rerank score for a job"""
        try:
            scores = {}
            
            # 1. Skill Match Score
            scores["skill_match"] = self._calculate_skill_match_score(job, candidate_profile)
            
            # 2. Experience Match Score
            scores["experience_match"] = self._calculate_experience_match_score(job, candidate_profile)
            
            # 3. Location Preference Score
            scores["location_preference"] = self._calculate_location_preference_score(job, candidate_profile)
            
            # 4. Salary Expectation Score
            scores["salary_expectation"] = self._calculate_salary_expectation_score(job, candidate_profile)
            
            # 5. Semantic Similarity Score
            scores["semantic_similarity"] = self._calculate_semantic_similarity_score(job, user_description)
            
            # 6. Company Preference Score
            scores["company_preference"] = self._calculate_company_preference_score(job, candidate_profile)
            
            # Calculate weighted final score
            final_score = sum(scores[factor] * weights[factor] for factor in weights)
            
            # Log detailed scores for debugging
            logger.debug(f"Job {job.id} scores: {scores}, final: {final_score:.3f}")
            
            return final_score
            
        except Exception as e:
            logger.error(f"Error calculating rerank score for job {job.id}: {e}")
            return 0.0
    
    def _calculate_skill_match_score(self, job: Job, candidate_profile: Optional[CandidateProfile]) -> float:
        """Calculate skill alignment score between job and candidate"""
        try:
            if not candidate_profile or not candidate_profile.extracted_skills:
                return 0.5  # Neutral score if no candidate skills
            
            job_skills = set(skill.lower() for skill in job.required_skills)
            candidate_skills = set(skill.lower() for skill in candidate_profile.extracted_skills)
            
            if not job_skills:
                return 0.5  # Neutral if job has no skills
            
            # Calculate skill overlap
            matching_skills = job_skills.intersection(candidate_skills)
            skill_match_ratio = len(matching_skills) / len(job_skills)
            
            # Bonus for having additional relevant skills
            additional_skills = candidate_skills - job_skills
            additional_bonus = min(len(additional_skills) * 0.05, 0.2)  # Max 20% bonus
            
            # Penalty for missing critical skills
            missing_skills = job_skills - candidate_skills
            missing_penalty = min(len(missing_skills) * 0.1, 0.3)  # Max 30% penalty
            
            final_score = skill_match_ratio + additional_bonus - missing_penalty
            return max(0.0, min(1.0, final_score))  # Clamp between 0 and 1
            
        except Exception as e:
            logger.error(f"Error calculating skill match score: {e}")
            return 0.5
    
    def _calculate_experience_match_score(self, job: Job, candidate_profile: Optional[CandidateProfile]) -> float:
        """Calculate experience level compatibility score"""
        try:
            if not candidate_profile:
                return 0.5
            
            # Map experience levels to numeric values
            experience_levels = {
                "entry": 1,
                "mid": 2,
                "senior": 3,
                "executive": 4
            }
            
            job_level = experience_levels.get(job.experience_level.value, 2)
            
            # Estimate candidate experience level from profile
            candidate_level = self._estimate_candidate_experience_level(candidate_profile)
            
            # Calculate compatibility score
            level_diff = abs(job_level - candidate_level)
            
            if level_diff == 0:
                return 1.0  # Perfect match
            elif level_diff == 1:
                return 0.8  # Good match (one level difference)
            elif level_diff == 2:
                return 0.5  # Moderate match
            else:
                return 0.2  # Poor match
            
        except Exception as e:
            logger.error(f"Error calculating experience match score: {e}")
            return 0.5
    
    def _estimate_candidate_experience_level(self, candidate_profile: CandidateProfile) -> int:
        """Estimate candidate's experience level from profile"""
        try:
            # Count years of experience from profile
            experience_count = len(candidate_profile.extracted_experience)
            
            # Look for seniority indicators in experience
            seniority_indicators = ["senior", "lead", "principal", "architect", "manager", "director"]
            has_seniority = any(
                any(indicator in exp.lower() for indicator in seniority_indicators)
                for exp in candidate_profile.extracted_experience
            )
            
            # Estimate level based on experience count and seniority
            if has_seniority or experience_count >= 5:
                return 3  # Senior
            elif experience_count >= 2:
                return 2  # Mid-level
            else:
                return 1  # Entry-level
                
        except Exception as e:
            logger.error(f"Error estimating candidate experience level: {e}")
            return 2  # Default to mid-level
    
    def _calculate_location_preference_score(self, job: Job, candidate_profile: Optional[CandidateProfile]) -> float:
        """Calculate location preference compatibility score"""
        try:
            if not candidate_profile or not candidate_profile.candidate.preferred_locations:
                return 0.5  # Neutral if no location preferences
            
            job_location = f"{job.location.city}, {job.location.state}".lower()
            candidate_locations = [loc.lower() for loc in candidate_profile.candidate.preferred_locations]
            
            # Check for exact match
            if job_location in candidate_locations:
                return 1.0
            
            # Check for state match
            job_state = job.location.state.lower()
            candidate_states = [loc.split(',')[-1].strip() for loc in candidate_locations]
            
            if job_state in candidate_states:
                return 0.7
            
            # Check for remote work preference
            if job.remote_allowed and any("remote" in loc for loc in candidate_locations):
                return 0.8
            
            return 0.3  # Low score for location mismatch
            
        except Exception as e:
            logger.error(f"Error calculating location preference score: {e}")
            return 0.5
    
    def _calculate_salary_expectation_score(self, job: Job, candidate_profile: Optional[CandidateProfile]) -> float:
        """Calculate salary expectation compatibility score"""
        try:
            if not candidate_profile or not candidate_profile.candidate.salary_expectation:
                return 0.5  # Neutral if no salary expectation
            
            candidate_salary = candidate_profile.candidate.salary_expectation
            
            if not job.salary or not job.salary.min_salary:
                return 0.5  # Neutral if job has no salary info
            
            job_min_salary = job.salary.min_salary
            job_max_salary = job.salary.max_salary or job_min_salary * 1.2
            
            # Calculate compatibility
            if candidate_salary <= job_max_salary and candidate_salary >= job_min_salary:
                return 1.0  # Perfect match
            elif candidate_salary <= job_max_salary * 1.1:
                return 0.8  # Slightly above but acceptable
            elif candidate_salary >= job_min_salary * 0.9:
                return 0.6  # Slightly below but might be negotiable
            else:
                return 0.2  # Significant mismatch
            
        except Exception as e:
            logger.error(f"Error calculating salary expectation score: {e}")
            return 0.5
    
    def _calculate_semantic_similarity_score(self, job: Job, user_description: Optional[str]) -> float:
        """Calculate semantic similarity between job and user description"""
        try:
            if not user_description:
                return 0.5  # Neutral if no user description
            
            # Combine job title and description for comparison
            job_text = f"{job.title} {job.description}"
            
            # Calculate semantic similarity
            similarity = self.nlp_service.calculate_semantic_similarity(job_text, user_description)
            
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity score: {e}")
            return 0.5
    
    def _calculate_company_preference_score(self, job: Job, candidate_profile: Optional[CandidateProfile]) -> float:
        """Calculate company/industry preference compatibility score"""
        try:
            if not candidate_profile:
                return 0.5
            
            # Look for company preferences in candidate profile
            # This could be enhanced with more sophisticated company matching
            company_name = job.company_name.lower()
            
            # Check if candidate has worked at similar companies
            candidate_companies = [
                exp.get("company", "").lower() 
                for exp in candidate_profile.candidate.experience
            ]
            
            # Simple company name similarity (could be enhanced with industry classification)
            for candidate_company in candidate_companies:
                if candidate_company and self._companies_similar(company_name, candidate_company):
                    return 0.8
            
            return 0.5  # Neutral if no company preferences
            
        except Exception as e:
            logger.error(f"Error calculating company preference score: {e}")
            return 0.5
    
    def _companies_similar(self, company1: str, company2: str) -> bool:
        """Check if two company names are similar"""
        try:
            # Simple similarity check - could be enhanced with fuzzy matching
            words1 = set(company1.split())
            words2 = set(company2.split())
            
            # Check for common words
            common_words = words1.intersection(words2)
            return len(common_words) > 0
            
        except Exception as e:
            logger.error(f"Error checking company similarity: {e}")
            return False
    
    def get_reranking_explanation(
        self,
        job: Job,
        user_description: Optional[str],
        candidate_profile: Optional[CandidateProfile]
    ) -> Dict[str, Any]:
        """
        Get detailed explanation of why a job was ranked as it was.
        
        Uses AI-based scoring with two pipelines:
        - Pipeline A: Query-only (when no resume/candidate_profile)
        - Pipeline B: Resume + Query (when candidate_profile is provided)
        
        Weights remain rule-based, but scores are calculated by AI.
        """
        try:
            weights = self.weights
            
            # Factor name mappings for human-readable display
            factor_names = {
                "skill_match": "Skills Match",
                "experience_match": "Experience Level",
                "location_preference": "Location",
                "salary_expectation": "Salary",
                "semantic_similarity": "Job Description Fit",
                "company_preference": "Company & Benefits"
            }
            
            # Determine scoring method and calculate scores
            if self.ai_scoring_service.is_available():
                # Use AI-based scoring
                logger.info(f"Using AI scoring for job {job.id}")
                ai_scores = self.ai_scoring_service.calculate_match_scores(
                    job=job,
                    query=user_description,
                    candidate_profile=candidate_profile
                )
                
                # Build explanations from AI scores
                explanations = {}
                for factor in weights.keys():
                    ai_result = ai_scores.get(factor, {"score": 0.5, "explanation": "Not evaluated"})
                    score = ai_result["score"]
                    explanation = ai_result["explanation"]
                    
                    explanations[factor] = {
                        "name": factor_names.get(factor, factor.replace("_", " ").title()),
                        "score": score,
                        "weight": weights[factor],
                        "contribution": score * weights[factor],
                        "explanation": explanation
                    }
                
                # Calculate weighted final score
                final_score = sum(
                    explanations[factor]["score"] * weights[factor] 
                    for factor in weights
                )
                
                scoring_method = "AI-powered analysis"
                if candidate_profile:
                    scoring_method += " (Resume + Query pipeline)"
                else:
                    scoring_method += " (Query-only pipeline)"
                    
            else:
                # Fallback to rule-based scoring
                logger.info(f"AI scoring not available, using rule-based scoring for job {job.id}")
                scores = {
                    "skill_match": self._calculate_skill_match_score(job, candidate_profile),
                    "experience_match": self._calculate_experience_match_score(job, candidate_profile),
                    "location_preference": self._calculate_location_preference_score(job, candidate_profile),
                    "salary_expectation": self._calculate_salary_expectation_score(job, candidate_profile),
                    "semantic_similarity": self._calculate_semantic_similarity_score(job, user_description),
                    "company_preference": self._calculate_company_preference_score(job, candidate_profile)
                }
                
                # Calculate weighted score
                final_score = sum(scores[factor] * weights[factor] for factor in weights)
                
                # Generate explanations using rule-based method
                explanations = {}
                for factor, score in scores.items():
                    explanations[factor] = {
                        "name": factor_names.get(factor, factor.replace("_", " ").title()),
                        "score": score,
                        "weight": weights[factor],
                        "contribution": score * weights[factor],
                        "explanation": self._get_factor_explanation(factor, score, job, candidate_profile)
                    }
                
                scoring_method = "Rule-based analysis"

            top_features = self._get_top_feature_attributions(job)
            kg_expl = self._get_kg_path_explanation(job)
            
            return {
                "job_id": job.id,
                "job_title": job.title,
                "company": job.company_name,
                "final_score": final_score,
                "factor_scores": explanations,
                "ranking_factors": weights,
                "top_feature_attributions": top_features,
                "knowledge_graph_explanation": kg_expl,
                "scoring_method": scoring_method
            }
            
        except Exception as e:
            logger.error(f"Error generating reranking explanation: {e}")
            return {}
    
    def _get_factor_explanation(self, factor: str, score: float, job: Job, candidate_profile: Optional[CandidateProfile]) -> str:
        """Generate detailed human-readable explanation using full job data"""
        try:
            if factor == "skill_match":
                if candidate_profile and candidate_profile.extracted_skills:
                    job_skills = set(skill.lower() for skill in job.required_skills)
                    candidate_skills = set(skill.lower() for skill in candidate_profile.extracted_skills)
                    matching = job_skills.intersection(candidate_skills)
                    missing = job_skills - candidate_skills
                    
                    if matching:
                        match_list = ", ".join(list(matching)[:5])  # Show top 5
                        explanation = f"Matching skills: {match_list}"
                        if missing:
                            miss_list = ", ".join(list(missing)[:3])
                            explanation += f". Missing: {miss_list}"
                        return explanation
                    elif missing:
                        return f"Job requires: {', '.join(list(missing)[:5])} which are not in your resume"
                
                # Fallback: show what the job requires
                if job.required_skills:
                    return f"Job requires: {', '.join(job.required_skills[:5])}"
                return "No specific skills listed for this job"

            elif factor == "experience_match":
                job_level = job.experience_level.value.capitalize()
                if candidate_profile:
                    candidate_level = self._estimate_candidate_experience_level(candidate_profile)
                    level_names = {1: "Entry", 2: "Mid-level", 3: "Senior", 4: "Executive"}
                    candidate_level_name = level_names.get(candidate_level, "Mid-level")
                    if score >= 0.8:
                        return f"Your {candidate_level_name} experience matches the {job_level} level requirement"
                    else:
                        return f"Job requires {job_level} level; your profile suggests {candidate_level_name} level"
                return f"Job requires {job_level} level experience"

            elif factor == "location_preference":
                job_location = f"{job.location.city}, {job.location.state}"
                remote_note = " (Remote work available)" if job.remote_allowed else ""
                
                if candidate_profile and candidate_profile.candidate.preferred_locations:
                    prefs = ", ".join(candidate_profile.candidate.preferred_locations[:3])
                    if score >= 0.8:
                        return f"Job location ({job_location}{remote_note}) matches your preferences: {prefs}"
                    else:
                        return f"Job is in {job_location}{remote_note}. Your preferences: {prefs}"
                return f"Job location: {job_location}{remote_note}"

            elif factor == "salary_expectation":
                if job.salary and job.salary.min_salary:
                    salary_range = f"${job.salary.min_salary:,}"
                    if job.salary.max_salary:
                        salary_range += f" - ${job.salary.max_salary:,}"
                    salary_range += f" {job.salary.period}"
                    
                    if candidate_profile and candidate_profile.candidate.salary_expectation:
                        expected = f"${candidate_profile.candidate.salary_expectation:,}"
                        if score >= 0.8:
                            return f"Salary range ({salary_range}) aligns with your expectation of {expected}"
                        else:
                            return f"Salary: {salary_range}. Your expectation: {expected}"
                    return f"Salary range: {salary_range}"
                return "No salary information provided for this job"

            elif factor == "semantic_similarity":
                # Include key job details in explanation
                details = []
                if job.responsibilities:
                    details.append(f"Responsibilities include: {', '.join(job.responsibilities[:2])}")
                if job.requirements:
                    details.append(f"Requirements: {', '.join(job.requirements[:2])}")
                
                if score >= 0.7:
                    return f"Job description closely matches your preferences. {' '.join(details)}"
                elif details:
                    return f"Job overview: {' '.join(details)}"
                return f"Role: {job.title} at {job.company_name}"

            elif factor == "company_preference":
                company_info = f"{job.company_name}"
                benefits_note = ""
                if job.benefits:
                    benefit_names = [b.name for b in job.benefits[:3]]
                    benefits_note = f". Benefits: {', '.join(benefit_names)}"
                
                visa_note = " (Visa sponsorship available)" if job.visa_sponsorship else ""
                return f"Company: {company_info}{visa_note}{benefits_note}"

            return "Factor score calculated"
            
        except Exception as e:
            logger.error(f"Error generating factor explanation: {e}")
            return "Unable to generate explanation"

    def _get_top_feature_attributions(self, job: Job, limit: int = 3) -> List[str]:
        vector = job.feature_vector or {}
        if not vector:
            metadata = job.search_metadata or {}
            vector = metadata.get("static_features", {})
        if not vector:
            return []

        sorted_items = sorted(vector.items(), key=lambda kv: abs(kv[1]), reverse=True)
        top = []
        for key, value in sorted_items[:limit]:
            label = self.feature_labels.get(key, key)
            top.append(f"{label}={value:+.2f}")
        return top

    def _get_kg_path_explanation(self, job: Job) -> Optional[str]:
        metadata = job.search_metadata or {}
        query_skills = metadata.get("last_query_skills") or []
        job_skills_lower = [s.lower() for s in (job.required_skills or [])]

        for skill in query_skills:
            if skill.lower() in job_skills_lower:
                return f"Because the job explicitly requires {skill}, which directly matches your query skill."

        feature_vector = job.feature_vector or {}
        path_len = feature_vector.get("kg_skill_shortest_path")
        if path_len and path_len > 0:
            return f"Job is connected to your skills through a knowledge-graph path of length {int(path_len)}, indicating closely related expertise."

        if feature_vector.get("kg_skill_2hop_count", 0) > 0:
            return "Job references skills that are closely connected to your query skills within the knowledge graph."

        return None
    
    def update_reranking_weights(self, new_weights: Dict[str, float]) -> bool:
        """Update reranking weights for customization"""
        try:
            # Validate weights
            total_weight = sum(new_weights.values())
            if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
                logger.warning(f"Reranking weights don't sum to 1.0: {total_weight}")
                return False
            
            self.weights.update(new_weights)
            logger.info(f"Updated reranking weights: {self.weights}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating reranking weights: {e}")
            return False
    
    def get_reranking_statistics(self, search_results: JobSearchResult) -> Dict[str, Any]:
        """Get statistics about reranking performance"""
        try:
            if not search_results.jobs:
                return {}
            
            scores = [getattr(job, 'rerank_score', 0.0) for job in search_results.jobs]
            
            return {
                "total_jobs": len(search_results.jobs),
                "average_score": np.mean(scores),
                "max_score": np.max(scores),
                "min_score": np.min(scores),
                "score_std": np.std(scores),
                "high_quality_matches": len([s for s in scores if s >= 0.8]),
                "medium_quality_matches": len([s for s in scores if 0.5 <= s < 0.8]),
                "low_quality_matches": len([s for s in scores if s < 0.5])
            }
            
        except Exception as e:
            logger.error(f"Error calculating reranking statistics: {e}")
            return {}
