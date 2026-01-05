from datetime import datetime
from typing import List, Optional
import uuid
import os

from src.domain.models import (
    Project,
    ProjectId,
    VerificationResult,
    Defect,
    DefectCategory,
    Severity,
    ProjectConfig,
)
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
        if os.path.exists(directory_path):
            for root, _, files in os.walk(directory_path):
                for file in files:
                    if file.lower().endswith((".md", ".txt", ".pdf", ".docx", ".xlsx")):
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

    def delete_project(self, project_id: ProjectId) -> None:
        self.repository.delete(project_id)


class VerifyRequirementsUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        llm_gateway: LLMGateway,
        file_provider: FileContentProvider,
    ):
        self.project_repo = project_repo
        self.llm_gateway = llm_gateway
        self.file_provider = file_provider

    def execute(
        self, project_id: ProjectId, callback: Optional[AnalysisProgressCallback] = None
    ) -> VerificationResult:
        if callback:
            callback.on_progress("Loading Project...", 10)

        project = self.project_repo.find_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        # 1. Load Files & Concatenate
        if callback:
            callback.on_progress("Loading Requirements...", 20)

        full_text = ""
        file_names = []
        for file_path in project.input_files:
            file_name = os.path.basename(file_path)
            file_names.append(file_name)
            if callback:
                callback.on_log(f"Reading {file_name}...")

            try:
                content = self.file_provider.read_text(file_path)
                full_text += f"\n\n# Document: {file_name}\n"
                full_text += content
            except Exception as e:
                msg = f"Error reading {file_name}: {e}"
                if callback:
                    callback.on_log(msg)
                print(msg)

        if not full_text:
            raise ValueError("No content found in project files.")

        # 2. Call LLM Verification
        if callback:
            callback.on_progress("Verifying with LLM...", 50)
            callback.on_log("Sending request to LLM (this may take a minute)...")

        llm_result = self.llm_gateway.verify_requirements(full_text)

        # 3. Process Result
        if callback:
            callback.on_progress("Processing Results...", 80)

        summary = llm_result.get("summary", "No summary provided.")
        defects_data = llm_result.get("defects", [])

        defects = []
        for d in defects_data:
            defects.append(
                Defect(
                    id=d.get("id", "N/A"),
                    category=d.get(
                        "category", DefectCategory.AMBIGUOUS_TERMS
                    ),  # Default fallback? or strict?
                    severity=d.get("severity", Severity.MINOR),
                    location=d.get("location", "Unknown"),
                    description=d.get("description", ""),
                    recommendation=d.get("recommendation", ""),
                )
            )

        # 4. Generate Markdown Report
        report_md = self._generate_report_markdown(summary, defects, file_names)

        # 5. Save
        result = VerificationResult(
            project_id=project.id,
            timestamp=datetime.now(),
            summary=summary,
            defects=defects,
            raw_report=report_md,
        )

        self.project_repo.save_result(project.id, result)

        if callback:
            callback.on_progress("Done", 100)

        return result

    def _generate_report_markdown(
        self, summary: str, defects: List[Defect], file_names: List[str]
    ) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"# LLM Verification Report\n\n"
        report += f"**Timestamp**: {now}\n"
        report += f"**Files**: {', '.join(file_names)}\n\n"

        report += "## Executive Summary\n"
        report += f"{summary}\n\n"

        if not defects:
            report += "> [!NOTE]\n> No significant defects found.\n\n"
            return report

        # Count severity
        critical = sum(1 for d in defects if d.severity == Severity.CRITICAL)
        major = sum(1 for d in defects if d.severity == Severity.MAJOR)
        minor = sum(1 for d in defects if d.severity == Severity.MINOR)

        report += f"| Critical | Major | Minor | Total |\n"
        report += f"| :---: | :---: | :---: | :---: |\n"
        report += f"| {critical} | {major} | {minor} | {len(defects)} |\n\n"

        report += "## Defect List\n\n"

        for d in defects:
            icon = (
                "🔴"
                if d.severity == Severity.CRITICAL
                else ("🟠" if d.severity == Severity.MAJOR else "🔵")
            )
            report += f"### {icon} [{d.id}] {d.category}\n\n"
            report += f"**Severity**: {d.severity}\n"
            report += f"**Location**: {d.location}\n\n"
            report += f"**Description**:\n{d.description}\n\n"
            report += f"**Recommendation**:\n{d.recommendation}\n\n"
            report += "---\n\n"

        return report
