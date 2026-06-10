"""
AI-based Job Matching Scoring Service using Anthropic Claude API

This service provides intelligent job matching by analyzing:
- Query-only matching (when no resume is provided)
- Resume + Query matching (when both are provided)

The AI evaluates multiple factors and provides scores with explanations.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from anthropic import Anthropic
from dotenv import load_dotenv

from ..models.job import Job
from ..models.candidate import CandidateProfile

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class AIScoringService:
    """Service for AI-based job matching using Claude API"""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        # Using Claude Sonnet 3.7
        self.model = "claude-3-7-sonnet-20250219"
        
        if self.api_key and self.api_key != "your-anthropic-api-key-here":
            try:
                self.client = Anthropic(api_key=self.api_key)
                logger.info("Anthropic client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self.client = None
        else:
            logger.warning("ANTHROPIC_API_KEY not configured - AI scoring disabled")
    
    def is_available(self) -> bool:
        """Check if AI scoring is available"""
        return self.client is not None
    
    def calculate_match_scores(
        self,
        job: Job,
        query: Optional[str] = None,
        candidate_profile: Optional[CandidateProfile] = None
    ) -> Dict[str, Any]:
        """
        Calculate AI-based match scores for a job.
        
        Two pipelines:
        1. Query-only: When only search query is provided
        2. Resume + Query: When both resume and query are provided
        
        Returns dict with scores (0-1) and explanations for each factor.
        """
        if not self.is_available():
            logger.warning("AI scoring not available, returning default scores")
            return self._get_default_scores()
        
        try:
            # Determine which pipeline to use
            if candidate_profile:
                # Pipeline B: Resume + Query matching
                return self._score_with_resume_and_query(job, query, candidate_profile)
            elif query:
                # Pipeline A: Query-only matching
                return self._score_with_query_only(job, query)
            else:
                # No context provided
                return self._get_default_scores()
                
        except Exception as e:
            logger.error(f"Error calculating AI match scores: {e}")
            return self._get_default_scores()
    
    def _score_with_query_only(self, job: Job, query: str) -> Dict[str, Any]:
        """
        Pipeline A: Score job match based on query only.
        Used when user searches without uploading a resume.
        """
        prompt = self._build_query_only_prompt(job, query)
        return self._call_claude_for_scores(prompt)
    
    def _score_with_resume_and_query(
        self, 
        job: Job, 
        query: Optional[str],
        candidate_profile: CandidateProfile
    ) -> Dict[str, Any]:
        """
        Pipeline B: Score job match based on both resume and query.
        Provides personalized matching based on candidate's actual qualifications.
        """
        prompt = self._build_resume_and_query_prompt(job, query, candidate_profile)
        return self._call_claude_for_scores(prompt)
    
    def _build_query_only_prompt(self, job: Job, query: str) -> str:
        """Build prompt for query-only matching"""
        
        job_info = self._format_job_info(job)
        
        return f"""You are an expert job matching AI assistant. Your task is to evaluate how well a job posting matches a user's search query.

## User's Search Query
"{query}"

## Job Posting Details
{job_info}

## Your Task
Analyze the match between the user's query and this job posting. Score each factor from 0.0 to 1.0 where:
- 1.0 = Perfect match
- 0.7-0.9 = Strong match
- 0.4-0.6 = Moderate match  
- 0.1-0.3 = Weak match
- 0.0 = No match

Evaluate these factors:

1. **skill_match**: How well do the job's required skills align with what the user is looking for based on their query? Consider skill synonyms (e.g., "JS" = "JavaScript", "ML" = "Machine Learning").

2. **experience_match**: Does the job's experience level (entry/mid/senior/executive) match what the user seems to be looking for? Infer from query context.

3. **location_preference**: Does the job location match what the user wants? Consider remote work preferences if mentioned. If location not specified in query, give 0.5.

4. **salary_expectation**: If salary expectations are mentioned in the query, how well does the job's salary range match? If not mentioned, give 0.5.

5. **semantic_similarity**: Overall semantic alignment - how well does the job title, description, and responsibilities match the intent of the user's query?

6. **company_preference**: Based on the query, does the company type/size/industry seem like a good fit? If no preference indicated, give 0.5.

