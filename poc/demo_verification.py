import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.infrastructure.llm_gateway import LLMGatewayImpl

# Configuration
REQ_FILE_PATHS = [
    project_root / "requirements" / "smart_lock.md",
]
PROMPT_PATH = project_root / "prompts" / "verify_requirements_llm.md"
REPORT_PATH = project_root / "poc" / "smart_lock_verification_report.md"


def load_text(path: Path) -> str:
    if not path.exists():
        print(f"Error: {path} not found.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_text(path: Path, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def extract_json_block(text: str) -> dict:
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        json_str = text.strip()
        if json_str.startswith("```"):
            lines = json_str.splitlines()
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                json_str = "\n".join(lines[1:-1])
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")
        return {}


def generate_report_markdown(data: dict, req_files: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = data.get("summary", "No summary provided.")
    defects = data.get("defects", [])

    report = f"# Verification Report: Smart Lock System\n\n"
    report += f"**Timestamp**: {now}\n"
    report += f"**Target File**: {', '.join([f.name for f in req_files])}\n\n"
    report += "## Summary\n"
    report += f"{summary}\n\n"

    if not defects:
        report += "> [!NOTE]\n> No significant defects found.\n\n"
        return report

    report += "## Critical Defects\n\n"
    for d in defects:
        icon = (
            "🔴"
            if d.get("severity") == "Critical"
            else ("🟠" if d.get("severity") == "Major" else "🔵")
        )
        report += f"### {icon} [{d.get('id')}] {d.get('category')}\n"
        report += f"- **Severity**: {d.get('severity')}\n"
        report += f"- **Location**: {d.get('location')}\n"
        report += f"- **Description**: {d.get('description')}\n"
        report += f"- **Recommendation**: {d.get('recommendation')}\n\n"

    return report


def main():
    print(f"Running verification on {REQ_FILE_PATHS[0].name}...")

    # 1. Load
    req_text = ""
    for path in REQ_FILE_PATHS:
        req_text += f"\n\n# Document: {path.name}\n"
        req_text += load_text(path)

    # 2. Prompt
    prompt_tmpl = load_text(PROMPT_PATH)
    prompt = prompt_tmpl.replace("{{requirement_text}}", req_text)

    # 3. LLM
    print("Sending to LLM...")
    gateway = LLMGatewayImpl()
    response = gateway.call_llm_text(prompt)

    # 4. Save & Report
    result_json = extract_json_block(response)
    if result_json:
        report = generate_report_markdown(result_json, REQ_FILE_PATHS)
        save_text(REPORT_PATH, report)
        print(f"Done! Report saved to {REPORT_PATH}")
    else:
        print("Failed to parse result.")


if __name__ == "__main__":
    main()
