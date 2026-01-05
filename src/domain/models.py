from enum import Enum
from typing import NewType, List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Value Objects
ProjectId = NewType("ProjectId", str)


# Enums
class DefectCategory(str, Enum):
    DEAD_ENDS = "Dead Ends"
    MISSING_ELSE = "Missing Else"
    ORPHAN_STATES = "Orphan States"
    CONFLICTING_OUTPUTS = "Conflicting Outputs"
    UNSTATED_SIDE_EFFECTS = "Unstated Side Effects"
    TIMING_VIOLATION = "Timing Violation"
    CYCLES = "Cycles"
    AMBIGUOUS_TERMS = "Ambiguous Terms"


class Severity(str, Enum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"


# Entities


class ProjectConfig(BaseModel):
    exclude_patterns: List[str] = Field(default_factory=list)
    description: Optional[str] = None


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


class Defect(BaseModel):
    id: str
    category: DefectCategory
    severity: Severity
    location: str
    description: str
    recommendation: str


class VerificationResult(BaseModel):
    project_id: ProjectId
    timestamp: datetime
    summary: str
    defects: List[Defect]
    raw_report: str  # Markdown report content

    class Config:
        arbitrary_types_allowed = True