## Response Format
Respond ONLY with a valid JSON object in this exact format (no markdown, no explanation outside JSON):
{{
    "skill_match": {{
        "score": <float 0-1>,
        "explanation": "<specific explanation referencing actual skills>"
    }},
    "experience_match": {{
        "score": <float 0-1>,
        "explanation": "<specific explanation>"
    }},
    "location_preference": {{
        "score": <float 0-1>,
        "explanation": "<specific explanation referencing locations>"
    }},
    "salary_expectation": {{
        "score": <float 0-1>,
        "explanation": "<specific explanation with salary figures if available>"
    }},
    "semantic_similarity": {{
        "score": <float 0-1>,
        "explanation": "<explanation of overall job-query alignment>"
    }},
    "company_preference": {{
        "score": <float 0-1>,
        "explanation": "<explanation about company fit>"
    }}
}}"""

    def _build_resume_and_query_prompt(
        self, 
        job: Job, 
        query: Optional[str],
        candidate_profile: CandidateProfile
    ) -> str:
        """Build prompt for resume + query matching"""
        
        job_info = self._format_job_info(job)
        candidate_info = self._format_candidate_info(candidate_profile)
        
        query_section = f'## User\'s Search Query\n"{query}"\n\n' if query else ""
        
        return f"""You are an expert job matching AI assistant. Your task is to evaluate how well a job posting matches a candidate's profile and search preferences.

{query_section}## Candidate Profile (from Resume)
{candidate_info}

## Job Posting Details
{job_info}

## Your Task
Analyze the match between this candidate and the job posting. Score each factor from 0.0 to 1.0 where:
- 1.0 = Perfect match
- 0.7-0.9 = Strong match
- 0.4-0.6 = Moderate match
- 0.1-0.3 = Weak match
- 0.0 = No match

Evaluate these factors based on the candidate's ACTUAL qualifications from their resume:

1. **skill_match**: How well do the candidate's skills match the job requirements? Consider:
   - Direct skill matches
   - Related/transferable skills (e.g., React experience for a Vue.js role)
   - Skill synonyms (e.g., "JavaScript" = "JS", "PostgreSQL" = "Postgres")
   - Missing critical skills

2. **experience_match**: How well does the candidate's experience level match? Consider:
   - Years of experience
   - Seniority of past roles (titles like "Senior", "Lead", "Manager")
   - Relevance of past experience to this role

3. **location_preference**: Does the job location work for the candidate? Consider:
   - Candidate's current/preferred locations
   - Remote work availability
   - Relocation potential

4. **salary_expectation**: If candidate has salary expectations, how well does the job's compensation match?

5. **semantic_similarity**: Overall fit - how well does the candidate's background, career trajectory, and the search query align with this job's requirements and responsibilities?

6. **company_preference**: Based on the candidate's work history and any preferences, is this company/industry a good fit?

## Response Format
Respond ONLY with a valid JSON object in this exact format (no markdown, no explanation outside JSON):
{{
    "skill_match": {{
        "score": <float 0-1>,
        "explanation": "<specific explanation mentioning candidate's skills vs job requirements>"
    }},
    "experience_match": {{
        "score": <float 0-1>,
        "explanation": "<specific explanation about experience alignment>"
    }},
    "location_preference": {{
        "score": <float 0-1>,
        "explanation": "<specific explanation about location compatibility>"
    }},
    "salary_expectation": {{
        "score": <float 0-1>,
        "explanation": "<specific explanation with salary figures if available>"
    }},
    "semantic_similarity": {{
        "score": <float 0-1>,
        "explanation": "<explanation of overall candidate-job alignment>"
    }},
    "company_preference": {{
        "score": <float 0-1>,
        "explanation": "<explanation about company/industry fit>"
    }}
}}"""

    def _format_job_info(self, job: Job) -> str:
        """Format job information for the prompt"""
        
        # Format salary
        salary_info = "Not specified"
        if job.salary:
            if job.salary.min_salary and job.salary.max_salary:
                salary_info = f"${job.salary.min_salary:,} - ${job.salary.max_salary:,} {job.salary.period}"
            elif job.salary.min_salary:
                salary_info = f"${job.salary.min_salary:,}+ {job.salary.period}"
        
        # Format location
        location_info = f"{job.location.city}, {job.location.state}, {job.location.country}"
        if job.remote_allowed:
            location_info += " (Remote available)"
        
        # Format benefits
        benefits = ", ".join([b.name for b in job.benefits[:5]]) if job.benefits else "Not specified"
        
        return f"""**Title:** {job.title}
**Company:** {job.company_name}
**Location:** {location_info}
**Job Type:** {job.job_type.value if job.job_type else 'Not specified'}
**Experience Level:** {job.experience_level.value if job.experience_level else 'Not specified'}
**Salary:** {salary_info}
**Remote Work:** {'Yes' if job.remote_allowed else 'No'}
**Visa Sponsorship:** {'Yes' if job.visa_sponsorship else 'No'}

**Required Skills:** {', '.join(job.required_skills) if job.required_skills else 'Not specified'}
**Preferred Skills:** {', '.join(job.preferred_skills) if job.preferred_skills else 'Not specified'}

