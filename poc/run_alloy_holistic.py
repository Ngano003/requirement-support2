import sys
import json
import re
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from poc.run_alloy_poc import (
    load_text,
    save_text,
    extract_code_block,
    extract_json_block,
    run_alloy_check,
    LLMGatewayImpl,
    REQ_FILE_PATHS,
    INTERMEDIATE_DIR,
)

PROMPT_GENERATE_HOLISTIC = "prompts/generate_holistic_alloy.md"
PROMPT_ANALYZE_HOLISTIC = "prompts/analyze_holistic_results.md"
PROMPT_LLM_FALLBACK = "prompts/llm_fallback_review.md"  # For holistic fallback?
MAX_RETRIES = 5


def main():
    print("Starting Holistic Alloy Verification...")
    gateway = LLMGatewayImpl()

    # 1. Load Requirements & Structure
    print("Step 1: Loading Requirements and Structure...")
    req_text = ""
    for path in REQ_FILE_PATHS:
        req_text += load_text(path) + "\n\n"

    structure_path = INTERMEDIATE_DIR / "agv_structure.json"
    if not structure_path.exists():
        print(
            "Error: agv_structure.json not found. Run run_alloy_poc.py first to generate structure."
        )
        return
    structure_text = load_text(structure_path)

    # 2. Generate Holistic Alloy Model (with Retry)
    print("Step 2: Generating Holistic Alloy Model...")
    prompt_tmpl = load_text(project_root / PROMPT_GENERATE_HOLISTIC)

    prompt = prompt_tmpl.replace(
        "{{requirement_text}}", req_text[:10000]
    ).replace(  # Allow larger text
        "{{structure_json}}", structure_text
    )  # This key might need to be added to prompt
    # Prompt text in `generate_holistic_alloy.md` doesn't have placeholders yet.
    # Need to update prompt or just append.
    # Actually, the prompt created in previous step didn't have {{}} placeholders.
    # Let's fix that in this script by just appending text.

    prompt_input = (
        prompt_tmpl
        + "\n\n# Requirements:\n"
        + req_text[:10000]
        + "\n\n# Structure:\n"
        + structure_text[:10000]
    )

    alloy_code = ""
    last_error = ""

    # Check if we should reuse existing model (for debugging speedup)
    als_path = INTERMEDIATE_DIR / "holistic_system.als"
    if als_path.exists():
        alloy_code = load_text(als_path)
        print("  (Using existing holistic_system.als)")
    else:
        for attempt in range(MAX_RETRIES):
            print(f"  Attempt {attempt+1}/{MAX_RETRIES}...")

            if attempt > 0 and last_error:
                # Feedback prompt
                current_prompt = f"{prompt_input}\n\nPreivous Alloy code had errors:\n{last_error}\n\nPlease fix the Alloy code."
            else:
                current_prompt = prompt_input

            resp = gateway.call_llm_text(current_prompt)
            alloy_code = extract_code_block(resp, "alloy")

            if not alloy_code:
                print("  Failed to extract Alloy code.")
                continue

            # Save temporarily to check syntax
            als_path = INTERMEDIATE_DIR / "holistic_system.als"
            save_text(als_path, alloy_code)

            # Dry run to check syntax (checking first assertion)
            # Note: run_alloy_check runs all commands in the file.
            # If it returns error in "error" field, it's a syntax/compilation error.

            result = run_alloy_check(str(als_path))

            if "error" in result:
                last_error = result["error"]
                if result.get("stderr"):
                    last_error += "\n" + result["stderr"]
                print(f"  ❌ Syntax/Type error: {last_error[:200]}...")
                continue
            else:
                print("  ✅ Alloy code generated and compiled successfully.")
                last_error = ""
                break

    if last_error:
        print("❌ Failed to generate valid Alloy code after retries.")
        # Fallback logic could go here
        return

    # 3. Analyze Results & Generate Detailed Report
    print("Step 3: Analyzing Verification Results...")
    result = run_alloy_check(str(als_path))

    prompt_analyze_tmpl = load_text(project_root / PROMPT_ANALYZE_HOLISTIC)

    report = "# Alloy全体検証レポート\n\n"
    report += f"**実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += f"**モデル**: `poc/intermediates/holistic_system.als`\n\n"

    if "results" in result:
        for cmd_res in result["results"]:
            cmd_name = cmd_res.get("command", "Unknown")
            status = cmd_res.get("status", "UNKNOWN")

            icon = (
                "✅"
                if status == "PASSED"
                else "⚠️" if status == "VIOLATION_FOUND" else "❓"
            )

            report += f"## {icon} {cmd_name}\n\n"
            report += f"**判定**: {status}\n\n"

            if status == "VIOLATION_FOUND":
                msg = cmd_res.get("message", "")
                report += f"**検出された問題**: {msg}\n\n"

                # --- Detailed Analysis using JSON Trace ---
                print(f"  Analyzing Trace for {cmd_name}...")

                # Find corresponding JSON file in alloy_temp/cli_output_tmp
                # Format is typically: CheckName-solution-0.json. CheckName might differ slightly from cmd_name
                # We search by partial match

                cli_output_dir = project_root / "alloy_temp" / "cli_output_tmp"
                json_files = list(cli_output_dir.glob("*.json"))
                target_json = None

                # Normalize command name to match filename pattern
                # cmd_name example: "Check DeadlockFree for 10 Step..." -> we need "DeadlockFree"
                # But filename is "DeadlockFree-solution-0.json".

                # Extract simple name (e.g. DeadlockFree) from command string
                simple_name = (
                    cmd_name.split()[1] if len(cmd_name.split()) > 1 else cmd_name
                )

                # Try to find matching file (most recent one preferably)
                candidates = [f for f in json_files if simple_name in f.name]
                if candidates:
                    # Sort by modification time, newest first
                    candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    target_json = candidates[0]

                trace_content = "{}"
                if target_json:
                    print(f"    Found trace file: {target_json.name}")
                    trace_content = load_text(target_json)
                else:
                    print(f"    ⚠️ Trace JSON not found for {simple_name}")

                # Call LLM for detailed analysis
                prompt_analyze = (
                    prompt_analyze_tmpl.replace(
                        "{{alloy_code}}", alloy_code[:20000]
                    )  # Code
                    .replace("{{assertion_name}}", cmd_name)
                    .replace("{{trace_json}}", trace_content[:30000])  # Trace limit
                )

                analysis = gateway.call_llm_text(prompt_analyze)
                report += f"### 詳細解説\n\n{analysis}\n\n"
                # ----------------------------------------

            report += "---\n\n"

    report_path = project_root / "poc" / "holistic_report.md"
    save_text(report_path, report)
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
