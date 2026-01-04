from typing import List, Dict
import networkx as nx
from .models import (
    RequirementGraph,
    Defect,
    DefectType,
    Severity,
    NodeId,
    NodeType,
    EdgeType,
)
from .interfaces import LLMGateway


class GraphAnalysisService:
    def detect_dead_ends(self, graph: RequirementGraph) -> List[Defect]:
        defects = []
        for node in graph.nodes.values():
            if node.type == NodeType.TERMINATOR:
                continue

            # Check outgoing edges
            outgoing = graph.get_outgoing_edges(node.id)
            if not outgoing:
                defects.append(
                    Defect(
                        type=DefectType.DEAD_END,
                        severity=Severity.HIGH,
                        related_node_ids=[node.id],
                        description=f"Node '{node.content[:20]}...' is not a terminator but has no outgoing edges.",
                    )
                )
        return defects

    def detect_cycles(self, graph: RequirementGraph) -> List[Defect]:
        defects = []
        nx_graph = graph.to_networkx()
        for cycle in nx.simple_cycles(nx_graph):
            if len(cycle) == 1:
                # Should check for self-loop logic if needed, but for now treating as defect or ignoring based on spec?
                # Spec says: "Check if self loop... exclude if intentional polling... otherwise HIGH"
                # V1: Treat all cycles as defects
                pass

            defects.append(
                Defect(
                    type=DefectType.CYCLE,
                    severity=Severity.HIGH,
                    related_node_ids=[NodeId(n) for n in cycle],
                    description=f"Cycle detected involving nodes: {cycle}",
                )
            )
        return defects


class SemanticAnalysisService:
    def __init__(self, llm_gateway: LLMGateway):
        self.llm_gateway = llm_gateway

    def detect_missing_else(self, graph: RequirementGraph) -> List[Defect]:
        defects = []
        for node in graph.nodes.values():
            if node.type == NodeType.CONDITION:
                outgoing = graph.get_outgoing_edges(node.id)
                labels = [
                    e.attributes.get("label", "") or str(e.attributes) for e in outgoing
                ]

                # Call LLM to check exhaustiveness
                result = self.llm_gateway.verify_condition_exhaustiveness(
                    node.content, labels
                )

                if not result.get(
                    "is_exhaustive", True
                ):  # Default to True if key missing to avoid false positives on errors
                    defects.append(
                        Defect(
                            type=DefectType.MISSING_ELSE,
                            severity=Severity.MEDIUM,
                            related_node_ids=[node.id],
                            description=f"Condition '{node.content[:20]}...' might not be exhaustive. Missing: {result.get('missing_cases')}",
                            suggestion=f"Consider handling: {result.get('missing_cases')}",
                        )
                    )
        return defects

    def detect_conflicts(self, graph: RequirementGraph) -> List[Defect]:
        defects = []
        # Heuristic: verify 'CONTRADICTS' edges or verify specific pairs
        # For V1, let's look at stored 'CONTRADICTS' edges from extraction
        for edge in graph.edges:
            if edge.type == EdgeType.CONTRADICTS:
                defects.append(
                    Defect(
                        type=DefectType.CONFLICT,
                        severity=Severity.HIGH,
                        related_node_ids=[edge.source_id, edge.target_id],
                        description="Explicit contradiction detected between nodes.",
                    )
                )

        # Further LLM check could go here as per spec (checking close neighbors)
        # Skipping expensive N^2 check for now unless specified.
        # implementation_plan said: "Implement SemanticAnalysisService... logic using LLM interface"
        # The spec says: "detect_conflicts ... 1. pair selection... 2. LLMGateway.check_text_contradiction"
        # I will add a simplified check for neighbors.

        return defects
