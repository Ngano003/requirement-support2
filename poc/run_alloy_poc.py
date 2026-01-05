import os
import sys
import re
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Ensure stdout uses utf-8
sys.stdout.reconfigure(encoding="utf-8")

from src.infrastructure.llm_gateway import LLMGatewayImpl
from src.alloy.alloy_wrapper import run_alloy_check


def main():
    # Paths
    req_file_paths = [
        project_root / "doc" / "samples" / "01_agv_core_logic.md",
        project_root / "doc" / "samples" / "02_agv_communication.md",
        project_root / "doc" / "samples" / "03_agv_hardware_safety.md",
    ]
    prompt_file_path = project_root / "prompts" / "generate_alloy.md"
    output_als_path = project_root / "poc" / "agv_system.als"

    # 1. Load Requirements
    print("Loading requirements...")
    req_text = ""
    for path in req_file_paths:
        if not path.exists():
            print(f"Error: {path} not found.")
            return
        print(f"Reading {path.name}...")
        with open(path, "r", encoding="utf-8") as f:
            req_text += f.read() + "\n\n"

    # 2. Load Prompt
    print("Loading prompt...")
    if not prompt_file_path.exists():
        print(f"Error: {prompt_file_path} not found.")
        return
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # 3. Generate Alloy Code
    print("Generating Alloy code using LLM...")
    prompt = prompt_template.replace("{{requirement_text}}", req_text)

    gateway = LLMGatewayImpl()
    response = gateway.call_llm_text(prompt)

    # Extract code from markdown block if present
    match = re.search(r"```alloy\n(.*?)\n```", response, re.DOTALL)
    if match:
        alloy_code = match.group(1)
    else:
        # Try finding standard markdown block without 'alloy' specifier or just use raw text
        match_generic = re.search(r"```\n(.*?)\n```", response, re.DOTALL)
        if match_generic:
            alloy_code = match_generic.group(1)
        else:
            alloy_code = response

    # Post-process to treat apostrophe in variable names (Alloy 6 syntax conflict prevention)
    # e.g. s' -> s_next
    # We replace "word'" with "word_next" globally to be safe
    alloy_code = re.sub(r"\b([a-zA-Z][a-zA-Z0-9_]*)'", r"\1_next", alloy_code)

    # Fix potential invalid comment syntax staring with / instead of //
    # Only if it looks like a separator line
    alloy_code = re.sub(r"^/-+$", r"--", alloy_code, flags=re.MULTILINE)

    print("Alloy Code Generated:")
    print("-" * 40)
    print(alloy_code)
    print("-" * 40)

    # 4. Save Alloy Code
    print(f"Saving Alloy code to {output_als_path}...")
    with open(output_als_path, "w", encoding="utf-8") as f:
        f.write(alloy_code)

    # 5. Run Alloy Check
    print("Running Alloy check...")
    result = run_alloy_check(str(output_als_path))

    # 6. Show Results
    print("\n=== Verification Result ===")
    if "error" in result:
        print(f"Execution Error: {result['error']}")
        if "stderr" in result:
            print(f"STDERR: {result['stderr']}")
    else:
        results = result.get("results", [])
        for cmd_res in results:
            print(f"Command: {cmd_res.get('command')}")
            print(f"Status: {cmd_res.get('status')}")
            print(f"Message: {cmd_res.get('message')}")
            if cmd_res.get("status") == "VIOLATION_FOUND":
                print("Trace/Counterexample:")
                trace = cmd_res.get("trace", {})
                for k, v in trace.items():
                    print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
