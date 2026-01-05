import json
import uuid
import os
from typing import List, Tuple, Optional
from src.domain.breakdown_models import Question, SessionData
from src.domain.interfaces import LLMGateway


class BreakdownService:
    """Requirement Breakdown Service"""

    def __init__(self, llm_gateway: LLMGateway):
        self.llm = llm_gateway
        # Resolve prompts directory relative to project root
        # src/application/services/ -> ../../../prompts
        self.prompts_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts")
        )

    def _load_prompt(self, filename: str) -> str:
        path = os.path.join(self.prompts_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def initialize_session(self, input_text: str) -> SessionData:
        """
        Initialize session, generate draft requirements and questions.
        """
        system_prompt = self._load_prompt("breakdown_system.md")

        # Generate Draft Requirements
        draft_tmpl = self._load_prompt("breakdown_draft.md")
        draft_prompt = draft_tmpl.replace("{{input_text}}", input_text)

        draft_requirements = self.llm.call_llm_with_system(system_prompt, draft_prompt)

        # Generate Questions
        questions_tmpl = self._load_prompt("breakdown_questions.md")
        questions_prompt = questions_tmpl.replace("{{input_text}}", input_text).replace(
            "{{draft_requirements}}", draft_requirements
        )

        questions_json = self.llm.call_llm_with_system(system_prompt, questions_prompt)
        questions = self._parse_questions(questions_json)

        session_id = str(uuid.uuid4())

        return SessionData(
            session_id=session_id,
            input_text=input_text,
            requirements=draft_requirements,
            questions=questions,
            answered_questions=[],
            answers={},
            completion_rate=0.0,
        )

    def validate_answer(
        self, question: str, answer: str, history: List[Tuple[str, str]]
    ) -> Tuple[bool, Optional[str]]:
        system_prompt = self._load_prompt("breakdown_system.md")

        history_text = ""
        for q, a in history:
            history_text += f"Q: {q}\nA: {a}\n\n"

        validate_tmpl = self._load_prompt("breakdown_validate.md")
        prompt = (
            validate_tmpl.replace("{{history_text}}", history_text)
            .replace("{{question}}", question)
            .replace("{{answer}}", answer)
        )

        response = self.llm.call_llm_with_system(system_prompt, prompt)
        try:
            # Basic cleanup
            response = response.strip()
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response)
            return data.get("is_valid", True), data.get("follow_up")
        except:
            return True, None

    def process_answer(
        self, session_data: SessionData, question_id: str, answer: str
    ) -> Tuple[bool, Optional[str]]:
        question = next(
            (q for q in session_data.questions if q.id == question_id), None
        )
        if not question:
            return False, "Question not found"

        # Build history
        history = [
            (q.question, session_data.answers.get(q.id, ""))
            for q in session_data.answered_questions
        ]

        is_valid, follow_up = self.validate_answer(question.question, answer, history)

        if is_valid:
            session_data.answers[question_id] = answer
            session_data.questions.remove(question)
            session_data.answered_questions.append(question)
            return True, None
        else:
            return False, follow_up

    def update_requirements(self, session_data: SessionData) -> str:
        system_prompt = self._load_prompt("breakdown_system.md")

        qa_text = ""
        for q in session_data.answered_questions:
            qa_text += f"\nQ: {q.question}\nA: {session_data.answers.get(q.id)}\n"

        update_tmpl = self._load_prompt("breakdown_update.md")
        prompt = update_tmpl.replace(
            "{{current_requirements}}", session_data.requirements
        ).replace("{{qa_text}}", qa_text)

        return self.llm.call_llm_with_system(system_prompt, prompt)

    def generate_next_questions(self, session_data: SessionData) -> List[Question]:
        system_prompt = self._load_prompt("breakdown_system.md")

        qa_text = ""
        for q in session_data.answered_questions:
            qa_text += f"\nQ: {q.question}\nA: {session_data.answers.get(q.id)}\n"

        next_q_tmpl = self._load_prompt("breakdown_next_questions.md")
        next_id = f"q{len(session_data.answered_questions) + 1}"
        prompt = (
            next_q_tmpl.replace("{{requirements}}", session_data.requirements)
            .replace("{{qa_text}}", qa_text)
            .replace("{{next_id}}", next_id)
        )

        response = self.llm.call_llm_with_system(system_prompt, prompt)
        return self._parse_questions(response)

    def _parse_questions(self, json_str: str) -> List[Question]:
        try:
            json_str = json_str.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str)
            questions = []
            for item in data:
                try:
                    questions.append(Question(**item))
                except:
                    continue
            return questions
        except:
            return []
