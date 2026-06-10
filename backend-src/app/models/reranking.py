from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from .job import JobSearchQuery
from .candidate import CandidateProfile

class RerankingRequest(BaseModel):
    """Request model for reranking search results"""
    search_query: JobSearchQuery
    user_description: Optional[str] = Field(None, description="User's specific job description or preferences")
    candidate_profile: Optional[CandidateProfile] = Field(None, description="Candidate's resume/profile information")
    reranking_factors: Optional[Dict[str, float]] = Field(None, description="Custom weights for different reranking factors")
    include_explanations: bool = Field(False, description="Whether to include detailed explanations for rankings")

class RerankingResponse(BaseModel):
    """Response model for reranking results"""
    jobs: List[Any]  # List of Job objects with rerank scores
    total_count: int
    page: int
    page_size: int
    total_pages: int
    search_time_ms: float
    reranking_time_ms: float
    reranking_statistics: Optional[Dict[str, Any]] = None
    explanations: Optional[Dict[str, Any]] = None

class RerankingFactor(BaseModel):
    """Model for individual reranking factor"""
    name: str
    weight: float = Field(ge=0.0, le=1.0, description="Weight of this factor (0.0 to 1.0)")
    score: float = Field(ge=0.0, le=1.0, description="Score for this factor (0.0 to 1.0)")
    contribution: float = Field(ge=0.0, le=1.0, description="Weighted contribution to final score")
    explanation: str = Field(description="Human-readable explanation of this factor")

class RerankingExplanation(BaseModel):
    """Model for detailed reranking explanation"""
    job_id: str
    job_title: str
    company: str
    final_score: float
    factor_scores: Dict[str, RerankingFactor]
    ranking_factors: Dict[str, float]
    top_feature_attributions: Optional[List[str]] = Field(default=None, description="Top feature contributions for the fusion model")
    knowledge_graph_explanation: Optional[str] = Field(default=None, description="Human-readable KG path explanation")
    scoring_method: Optional[str] = Field(default=None, description="Method used for scoring: AI-powered or Rule-based")

class RerankingStatistics(BaseModel):
    """Model for reranking performance statistics"""
    total_jobs: int
    average_score: float
    max_score: float
    min_score: float
    score_std: float
    high_quality_matches: int = Field(description="Jobs with score >= 0.8")
    medium_quality_matches: int = Field(description="Jobs with score 0.5-0.8")
    low_quality_matches: int = Field(description="Jobs with score < 0.5")

class RerankingWeightsUpdate(BaseModel):
    """Model for updating reranking weights"""
    skill_match: Optional[float] = Field(None, ge=0.0, le=1.0)
    experience_match: Optional[float] = Field(None, ge=0.0, le=1.0)
    location_preference: Optional[float] = Field(None, ge=0.0, le=1.0)
    salary_expectation: Optional[float] = Field(None, ge=0.0, le=1.0)
    semantic_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    company_preference: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in self.dict().items() if v is not None}