**Responsibilities:**
{chr(10).join(['- ' + r for r in job.responsibilities[:5]]) if job.responsibilities else 'Not specified'}

**Requirements:**
{chr(10).join(['- ' + r for r in job.requirements[:5]]) if job.requirements else 'Not specified'}

**Benefits:** {benefits}

**Description:**
{job.description[:1000]}{'...' if len(job.description) > 1000 else ''}"""

    def _format_candidate_info(self, candidate_profile: CandidateProfile) -> str:
        """Format candidate profile information for the prompt"""
        
        candidate = candidate_profile.candidate
        
        # Format skills from extracted_skills
        skills = candidate_profile.extracted_skills or []
        skills_str = ", ".join(skills[:20]) if skills else "Not extracted"
        
        # Format experience from extracted_experience
        experience_list = candidate_profile.extracted_experience or []
        experience_str = "\n".join([f"- {exp}" for exp in experience_list[:5]]) if experience_list else "Not extracted"
        
        # Format education from candidate.education (list of Education objects)
        education_str = "Not specified"
        if candidate.education:
            edu_items = []
            for edu in candidate.education[:3]:
                edu_items.append(f"- {edu.degree} in {edu.field_of_study} from {edu.institution}")
            education_str = "\n".join(edu_items) if edu_items else "Not specified"
        elif candidate_profile.degree_level:
            education_str = f"- {candidate_profile.degree_level.value}"
        
        # Format preferred locations
        locations = candidate.preferred_locations if candidate.preferred_locations else []
        locations_str = ", ".join(locations) if locations else "Not specified"
        
        # Salary expectation
        salary_exp = f"${candidate.salary_expectation:,}" if candidate.salary_expectation else "Not specified"
        
        # Calculate years of experience from experience list
        years_exp = len(candidate.experience) if candidate.experience else "Not specified"
        if isinstance(years_exp, int):
            years_exp = f"~{years_exp} positions"
        
        # Experience summary if available
        exp_summary = candidate_profile.experience_summary or ""
        
        return f"""**Name:** {candidate.name or 'Not provided'}
**Email:** {candidate.email or 'Not provided'}

**Skills:** {skills_str}

**Experience:**
{experience_str}
{f'Summary: {exp_summary}' if exp_summary else ''}

**Education:**
{education_str}

**Certifications:** {', '.join(candidate_profile.certifications) if candidate_profile.certifications else 'None'}
**Preferred Locations:** {locations_str}
**Salary Expectation:** {salary_exp}
**Experience Level:** {years_exp}"""

    def _call_claude_for_scores(self, prompt: str) -> Dict[str, Any]:
        """Call Claude API and parse the response"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract the text response
            response_text = response.content[0].text.strip()
            
            # Parse JSON response
            # Handle potential markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            scores = json.loads(response_text)
            
            # Validate and normalize scores
            return self._validate_scores(scores)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            return self._get_default_scores()
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return self._get_default_scores()
    
    def _validate_scores(self, scores: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize AI-generated scores"""
        required_factors = [
            "skill_match", "experience_match", "location_preference",
            "salary_expectation", "semantic_similarity", "company_preference"
        ]
        
        validated = {}
        for factor in required_factors:
            if factor in scores and isinstance(scores[factor], dict):
                score = scores[factor].get("score", 0.5)
                explanation = scores[factor].get("explanation", "AI analysis not available")
                
                # Ensure score is in valid range
                score = max(0.0, min(1.0, float(score)))
                
                validated[factor] = {
                    "score": score,
                    "explanation": explanation
                }
            else:
                validated[factor] = {
                    "score": 0.5,
                    "explanation": "Factor not evaluated by AI"
                }
        
        return validated
    
    def _get_default_scores(self) -> Dict[str, Any]:
        """Return default scores when AI is not available"""
        return {
            "skill_match": {
                "score": 0.5,
                "explanation": "AI scoring not available - using neutral score"
            },
            "experience_match": {
                "score": 0.5,
                "explanation": "AI scoring not available - using neutral score"
            },
            "location_preference": {
                "score": 0.5,
                "explanation": "AI scoring not available - using neutral score"
            },
            "salary_expectation": {
                "score": 0.5,
                "explanation": "AI scoring not available - using neutral score"
            },
            "semantic_similarity": {
                "score": 0.5,
                "explanation": "AI scoring not available - using neutral score"
            },
            "company_preference": {
                "score": 0.5,
                "explanation": "AI scoring not available - using neutral score"
            }
        }


# Singleton instance
ai_scoring_service = AIScoringService()

