from src.domain.models import ProjectId
from src.application.use_cases import VerifyRequirementsUseCase, ManageProjectUseCase
from src.application.interfaces import AnalysisProgressCallback


class StreamlitController:
    def __init__(
        self,
        manage_project_uc: ManageProjectUseCase,
        verify_requirements_uc: VerifyRequirementsUseCase,
    ):
        self.manage_project_uc = manage_project_uc
        self.verify_requirements_uc = verify_requirements_uc

    def get_all_projects(self):
        return self.manage_project_uc.list_projects()

    def create_project(self, name: str, path: str):
        return self.manage_project_uc.create_project(name, path)

    def add_file(self, project_id: ProjectId, file_path: str):
        return self.manage_project_uc.add_file(project_id, file_path)

    def delete_project(self, project_id: ProjectId):
        return self.manage_project_uc.delete_project(project_id)

    def run_verification(
        self, project_id: ProjectId, callback: AnalysisProgressCallback
    ):
        return self.verify_requirements_uc.execute(project_id, callback)
