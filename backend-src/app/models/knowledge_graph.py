from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class NodeType(str, Enum):
    JOB = "Job"
    CANDIDATE = "Candidate"
    SKILL = "Skill"
    COMPANY = "Company"
    LOCATION = "Location"
    BENEFIT = "Benefit"
    CONCEPT = "Concept"
    INDUSTRY = "Industry"

class RelationshipType(str, Enum):
    # Job relationships
    REQUIRES_SKILL = "REQUIRES_SKILL"
    OFFERED_BY = "OFFERED_BY"
    LOCATED_IN = "LOCATED_IN"
    OFFERS_BENEFIT = "OFFERS_BENEFIT"
    BELONGS_TO_INDUSTRY = "BELONGS_TO_INDUSTRY"
    
    # Candidate relationships
    HAS_SKILL = "HAS_SKILL"
    WORKED_AT = "WORKED_AT"
    STUDIED_AT = "STUDIED_AT"
    PREFERS_LOCATION = "PREFERS_LOCATION"
    NEEDS_VISA = "NEEDS_VISA"
    
    # Skill relationships
    IS_A = "IS_A"
    RELATED_TO = "RELATED_TO"
    PREREQUISITE_FOR = "PREREQUISITE_FOR"
    USED_WITH = "USED_WITH"
    
    # Location relationships
    PART_OF = "PART_OF"
    NEAR = "NEAR"

class GraphNode(BaseModel):
    id: str
    type: NodeType
    properties: Dict[str, Any]
    labels: List[str] = []

class GraphRelationship(BaseModel):
    id: str
    type: RelationshipType
    source_id: str
    target_id: str
    properties: Dict[str, Any] = {}

class KnowledgeGraphQuery(BaseModel):
    start_nodes: List[str] = []
    relationship_types: List[RelationshipType] = []
    target_node_types: List[NodeType] = []
    max_depth: int = 3
    filters: Dict[str, Any] = {}

class GraphSearchResult(BaseModel):
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    paths: List[List[str]] = []
    relevance_scores: Dict[str, float] = {}

class EntityExtraction(BaseModel):
    entities: List[str]
    entity_types: Dict[str, str]
    relationships: List[tuple]
    confidence_scores: Dict[str, float]

class SemanticEnrichment(BaseModel):
    original_query: str
    extracted_entities: List[str]
    expanded_concepts: List[str]
    related_skills: List[str]
    semantic_vectors: List[float]
    enrichment_score: float
