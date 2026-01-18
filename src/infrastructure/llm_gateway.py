import os
import json
import re
import time
import random
from typing import Dict, Any, List, Callable
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

    def _extract_json_block(self, text: str) -> dict:
        # Remove <think> blocks (often from reasoning models)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

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
            return {"summary": "Error parsing LLM response", "defects": []}

    def _retry_with_backoff(
        self, func: Callable, max_retries: int = 5, initial_delay: float = 2.0
    ) -> str:
        """
        Executes a function with exponential backoff on exception.
        """
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                # Check for rate limit keywords if possible
                error_msg = str(e).lower()
                is_rate_limit = (
                    "429" in error_msg
                    or "quota" in error_msg
                    or "rate limit" in error_msg
                )

                if attempt == max_retries - 1:
                    print(f"Max retries reached. Last error: {e}")
                    raise e

                print(f"Request failed (Attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {delay:.2f} seconds...")

                time.sleep(delay)
                # Exponential backoff with jitter
                delay = delay * 2 + random.uniform(0, 1)
        return ""

    def _call_llm_generic(self, prompt: str, temperature: float = None) -> str:
        if self.provider == "google":
            from google.genai.types import GenerateContentConfig

            def call_google():
                config = (
                    GenerateContentConfig(temperature=temperature)
                    if temperature is not None
                    else None
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                return response.text

            return self._retry_with_backoff(call_google)
        else:

            def call_openai():
                kwargs = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if temperature is not None:
                    kwargs["temperature"] = temperature

                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content

            return self._retry_with_backoff(call_openai)

    # Deprecated interface methods
    def extract_structure(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError("This method is deprecated.")

    def verify_condition_exhaustiveness(
        self, condition: str, outgoing_paths: List[str]
    ) -> Dict[str, Any]:
        raise NotImplementedError("This method is deprecated.")

    def check_text_contradiction(self, text_a: str, text_b: str) -> Dict[str, Any]:
        raise NotImplementedError("This method is deprecated.")

    def call_llm_text(self, prompt: str) -> str:
        return self._call_llm_generic(prompt)

    def call_llm_with_system(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "google":

            def call_google():
                # Gemini doesn't strictly have a "system" role in the same way as OpenAI in generate_content
                # But we can use system_instruction if using the beta client or just prepend it.
                # Since we are using genai.Client (Google Gen AI SDK v0.x or 1.x?), let's check init.
                # The code uses genai.Client(api_key=...) which suggests the newer SDK.
                # However, for simplicity and compatibility with the existing _call_llm_generic pattern:
                # We will prepend the system prompt or use config if available.
                # Actually, the simplest way for both providers that is robust:
                full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                )
                return response.text

            return self._retry_with_backoff(call_google)
        else:

            def call_openai():
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response.choices[0].message.content

            return self._retry_with_backoff(call_openai)
