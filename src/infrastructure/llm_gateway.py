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
        self.openai_base_url = os.getenv("OPENAI_BASE_URL")

        # Default to google if key exists, otherwise openai, unless explicitly set
        default_provider = "google" if self.google_api_key else "openai"
        self.provider = os.getenv("LLM_PROVIDER", default_provider).lower()

        if self.provider == "google":
            self.model_name = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
            # genai.configure(api_key=self.google_api_key) # Old SDK
            # self.model = genai.GenerativeModel(self.model_name)
            self.client = genai.Client(api_key=self.google_api_key)
        else:
            self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            self.client = OpenAI(
                api_key=self.openai_api_key, base_url=self.openai_base_url
            )

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

    def call_llm_text(self, prompt: str) -> str:
        return self._call_llm_generic(prompt, output_json=False)

    def _call_llm_json(self, prompt: str) -> Dict[str, Any]:
        try:
            result_text = self._call_llm_generic(prompt, output_json=True)
            return json.loads(result_text)
        except json.JSONDecodeError:
            # Fallback or error handling
            # For now, just raise or return empty
            return {"error": "Failed to parse JSON", "raw_output": result_text}

    def _call_llm_generic(self, prompt: str, output_json: bool = False) -> str:
        import time

        result_text = ""
        # Removed try-except to allow exceptions (e.g. Rate Limit) to propagate
        if self.provider == "google":
            from google.genai import types

            config_args = {}
            if output_json:
                config_args["response_mime_type"] = "application/json"

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_args),
            )
            result_text = response.text
        else:
            kwargs = {}
            if output_json:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            result_text = response.choices[0].message.content

        time.sleep(3)  # Rate limit mitigation
        return result_text
