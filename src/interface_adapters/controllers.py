from typing import Dict
from src.domain.models import ProjectId
from src.application.use_cases import AnalyzeRequirementsUseCase, ManageProjectUseCase
from src.application.interfaces import AnalysisProgressCallback


class StreamlitController:
    def __init__(
        self,
        manage_project_uc: ManageProjectUseCase,
        analyze_requirements_uc: AnalyzeRequirementsUseCase,
    ):
        self.manage_project_uc = manage_project_uc
        self.analyze_requirements_uc = analyze_requirements_uc

    def get_all_projects(self):
        return self.manage_project_uc.list_projects()

    def create_project(self, name: str, path: str):
        return self.manage_project_uc.create_project(name, path)

    def add_file(self, project_id: ProjectId, file_path: str):
        return self.manage_project_uc.add_file(project_id, file_path)

    def delete_project(self, project_id: ProjectId):
        return self.manage_project_uc.delete_project(project_id)

    def run_analysis(self, project_id: ProjectId, callback: AnalysisProgressCallback):
        return self.analyze_requirements_uc.execute(project_id, callback)
