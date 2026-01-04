import os
import yaml
import json
from datetime import datetime
from typing import List, Optional

from src.domain.models import Project, ProjectId, AnalysisResult, ProjectConfig
from src.application.interfaces import ProjectRepository


class FileProjectRepository(ProjectRepository):
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self.projects_dir = os.path.join(self.root_dir, "projects")
        os.makedirs(self.projects_dir, exist_ok=True)

    def _get_project_path(self, project_id: ProjectId) -> str:
        return os.path.join(self.projects_dir, str(project_id))

    def save(self, project: Project) -> None:
        project_path = self._get_project_path(project.id)
        os.makedirs(project_path, exist_ok=True)

        # Save project.yaml
        config_file = os.path.join(project_path, "project.yaml")
        data = project.model_dump(mode="json")
        with open(config_file, "w") as f:
            yaml.dump(data, f)

    def find_by_id(self, id: ProjectId) -> Optional[Project]:
        project_path = self._get_project_path(id)
        config_file = os.path.join(project_path, "project.yaml")

        if not os.path.exists(config_file):
            return None

        with open(config_file, "r") as f:
            data = yaml.safe_load(f)

        if not data or not isinstance(data, dict):
            return None

        # Reconstruct object
        # Need to handle datetime parsing if yaml loaded as str, but Pydantic handles str -> datetime usually
        try:
            return Project(**data)
        except Exception as e:
            print(f"Error loading project {id}: {e}")
            return None

    def save_result(self, project_id: ProjectId, result: AnalysisResult) -> None:
        project_path = self._get_project_path(project_id)
        reports_dir = os.path.join(project_path, "reports")

        # Timestamp based folder
        ts_str = result.timestamp.strftime("%Y%m%d_%H%M%S")
        report_dir = os.path.join(reports_dir, ts_str)
        os.makedirs(report_dir, exist_ok=True)

        result_file = os.path.join(report_dir, "result.json")
        with open(result_file, "w") as f:
            f.write(result.model_dump_json(indent=2))

    def list_projects(self) -> List[Project]:
        projects = []
        if not os.path.exists(self.projects_dir):
            return []

        for pid in os.listdir(self.projects_dir):
            project = self.find_by_id(ProjectId(pid))
            if project:
                projects.append(project)
        return projects

    def delete(self, project_id: ProjectId) -> None:
        import shutil

        project_path = self._get_project_path(project_id)
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
