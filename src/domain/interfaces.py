from abc import ABC, abstractmethod
from typing import Dict, Any, List


class LLMGateway(ABC):
    @abstractmethod
    def verify_requirements(self, text: str) -> Dict[str, Any]:
        """
        Verify requirements and return a dictionary compatible with VerificationResult.
        Expected keys: summary, defects (list of dicts)
        """
        pass

    @abstractmethod
    def call_llm_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call LLM with a system prompt and a user prompt.
        """
        pass
