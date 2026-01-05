import sys
import json
import re
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from poc.run_alloy_poc import (
    generate_final_report,
    save_text,
    load_text,
    run_alloy_check,
    LLMGatewayImpl,
    PROMPT_ANALYZE_RESULTS,
    REQ_FILE_PATHS,
)


def main():
    print("Regenerating Analysis Report...")
    INTERMEDIATE_DIR = project_root / "poc" / "intermediates"

    # Load Requirements
    req_text = ""
    for path in REQ_FILE_PATHS:
        req_text += load_text(path) + "\n\n"

    # Load Viewpoints
    vp_path = INTERMEDIATE_DIR / "generated_viewpoints.json"
    if not vp_path.exists():
        # Fallback to extracted_viewpoints if generated doesn't exist
        vp_path = INTERMEDIATE_DIR / "extracted_viewpoints.json"

    if not vp_path.exists():
        print(f"Error: Viewpoints json not found.")
        return

    print(f"Loading viewpoints from {vp_path.name}")
    with open(vp_path, "r", encoding="utf-8") as f:
        viewpoints_data = json.load(f)
        viewpoints = viewpoints_data.get("viewpoints", [])

    gateway = LLMGatewayImpl()
    prompt_analyze_tmpl = load_text(PROMPT_ANALYZE_RESULTS)

    results_summary = []

    # Process each viewpoint
    for vp in viewpoints:
        vp_id = vp.get("id", "UNKNOWN")
        vp_name = vp.get("name", "Unnamed")
        als_path = INTERMEDIATE_DIR / f"verify_{vp_id}.als"

        if not als_path.exists():
            # print(f"Skipping {vp_id}: ALS file not found.")
            continue

        print(f"Processing {vp_id} ({vp_name})...")
        alloy_code = load_text(als_path)

        # Run Check
        result = run_alloy_check(str(als_path))

        # Analyze Result
        status = "UNKNOWN"
        message = ""
        trace = {}

        if "error" in result:
            status = "ERROR"
            message = result.get("error", "Unknown error")
            if result.get("stderr"):
                message += f"\n詳細: {result.get('stderr', '')[:500]}"
        elif result.get("results"):
            for cmd_res in result["results"]:
                cmd_status = cmd_res.get("status", "UNKNOWN")
                if cmd_status != "UNKNOWN":
                    status = cmd_status
                    message = cmd_res.get("message", "")
                    trace = cmd_res.get("trace", {})
                    break
            if status == "UNKNOWN" and result["results"]:
                status = result["results"][0].get("status", "UNKNOWN")
                message = result["results"][0].get(
                    "message", "結果を解析できませんでした"
                )
        else:
            status = "UNKNOWN"
            message = "Alloy実行結果を取得できませんでした"

        print(f"  Result: {status}")

        results_summary.append(
            {
                "id": vp_id,
                "name": vp_name,
                "description": vp.get("description", ""),
                "status": status,
                "message": message,
                "trace": trace,
                "file": str(als_path),
                "alloy_code": alloy_code,
            }
        )

    # Generate Detailed Analysis with Updated Prompt
    detailed_analyses = []

    # 対象：VIOLATION, ERROR, UNKNOWN + PASSED(数件)
    # 全件やると時間がかかるが、レポート品質確認のため、問題があるものは全て、合格は最大3件

    problem_items = [
        r for r in results_summary if r["status"] in ["VIOLATION_FOUND", "ERROR"]
    ]
    unknown_items = [r for r in results_summary if r["status"] == "UNKNOWN"]
    passed_items = [r for r in results_summary if r["status"] == "PASSED"]

    # 優先順位: VIOLATION/ERROR全件 -> UNKNOWN(2件) -> PASSED(1件)
    targets = problem_items + unknown_items[:2] + passed_items[:1]

    print(f"\nGeneraring detailed analysis for {len(targets)} items...")

    for res in targets:
        print(f"  Analyzing {res['id']}...")
        prompt_analyze = (
            prompt_analyze_tmpl.replace("{{requirement_text}}", req_text[:5000])
            .replace("{{viewpoint_name}}", res["name"])
            .replace("{{viewpoint_description}}", res["description"])
            .replace("{{alloy_code}}", res["alloy_code"][:3000])
            .replace("{{result_status}}", res["status"])
            .replace("{{result_message}}", res["message"])
            .replace("{{result_trace}}", json.dumps(res["trace"], ensure_ascii=False))
        )
        analysis = gateway.call_llm_text(prompt_analyze)
        detailed_analyses.append(
            {"id": res["id"], "name": res["name"], "analysis": analysis}
        )

    # Build Report
    report_content = generate_final_report(results_summary, detailed_analyses, req_text)
    report_path = project_root / "poc" / "analysis_report.md"
    save_text(report_path, report_content)
    print(f"Report regenerates to {report_path}")


if __name__ == "__main__":
    main()
