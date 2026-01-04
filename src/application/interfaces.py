from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models import Project, ProjectId, AnalysisResult


class ProjectRepository(ABC):
    @abstractmethod
    def save(self, project: Project) -> None:
        pass

    @abstractmethod
    def find_by_id(self, id: ProjectId) -> Optional[Project]:
        pass

    @abstractmethod
    def save_result(self, project_id: ProjectId, result: AnalysisResult) -> None:
        pass

    @abstractmethod
    def list_projects(self) -> List[Project]:
        pass

    @abstractmethod
    def delete(self, project_id: ProjectId) -> None:
        pass


class AnalysisProgressCallback(ABC):
    @abstractmethod
    def on_progress(self, step: str, percentage: int) -> None:
        pass

    @abstractmethod
    def on_log(self, message: str) -> None:
        pass


class FileContentProvider(ABC):
    @abstractmethod
    def read_text(self, file_path: str) -> str:
        pass
