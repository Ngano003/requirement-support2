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
    project_root / "requirements" / "samples" / "agv_system" / "01_agv_core_logic.md",
    project_root
    / "requirements"
    / "samples"
    / "agv_system"
    / "02_agv_communication.md",
    project_root
    / "requirements"
    / "samples"
    / "agv_system"
    / "03_agv_hardware_safety.md",
]
PROMPT_PATH = project_root / "prompts" / "verify_requirements_llm.md"
REPORT_PATH = project_root / "poc" / "llm_verification_report.md"


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
        # Fallback
        json_str = text.strip()
        if json_str.startswith("```"):
            lines = json_str.splitlines()
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                json_str = "\n".join(lines[1:-1])

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")
        print("Raw text snippet:", json_str[:200])
        return {}


def generate_report_markdown(data: dict, req_files: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = data.get("summary", "No summary provided.")
    defects = data.get("defects", [])

    report = f"# LLM要件検証レポート\n\n"
    report += f"**実行日時**: {now}\n"
    report += f"**対象ファイル**: {', '.join([f.name for f in req_files])}\n\n"

    report += "## エグゼクティブサマリー\n"
    report += f"{summary}\n\n"

    if not defects:
        report += "> [!NOTE]\n> 重大な欠陥は検出されませんでした。\n\n"
        return report

    # Count severity
    critical = sum(1 for d in defects if d.get("severity") == "Critical")
    major = sum(1 for d in defects if d.get("severity") == "Major")
    minor = sum(1 for d in defects if d.get("severity") == "Minor")

    report += f"| Critical | Major | Minor | Total |\n"
    report += f"| :---: | :---: | :---: | :---: |\n"
    report += f"| {critical} | {major} | {minor} | {len(defects)} |\n\n"

    report += "## 検出された欠陥一覧\n\n"

    for d in defects:
        icon = (
            "🔴"
            if d.get("severity") == "Critical"
            else ("🟠" if d.get("severity") == "Major" else "🔵")
        )
        report += f"### {icon} [{d.get('id', 'N/A')}] {d.get('category', 'Issue')}\n\n"
        report += f"**Severity**: {d.get('severity')}\n"
        report += f"**Location**: {d.get('location')}\n\n"
        report += f"**Description**:\n{d.get('description')}\n\n"
        report += f"**Recommendation**:\n{d.get('recommendation')}\n\n"
        report += "---\n\n"

    return report


def main():
    print("Starting LLM-based Requirement Verification...")

    # 1. Load Requirements
    print("Loading requirements...")
    req_text = ""
    for path in REQ_FILE_PATHS:
        print(f"Reading {path.name}...")
        req_text += f"\n\n# Document: {path.name}\n"
        req_text += load_text(path)

    # 2. Build Prompt
    print("Building prompt...")
    prompt_tmpl = load_text(PROMPT_PATH)
    prompt = prompt_tmpl.replace("{{requirement_text}}", req_text)

    # 3. Call LLM
    print("Calling LLM (Gemini)...")
    gateway = LLMGatewayImpl()
    response_text = gateway.call_llm_text(prompt)

    # 4. Parse & Save
    print("Parsing response...")
    result_json = extract_json_block(response_text)

    if not result_json:
        print("Failed to parse LLM response into JSON.")
        # Save raw response for debug
        save_text(project_root / "poc" / "llm_raw_response.txt", response_text)
        print(f"Raw response saved to poc/llm_raw_response.txt")
        return

    # Save JSON for intermediate check
    save_text(
        project_root / "poc" / "llm_verification_result.json",
        json.dumps(result_json, indent=2, ensure_ascii=False),
    )

    # Generate Markdown Report
    print("Generating report...")
    report_md = generate_report_markdown(result_json, REQ_FILE_PATHS)
    save_text(REPORT_PATH, report_md)

    print(f"✅ Verification complete. Report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
