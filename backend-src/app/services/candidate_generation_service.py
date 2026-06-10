from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging

from ..models.job import Job, JobSearchQuery
from .elasticsearch_service import ElasticsearchService
from .knowledge_graph_service import KnowledgeGraphService
from .semantic_ann_service import SemanticANNService

logger = logging.getLogger(__name__)


@dataclass
class CandidateGenerationResult:
    jobs: List[Job]
    source_breakdown: Dict[str, int] = field(default_factory=dict)
    lexical_total_hits: int = 0


class CandidateGenerationService:
    """Aggregate candidates from lexical, semantic, and KG sources."""

    def __init__(self):
        self.es_service = ElasticsearchService()
        self.kg_service = KnowledgeGraphService()
        self.semantic_service = SemanticANNService()

    def generate_candidates(
        self,
        query: JobSearchQuery,
        lexical_k: int = 150,
        semantic_k: int = 150,
        kg_k: int = 75,
        max_candidates: int = 400,
    ) -> CandidateGenerationResult:
        candidates: Dict[str, Job] = {}
        source_breakdown: Dict[str, int] = {"lexical": 0, "semantic": 0, "graph": 0}

        lexical_jobs, lexical_total = self._lexical_candidates(query, k=lexical_k)
        for job in lexical_jobs:
            self._add_candidate(candidates, job, "lexical")
            source_breakdown["lexical"] += 1

        semantic_jobs = self._semantic_candidates(query.query, k=semantic_k)
        for job in semantic_jobs:
            self._add_candidate(candidates, job, "semantic")
            source_breakdown["semantic"] += 1

        graph_jobs = self._graph_candidates(query.query, k=kg_k)
        for job in graph_jobs:
            self._add_candidate(candidates, job, "graph")
            source_breakdown["graph"] += 1

        # Limit total candidates
        merged = list(candidates.values())[:max_candidates]
        return CandidateGenerationResult(
            jobs=merged,
            source_breakdown=source_breakdown,
            lexical_total_hits=lexical_total,
        )

    def _lexical_candidates(self, query: JobSearchQuery, k: int) -> Tuple[List[Job], int]:
        lexical_query = JobSearchQuery(**query.dict())
        lexical_query.page_size = k
        es_results = self.es_service.search_jobs(lexical_query)
        return es_results.jobs, es_results.total_count

    def _semantic_candidates(self, query_text: str, k: int) -> List[Job]:
        if not self.semantic_service.is_available():
            return []

        hits = self.semantic_service.query(query_text, top_k=k)
        job_ids = [job_id for job_id, _ in hits]
        semantic_jobs = self.es_service.get_jobs_by_ids(job_ids)

        score_map = {job_id: score for job_id, score in hits}
        for job in semantic_jobs:
            job.search_metadata = job.search_metadata or {}
            job.search_metadata["semantic_score"] = score_map.get(job.id)
        return semantic_jobs

    def _graph_candidates(self, query_text: str, k: int) -> List[Job]:
        graph_results = self.kg_service.find_semantic_matches(query_text)
        job_ids: List[str] = []
        for node in graph_results.nodes:
            if node.type.value == "Job":
                job_ids.append(node.id)
            if len(job_ids) >= k:
                break
        if not job_ids:
            return []
        return self.es_service.get_jobs_by_ids(job_ids)

    def _add_candidate(self, candidates: Dict[str, Job], job: Job, source: str) -> None:
        if job.id not in candidates:
            job.search_metadata = job.search_metadata or {}
            job.search_metadata["candidate_sources"] = [source]
            candidates[job.id] = job
        else:
            existing_sources = set(candidates[job.id].search_metadata.get("candidate_sources", []))
            existing_sources.add(source)
            candidates[job.id].search_metadata["candidate_sources"] = sorted(existing_sources)
