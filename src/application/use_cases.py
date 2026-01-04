from datetime import datetime
from typing import List, Optional
import uuid
import os

from src.domain.models import (
    Project,
    ProjectId,
    AnalysisResult,
    RequirementGraph,
    RequirementNode,
    RequirementEdge,
    Defect,
    ProjectConfig,
    NodeType,
    EdgeType,
)
from src.domain.services import GraphAnalysisService, SemanticAnalysisService
from src.domain.interfaces import LLMGateway
from src.application.interfaces import (
    ProjectRepository,
    AnalysisProgressCallback,
    FileContentProvider,
)


class ManageProjectUseCase:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository

    def create_project(self, name: str, directory_path: str) -> Project:
        project_id = ProjectId(str(uuid.uuid4()))
        project = Project(
            id=project_id,
            name=name,
            created_at=datetime.now(),
            config=ProjectConfig(),
            input_files=[],
        )
        # Scan directory for initial files (simplified)
        if os.path.exists(directory_path):
            for root, _, files in os.walk(directory_path):
                for file in files:
                    if file.endswith((".md", ".txt", ".pdf", ".docx", ".xlsx")):
                        # Store relative path or absolute? Using absolute for simplicity in V1 specific to local fs
                        # But design says "Project-based". Let's stick to absolute for now or path relative to what?
                        # Architecture says "Project-based config".
                        # Let's assume input_files stores absolute paths for now as per `add_file` logic context.
                        full_path = os.path.join(root, file)
                        project.add_file(full_path)

        self.repository.save(project)
        return project

    def list_projects(self) -> List[Project]:
        return self.repository.list_projects()

    def add_file(self, project_id: ProjectId, file_path: str) -> Project:
        project = self.repository.find_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        project.add_file(file_path)
        self.repository.save(project)
        return project


class AnalyzeRequirementsUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        llm_gateway: LLMGateway,
        graph_service: GraphAnalysisService,
        semantic_service: SemanticAnalysisService,
        file_provider: FileContentProvider,
    ):
        self.project_repo = project_repo
        self.llm_gateway = llm_gateway
        self.graph_service = graph_service
        self.semantic_service = semantic_service
        self.file_provider = file_provider

    def execute(
        self, project_id: ProjectId, callback: Optional[AnalysisProgressCallback] = None
    ) -> AnalysisResult:
        if callback:
            callback.on_progress("Loading Project...", 10)
        project = self.project_repo.find_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        # 1. Extraction & Graph Construction
        if callback:
            callback.on_progress("Extracting Structure...", 30)
        graph = RequirementGraph()

        for file_path in project.input_files:
            if callback:
                callback.on_log(f"Processing file: {file_path}")
            try:
                text = self.file_provider.read_text(file_path)

                # Chunking (simplified)
                chunk_size = 2000
                chunks = [
                    text[i : i + chunk_size] for i in range(0, len(text), chunk_size)
                ]

                for chunk in chunks:
                    structure = self.llm_gateway.extract_structure(chunk)
                    # Parse structure to nodes/edges
                    nodes_data = structure.get("nodes", [])
                    edges_data = structure.get("edges", [])

                    for n_data in nodes_data:
                        # Map string type to Enum
                        try:
                            node_type = NodeType(n_data.get("type", "action"))
                        except ValueError:
                            node_type = NodeType.ACTION

                        node = RequirementNode(
                            id=n_data.get("id"),
                            content=n_data.get("content"),
                            type=node_type,
                            source_file=file_path,
                            line_number=0,
                        )
                        graph.nodes[node.id] = node

                    for e_data in edges_data:
                        try:
                            edge_type = EdgeType(e_data.get("type", "depends_on"))
                        except ValueError:
                            edge_type = EdgeType.DEPENDS_ON

                        edge = RequirementEdge(
                            source_id=e_data.get("source"),
                            target_id=e_data.get("target"),
                            type=edge_type,
                            attributes=e_data.get("attributes", {}),
                        )
                        # Only add valid edges
                        if (
                            edge.source_id in graph.nodes
                            and edge.target_id in graph.nodes
                        ):
                            graph.edges.append(edge)

            except Exception as e:
                if callback:
                    callback.on_log(f"Error reading {file_path}: {e}")

        # 2. Structural Analysis
        if callback:
            callback.on_progress("Analyzing Structure...", 60)
        defects = []
        defects.extend(self.graph_service.detect_dead_ends(graph))
        defects.extend(self.graph_service.detect_cycles(graph))

        # 3. Semantic Analysis
        if callback:
            callback.on_progress("Analyzing Semantics...", 80)
        defects.extend(self.semantic_service.detect_missing_else(graph))
        # defects.extend(self.semantic_service.detect_conflicts(graph)) # Optional V1

        # 4. Save Result
        result = AnalysisResult(
            project_id=project.id,
            timestamp=datetime.now(),
            graph=graph,
            defects=defects,
            metrics={"node_count": len(graph.nodes), "edge_count": len(graph.edges)},
        )
        self.project_repo.save_result(project.id, result)

        if callback:
            callback.on_progress("Done", 100)
        return result
