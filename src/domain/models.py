from enum import Enum
from typing import NewType, List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Value Objects
ProjectId = NewType('ProjectId', str)
NodeId = NewType('NodeId', str)

# Enums
class NodeType(str, Enum):
    ACTOR = "actor"
    ACTION = "action"
    CONDITION = "condition"
    TERMINATOR = "terminator"

class EdgeType(str, Enum):
    DEPENDS_ON = "depends_on"
    CONTRADICTS = "contradicts"
    REFINES = "refines"

class DefectType(str, Enum):
    DEAD_END = "DeadEnd"
    CYCLE = "Cycle"
    MISSING_ELSE = "MissingElse"
    CONFLICT = "Conflict"

class Severity(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

# Entities

class ProjectConfig(BaseModel):
    exclude_patterns: List[str] = Field(default_factory=list)

class Project(BaseModel):
    id: ProjectId
    name: str
    created_at: datetime
    config: ProjectConfig
    input_files: List[str] = Field(default_factory=list)

    def add_file(self, path: str) -> None:
        if path not in self.input_files:
            self.input_files.append(path)

    def remove_file(self, path: str) -> None:
        if path in self.input_files:
            self.input_files.remove(path)

    def update_config(self, config: ProjectConfig) -> None:
        self.config = config

class RequirementNode(BaseModel):
    id: NodeId
    content: str
    type: NodeType
    source_file: str
    line_number: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RequirementEdge(BaseModel):
    source_id: NodeId
    target_id: NodeId
    type: EdgeType
    attributes: Dict[str, Any] = Field(default_factory=dict)

class RequirementGraph:
    def __init__(self):
        self.nodes: Dict[NodeId, RequirementNode] = {}
        self.edges: List[RequirementEdge] = []

    def add_node(self, node: RequirementNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: RequirementEdge) -> None:
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_id} does not exist")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_id} does not exist")
        self.edges.append(edge)

    def get_outgoing_edges(self, node_id: NodeId) -> List[RequirementEdge]:
        return [e for e in self.edges if e.source_id == node_id]

    def get_incoming_edges(self, node_id: NodeId) -> List[RequirementEdge]:
        return [e for e in self.edges if e.target_id == node_id]

    def get_orphans(self) -> List[RequirementNode]:
        source_ids = {e.source_id for e in self.edges}
        target_ids = {e.target_id for e in self.edges}
        connected_ids = source_ids.union(target_ids)
        return [n for n in self.nodes.values() if n.id not in connected_ids]
    
    def to_networkx(self):
        import networkx as nx
        G = nx.DiGraph()
        for node in self.nodes.values():
            G.add_node(node.id, **node.model_dump())
        for edge in self.edges:
            G.add_edge(edge.source_id, edge.target_id, **edge.model_dump())
        return G

class Defect(BaseModel):
    type: DefectType
    severity: Severity
    related_node_ids: List[NodeId]
    description: str
    suggestion: Optional[str] = None

class AnalysisResult(BaseModel):
    project_id: ProjectId
    timestamp: datetime
    graph: RequirementGraph
    defects: List[Defect]
    metrics: Dict[str, float]

    class Config:
        arbitrary_types_allowed = True

    def has_critical_defects(self) -> bool:
        return any(d.severity == Severity.HIGH for d in self.defects)
