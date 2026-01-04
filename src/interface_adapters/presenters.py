import pandas as pd
from typing import Dict, Any, List
from src.domain.models import (
    AnalysisResult,
    RequirementGraph,
    Defect,
    NodeType,
    EdgeType,
)


class ResultPresenter:
    def present_graph(self, graph: RequirementGraph) -> Dict[str, Any]:
        """
        Convert RequirementGraph to streamlit-agraph config or similar.
        Returns dictionary with 'nodes' and 'edges' lists suitable for agraph.
        """
        nodes = []
        edges = []

        # Calculate degrees for importance (simple)
        # In a real impl, we might use PageRank here if requested in design
        # Design says: "present_graph... filtering... PageRank or Degree Centrality"
        # Let's use simple degree centrality for size scaling

        for node in graph.nodes.values():
            # Color mapping
            color = "#999999"
            if node.type == NodeType.ACTOR:
                color = "#5DADE2"
            elif node.type == NodeType.ACTION:
                color = "#58D68D"
            elif node.type == NodeType.CONDITION:
                color = "#F4D03F"
            elif node.type == NodeType.TERMINATOR:
                color = "#EC7063"

            nodes.append(
                {
                    "data": {
                        "id": node.id,
                        "label": node.content[:20] + "...",
                        "type": node.type,
                    },
                    "style": {"background-color": color},
                    # Note: Specific config depends on the library used (cytoscape/agraph).
                    # Assuming agraph Node(id, label, size, color)
                }
            )

        for edge in graph.edges:
            edges.append(
                {
                    "data": {
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "label": edge.type,
                    },
                    "style": {},
                }
            )

        return {"nodes": nodes, "edges": edges}

    def present_defects(self, defects: List[Defect]) -> pd.DataFrame:
        data = []
        for d in defects:
            data.append(
                {
                    "Type": d.type,
                    "Severity": d.severity,
                    "Description": d.description,
                    "Nodes": ", ".join(d.related_node_ids),
                    "Suggestion": d.suggestion or "",
                }
            )
        return pd.DataFrame(data)

    def present_metrics(self, metrics: Dict[str, float]) -> Dict[str, str]:
        return {
            k: f"{v:.0f}" if isinstance(v, int) or v.is_integer() else f"{v:.2f}"
            for k, v in metrics.items()
        }
