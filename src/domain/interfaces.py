from abc import ABC, abstractmethod
from typing import Dict, Any, List


class LLMGateway(ABC):
    @abstractmethod
    def extract_structure(self, text: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def verify_condition_exhaustiveness(
        self, condition: str, outgoing_paths: List[str]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def check_text_contradiction(self, text_a: str, text_b: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def call_llm_text(self, prompt: str) -> str:
        """
        Generic method to call LLM and get a text response.
        """
        pass
