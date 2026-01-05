import sys
import json
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from poc.run_alloy_poc import (
    load_text,
    save_text,
    extract_json_block,
    LLMGatewayImpl,
    REQ_FILE_PATHS,
    INTERMEDIATE_DIR,
)

PROMPT_EXTRACT_STRUCTURE = "prompts/extract_structure.md"


def main():
    print("Starting Structural Extraction...")
    gateway = LLMGatewayImpl()

    # Load Requirements
    req_text = ""
    for path in REQ_FILE_PATHS:
        print(f"Loading {path.name}...")
        req_text += load_text(path) + "\n\n"

    prompt_tmpl = load_text(project_root / PROMPT_EXTRACT_STRUCTURE)
    prompt = prompt_tmpl.replace("{{requirement_text}}", req_text)

    print("Calling LLM for extraction...")
    resp = gateway.call_llm_text(prompt)

    structure_dict = extract_json_block(resp)
    if not structure_dict:
        print("❌ Failed to extract JSON structure.")
        return

    structure_json_str = json.dumps(structure_dict, indent=2, ensure_ascii=False)

    output_path = INTERMEDIATE_DIR / "agv_structure.json"
    save_text(output_path, structure_json_str)
    print(f"✅ Structure extracted and saved to {output_path}")


if __name__ == "__main__":
    main()
