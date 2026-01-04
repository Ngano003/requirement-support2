import pytest
from src.domain.models import (
    RequirementGraph,
    RequirementNode,
    RequirementEdge,
    NodeType,
    EdgeType,
    NodeId,
    DefectType,
)
from src.domain.services import GraphAnalysisService


def test_detect_dead_ends():
    graph = RequirementGraph()
    # Node 1 -> Node 2 (Dead End)
    n1 = RequirementNode(
        id=NodeId("1"),
        content="Start",
        type=NodeType.ACTION,
        source_file="doc.md",
        line_number=1,
    )
    n2 = RequirementNode(
        id=NodeId("2"),
        content="Process",
        type=NodeType.ACTION,
        source_file="doc.md",
        line_number=2,
    )
    graph.nodes = {n1.id: n1, n2.id: n2}
    graph.edges.append(
        RequirementEdge(source_id=n1.id, target_id=n2.id, type=EdgeType.DEPENDS_ON)
    )

    service = GraphAnalysisService()
    defects = service.detect_dead_ends(graph)

    assert len(defects) == 1
    assert defects[0].type == DefectType.DEAD_END
    assert defects[0].related_node_ids == ["2"]


def test_detect_cycles():
    graph = RequirementGraph()
    # Node 1 -> Node 2 -> Node 1
    n1 = RequirementNode(
        id=NodeId("1"),
        content="A",
        type=NodeType.ACTION,
        source_file="doc.md",
        line_number=1,
    )
    n2 = RequirementNode(
        id=NodeId("2"),
        content="B",
        type=NodeType.ACTION,
        source_file="doc.md",
        line_number=2,
    )
    graph.nodes = {n1.id: n1, n2.id: n2}
    graph.edges.append(
        RequirementEdge(source_id=n1.id, target_id=n2.id, type=EdgeType.DEPENDS_ON)
    )
    graph.edges.append(
        RequirementEdge(source_id=n2.id, target_id=n1.id, type=EdgeType.DEPENDS_ON)
    )

    service = GraphAnalysisService()
    defects = service.detect_cycles(graph)

    assert len(defects) >= 1
    assert defects[0].type == DefectType.CYCLE
    # Check if related nodes contain 1 and 2
    ids = set(defects[0].related_node_ids)
    assert "1" in ids and "2" in ids
