from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field

# ========== Breakdown Models ==========


class Question(BaseModel):
    """AI Generated Question"""

    id: str = Field(..., description="Question ID")
    category: Literal["functional", "non_functional", "constraint", "other"] = Field(
        ..., description="Category"
    )
    question: str = Field(..., description="Question Text")
    priority: Literal["high", "medium", "low"] = Field(..., description="Priority")
    context: Optional[str] = Field(None, description="Context")


class SessionData(BaseModel):
    """Session Data"""

    session_id: str
    input_text: str
    requirements: str
    questions: List[Question]
    answered_questions: List[Question]
    answers: Dict[str, str]  # question_id -> answer
    completion_rate: float
