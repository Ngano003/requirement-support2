import os
import json
import re
from typing import Dict, Any, List
from pathlib import Path
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
            self.model_name = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-exp")
            self.client = genai.Client(api_key=self.google_api_key)
        else:
            self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
            self.client = OpenAI(
                api_key=self.openai_api_key, base_url=self.openai_base_url
            )

        # Resolve prompt path
        # Assuming src/infrastructure/llm_gateway.py -> ../../prompts
        self.prompt_path = (
            Path(__file__).parent.parent.parent
            / "prompts"
            / "verify_requirements_llm.md"
        )

    def verify_requirements(self, text: str) -> Dict[str, Any]:
        if not self.prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found at {self.prompt_path}")

        with open(self.prompt_path, "r", encoding="utf-8") as f:
            prompt_tmpl = f.read()

        prompt = prompt_tmpl.replace("{{requirement_text}}", text)

        response_text = self._call_llm_generic(prompt)
        return self._extract_json_block(response_text)

    def extract_structure(self, text: str) -> Dict[str, Any]:
        # Deprecated or Unused in new flow, but keeping empty or simplified if interface is strict?
        # Interface was updated to ONLY have verify_requirements in previous step?
        # Wait, I updated src/domain/interfaces.py in Step 116 to ONLY have verify_requirements.
        # So I should remove this.
        raise NotImplementedError("This method is deprecated.")

    def verify_condition_exhaustiveness(
        self, condition: str, outgoing_paths: List[str]
    ) -> Dict[str, Any]:
        raise NotImplementedError("This method is deprecated.")

    def check_text_contradiction(self, text_a: str, text_b: str) -> Dict[str, Any]:
        raise NotImplementedError("This method is deprecated.")

    def call_llm_text(self, prompt: str) -> str:
        return self._call_llm_generic(prompt)

    def _extract_json_block(self, text: str) -> dict:
        match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback
            json_str = text.strip()
            if json_str.startswith("```"):
                lines = json_str.splitlines()
                if lines[0].startswith("```") and lines[-1].startswith("```"):
                    json_str = "\n".join(lines[1:-1])

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Return raw struct with error/empty
            return {"summary": "Error parsing LLM response", "defects": []}

    def _call_llm_generic(self, prompt: str) -> str:
        result_text = ""
        try:
            if self.provider == "google":
                from google.genai import types

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    # config=types.GenerateContentConfig(response_mime_type="application/json"), # Prompt expects Markdown+JSON mixed output usually?
                    # actually the prompt verify_requirements_llm.md expects JSON output block.
                    # but let's be safe and just get text.
                )
                result_text = response.text
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                )
                result_text = response.choices[0].message.content
        except Exception as e:
            print(f"LLM Call failed: {e}")
            raise e

        return result_text
