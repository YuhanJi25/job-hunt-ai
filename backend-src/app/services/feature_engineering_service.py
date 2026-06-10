import logging
from typing import Dict, List, Optional

from ..models.job import Job
from .nlp_service import NLPService
from .knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)


class FeatureEngineeringService:
    """Aggregate lexical, semantic, and knowledge-graph signals for attribution."""

    def __init__(self):
        self.nlp_service = NLPService()
        self.kg_service = KnowledgeGraphService()

    def build_features_for_jobs(
        self,
        query_text: str,
        jobs: List[Job],
        query_skills: Optional[List[str]] = None,
        query_locations: Optional[List[str]] = None,
    ) -> None:
        if not jobs:
            return

        skills = query_skills or self._extract_query_skills(query_text)
        locations = query_locations or self._extract_query_locations(query_text)

        for job in jobs:
            job.feature_vector = self.build_feature_vector(
                query_text=query_text,
                job=job,
                query_skills=skills,
                query_locations=locations,
            )
            job.search_metadata = job.search_metadata or {}
            job.search_metadata["last_query_skills"] = list(skills)
            job.search_metadata["last_query_text"] = query_text

    def build_feature_vector(
        self,
        query_text: str,
        job: Job,
        query_skills: Optional[List[str]] = None,
        query_locations: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        features: Dict[str, float] = {}
        query_skills = query_skills or self._extract_query_skills(query_text)
        query_locations = query_locations or self._extract_query_locations(query_text)

        features.update(self._lexical_features(query_text, job, query_skills))
        features.update(self._semantic_features(query_text, job))
        features.update(self._kg_features(query_text, job, query_skills, query_locations))
        job.search_metadata = job.search_metadata or {}
        job.search_metadata["last_query_skills"] = list(query_skills)
        job.search_metadata["last_query_text"] = query_text
        return features

    # ---------------- Lexical ---------------- #
    def _lexical_features(
        self, query_text: str, job: Job, query_skills: List[str]
    ) -> Dict[str, float]:
        features: Dict[str, float] = {}
        metadata = job.search_metadata or {}

        features["lexical_es_score"] = float(metadata.get("es_score") or 0.0)

        lower_query = (query_text or "").lower()
        features["lexical_title_exact"] = 1.0 if lower_query in (job.title or "").lower() else 0.0

        job_skills = [skill.lower() for skill in (job.required_skills or [])]
        overlap = set(job_skills).intersection(set(skill.lower() for skill in query_skills))
        if query_skills:
            features["lexical_skill_overlap_ratio"] = len(overlap) / max(1, len(set(query_skills)))
        else:
            features["lexical_skill_overlap_ratio"] = 0.0

        features["lexical_filter_location_match"] = 1.0 if self._location_in_query(job, lower_query) else 0.0
        return features

    # ---------------- Semantic ---------------- #
    def _semantic_features(self, query_text: str, job: Job) -> Dict[str, float]:
        features: Dict[str, float] = {}

        title = job.title or ""
        description = job.description or ""
        skill_text = " ".join(job.required_skills or [])

        features["semantic_title"] = self.nlp_service.calculate_semantic_similarity(query_text, title)
        features["semantic_description"] = self.nlp_service.calculate_semantic_similarity(query_text, description)
        features["semantic_skills"] = self.nlp_service.calculate_semantic_similarity(query_text, skill_text)

        return features

    # ---------------- Knowledge Graph ---------------- #
    def _kg_features(
        self,
        query_text: str,
        job: Job,
        query_skills: List[str],
        query_locations: List[str],
    ) -> Dict[str, float]:
        features: Dict[str, float] = {}
        normalized_skills = [skill.lower() for skill in query_skills if skill]

        try:
            features["kg_skill_1hop_count"] = float(
                self.kg_service.count_job_skill_matches(job.id, normalized_skills, hops=1)
            )
            features["kg_skill_2hop_count"] = float(
                self.kg_service.count_job_skill_matches(job.id, normalized_skills, hops=2)
            )
            denom = float(max(1, len(set(normalized_skills))))
            features["kg_skill_related_ratio"] = features["kg_skill_2hop_count"] / denom
        except Exception as exc:
            logger.warning(f"KG skill count failed for job {job.id}: {exc}")
            features.setdefault("kg_skill_1hop_count", 0.0)
            features.setdefault("kg_skill_2hop_count", 0.0)
            features.setdefault("kg_skill_related_ratio", 0.0)

        features["kg_skill_shortest_path"] = self._compute_min_skill_path(job.id, normalized_skills)
        features["kg_location_shortest_path"] = self._compute_min_location_path(job.id, query_locations)

        # Simple proxy for company-focused signal: query mentions the company
        lower_query = (query_text or "").lower()
        company = (job.company_name or "").lower()
        features["kg_company_overlap_proxy"] = 1.0 if company and company in lower_query else 0.0
        return features

    def _compute_min_skill_path(self, job_id: str, skills: List[str]) -> float:
        if not skills:
            return 0.0
        lengths: List[int] = []
        for skill in skills:
            length = self.kg_service.shortest_path_to_skill(job_id, skill)
            if length is not None:
                lengths.append(length)
        return float(min(lengths)) if lengths else 0.0

    def _compute_min_location_path(self, job_id: str, locations: List[str]) -> float:
        if not locations:
            return 0.0
        lengths: List[int] = []
        for loc in locations:
            length = self.kg_service.shortest_path_to_location(job_id, loc)
            if length is not None:
                lengths.append(length)
        return float(min(lengths)) if lengths else 0.0

    # ---------------- Helpers ---------------- #
    def _extract_query_skills(self, query_text: str) -> List[str]:
        try:
            return self.nlp_service.extract_skills_from_text(query_text) or []
        except Exception:
            return []

    def _extract_query_locations(self, query_text: str) -> List[str]:
        try:
            entities = self.nlp_service.extract_entities_from_text(query_text)
            return entities.get("GPE", []) if entities else []
        except Exception:
            return []

    def _location_in_query(self, job: Job, lower_query: str) -> bool:
        location_tokens = filter(
            None,
            [
                getattr(job.location, "city", "") if job.location else "",
                getattr(job.location, "state", "") if job.location else "",
            ],
        )
        return any(token and token.lower() in lower_query for token in location_tokens)
