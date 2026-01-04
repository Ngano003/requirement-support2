import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

from google import genai
from openai import OpenAI

from src.domain.interfaces import LLMGateway

load_dotenv()


class LLMGatewayImpl(LLMGateway):
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Default to google if key exists, otherwise openai, unless explicitly set
        default_provider = "google" if self.google_api_key else "openai"
        self.provider = os.getenv("LLM_PROVIDER", default_provider).lower()

        self.model_name = os.getenv("LLM_MODEL")

        if self.provider == "google":
            if not self.model_name:
                self.model_name = "gemini-2.5-flash"
            # genai.configure(api_key=self.google_api_key) # Old SDK
            # self.model = genai.GenerativeModel(self.model_name)
            self.client = genai.Client(api_key=self.google_api_key)
        else:
            if not self.model_name:
                self.model_name = "gpt-4o-mini"
            self.client = OpenAI(api_key=self.openai_api_key)

    def extract_structure(self, text: str) -> Dict[str, Any]:
        prompt = f"""
        Extract requirement nodes and edges from the following text into JSON format.
        Nodes should have id, content, type (action, condition, actor, terminator).
        Edges should have source, target, type (depends_on, contradicts, refines).
        
        Text:
        {text[:5000]} 
        
        Output JSON:
        {{ "nodes": [...], "edges": [...] }}
        """

        return self._call_llm_json(prompt)

    def verify_condition_exhaustiveness(
        self, condition: str, outgoing_paths: List[str]
    ) -> Dict[str, Any]:
        prompt = f"""
        Condition: "{condition}"
        Defined Paths: {outgoing_paths}
        
        Is this exhaustive (MECE)? If not, list missing cases.
        Output JSON:
        {{ "is_exhaustive": boolean, "missing_cases": ["..."] }}
        """
        return self._call_llm_json(prompt)

    def check_text_contradiction(self, text_a: str, text_b: str) -> Dict[str, Any]:
        prompt = f"""
        Text A: "{text_a}"
        Text B: "{text_b}"
        
        Do these contradict?
        Output JSON:
        {{ "has_contradiction": boolean, "reason": "..." }}
        """
        return self._call_llm_json(prompt)

    def _call_llm_json(self, prompt: str) -> Dict[str, Any]:
        # Removed try-except to allow exceptions (e.g. Rate Limit) to propagate
        if self.provider == "google":
            from google.genai import types

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            return json.loads(response.text)
        else:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
