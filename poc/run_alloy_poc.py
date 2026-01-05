import os
import sys
import re
import json
import shutil
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Ensure stdout uses utf-8
sys.stdout.reconfigure(encoding="utf-8")

from src.infrastructure.llm_gateway import LLMGatewayImpl
from src.alloy.alloy_wrapper import run_alloy_check

# Configuration
INTERMEDIATE_DIR = project_root / "poc" / "intermediates"
REQ_FILE_PATHS = [
    project_root / "doc" / "samples" / "01_agv_core_logic.md",
    project_root / "doc" / "samples" / "02_agv_communication.md",
    project_root / "doc" / "samples" / "03_agv_hardware_safety.md",
]
PROMPT_EXTRACT_STRUCTURE = project_root / "prompts" / "extract_structure.md"
PROMPT_EXTRACT_VIEWPOINTS = project_root / "prompts" / "extract_viewpoints.md"
PROMPT_GENERATE_ALLOY = project_root / "prompts" / "generate_alloy_from_json.md"
PROMPT_ANALYZE_RESULTS = project_root / "prompts" / "analyze_results.md"
PROMPT_LLM_FALLBACK = project_root / "prompts" / "llm_fallback_review.md"


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
        # Fallback: maybe the whole text is JSON or wrapped differently
        json_str = text.strip()
        if json_str.startswith("```"):
            # Try to strip lines
            lines = json_str.splitlines()
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                json_str = "\n".join(lines[1:-1])

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")
        print("Raw text snippet:", json_str[:500])
        return {}


def extract_code_block(text: str, lang: str = "") -> str:
    """
    テキストからコードブロックを抽出する。
    LLMが説明文を含む出力を生成した場合でも、純粋なコードを抽出できるように改善。
    """
    # Case 1: ```alloy ... ``` or ```lang ... ``` (言語指定あり)
    if lang:
        pattern = rf"```{lang}\s*\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

    # Case 2: Generic ``` ... ``` (言語指定なし)
    match_generic = re.search(r"```\s*\n(.*?)\n```", text, re.DOTALL)
    if match_generic:
        return match_generic.group(1).strip()

    # Case 3: 複数のコードブロックがある場合、最初の有効なものを探す
    all_blocks = re.findall(r"```(?:\w*)\s*\n(.*?)\n```", text, re.DOTALL)
    for block in all_blocks:
        block = block.strip()
        # Alloyコードらしいかチェック（module, open, sig, fact, pred, assert, check）
        if any(
            block.startswith(kw)
            for kw in [
                "module",
                "open",
                "sig",
                "fact",
                "pred",
                "assert",
                "check",
                "--",
                "//",
            ]
        ):
            return block
        # 先頭行がAlloyキーワードで始まるか
        first_line = block.split("\n")[0].strip() if block else ""
        if any(
            first_line.startswith(kw)
            for kw in [
                "module",
                "open",
                "sig",
                "fact",
                "pred",
                "assert",
                "check",
                "--",
                "//",
            ]
        ):
            return block

    # Case 4: コードブロックなしで、テキストがAlloyコードで始まる場合
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(
            stripped.startswith(kw)
            for kw in ["module", "open", "sig", "fact", "pred", "assert", "check"]
        ):
            return "\n".join(lines[i:]).strip()

    # Fallback: そのまま返す
    return text.strip()


def generate_viewpoints_from_structure(structure: dict) -> list:
    """
    構造化データから機械的に検証観点を生成する。
    網羅的かつ再現性のある観点リストを作成。
    """
    viewpoints = []
    vp_id = 1

    # 1. 状態遷移の観点（Liveness）
    states = structure.get("state_transition", {}).get("states", [])
    transitions = structure.get("state_transition", {}).get("transitions", [])

    # 各状態からの遷移可能性（Dead End チェック）
    terminal_states = {"SafeMode"}  # 最終状態として扱う
    for state in states:
        if state not in terminal_states:
            # この状態からの遷移が存在するか確認
            outgoing = [
                t for t in transitions if t.get("src") == state or t.get("src") == "*"
            ]
            if outgoing:
                viewpoints.append(
                    {
                        "id": f"VP_{vp_id:03d}",
                        "category": "Liveness",
                        "name": f"{state}状態からの遷移可能性",
                        "description": f"{state}状態から少なくとも1つの遷移先が存在することを検証する。Dead Endがないことを確認。",
                        "priority": "High",
                        "target_states": [state],
                    }
                )
                vp_id += 1

    # 2. リソース排他制御の観点（Safety）
    resources = structure.get("resource_concurrency", {}).get("resources", [])
    for resource in resources:
        name = resource.get("name", "")
        rules = resource.get("access_rules", [])
        # 排他アクセスが必要なリソースのみ
        if any("exclusive" in r.lower() or "only one" in r.lower() for r in rules):
            viewpoints.append(
                {
                    "id": f"VP_{vp_id:03d}",
                    "category": "Safety",
                    "name": f"{name}の排他制御",
                    "description": f"{name}リソースに同時に複数のAGVがアクセスできないことを検証する。{'; '.join(rules[:2])}",
                    "priority": "High",
                    "target_resources": [name],
                }
            )
            vp_id += 1

    # 3. ガード条件の観点（Safety/Consistency）
    guards = structure.get("logic_guard", [])
    guard_categories = {}
    for guard in guards:
        cat = guard.get("category", "")
        if cat not in guard_categories:
            guard_categories[cat] = []
        guard_categories[cat].append(guard)

    # 重要なガード条件カテゴリのみ
    priority_categories = ["Battery_SOC", "LDS_Distance", "Speed", "WiFi_RSSI"]
    for cat in priority_categories:
        if cat in guard_categories:
            guards_in_cat = guard_categories[cat]
            conditions = [g.get("condition", "") for g in guards_in_cat[:3]]
            viewpoints.append(
                {
                    "id": f"VP_{vp_id:03d}",
                    "category": "Safety",
                    "name": f"{cat}ガード条件の検証",
                    "description": f"{cat}に関するガード条件({', '.join(conditions[:2])})が正しく適用されることを検証する。",
                    "priority": "Medium",
                    "target_guards": conditions,
                }
            )
            vp_id += 1

    # 4. 状態→状態の遷移ペアの観点（主要な遷移のみ）
    important_transitions = [
        ("Error", "Maintenance", "Error状態からMaintenanceへの復帰"),
        ("Error", "SafeMode", "Error状態からSafeModeへの遷移"),
        ("Charging", "Idle", "充電完了後のIdle復帰"),
        ("Moving", "Paused", "障害物検知時のPaused遷移"),
        ("Paused", "Moving", "障害物除去後のMoving復帰"),
    ]
    for src, tgt, name in important_transitions:
        # この遷移が定義されているか確認
        matching = [
            t for t in transitions if t.get("src") == src and t.get("tgt") == tgt
        ]
        if matching:
            t = matching[0]
            viewpoints.append(
                {
                    "id": f"VP_{vp_id:03d}",
                    "category": "Liveness",
                    "name": name,
                    "description": f"{src}状態から{tgt}状態への遷移が、条件「{t.get('condition', 'N/A')}」を満たすとき可能であることを検証する。",
                    "priority": "High",
                    "target_states": [src, tgt],
                }
            )
            vp_id += 1

    return viewpoints


def main():
    # Setup
    if INTERMEDIATE_DIR.exists():
        shutil.rmtree(INTERMEDIATE_DIR)
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

    gateway = LLMGatewayImpl()

    # 1. Load Requirements
    print("Loading requirements...")
    req_text = ""
    for path in REQ_FILE_PATHS:
        print(f"Reading {path.name}...")
        req_text += load_text(path) + "\n\n"

    # 2. Extract Structure
    print("Step 1: Extracting Structure (4 Dimensions)...")
    prompt_struct_tmpl = load_text(PROMPT_EXTRACT_STRUCTURE)
    prompt_struct = prompt_struct_tmpl.replace("{{requirement_text}}", req_text)

    resp_struct = gateway.call_llm_text(prompt_struct)
    structure_json = extract_json_block(resp_struct)

    struct_json_path = INTERMEDIATE_DIR / "agv_structure.json"
    save_text(
        struct_json_path, json.dumps(structure_json, indent=2, ensure_ascii=False)
    )
    print(f"Structure saved to {struct_json_path}")

    # 3. Generate Viewpoints (機械的に生成 - 網羅的)
    print("Step 2: Generating Viewpoints from Structure...")
    viewpoints = generate_viewpoints_from_structure(structure_json)

    vp_json_path = INTERMEDIATE_DIR / "generated_viewpoints.json"
    save_text(
        vp_json_path,
        json.dumps({"viewpoints": viewpoints}, indent=2, ensure_ascii=False),
    )
    print(f"Generated {len(viewpoints)} viewpoints (saved to {vp_json_path})")

    # 4. Loop Verification
    print("Step 3: Verification Loop...")
    prompt_alloy_tmpl = load_text(PROMPT_GENERATE_ALLOY)

    results_summary = []

    for vp in viewpoints:
        vp_id = vp.get("id", "UNKNOWN")
        vp_name = vp.get("name", "Unnamed")
        print(f"\n--- Verifying Viewpoint: {vp_id} {vp_name} ---")

        # Retry loop for Alloy generation and execution
        MAX_RETRIES = 3
        last_error = ""
        alloy_code = ""
        result = {}

        for attempt in range(1, MAX_RETRIES + 1):
            print(f"  Attempt {attempt}/{MAX_RETRIES}...")

            # Prepare Prompt
            prompt_alloy = (
                prompt_alloy_tmpl.replace(
                    "{{structure_json}}", json.dumps(structure_json, ensure_ascii=False)
                )
                .replace("{{viewpoint_name}}", vp_name)
                .replace("{{viewpoint_description}}", vp.get("description", ""))
            )

            # Add error feedback for retry
            if last_error:
                prompt_alloy += f"\n\n## 前回のエラー（修正してください）\n```\n{last_error[:1000]}\n```\n上記のエラーを修正したAlloyコードを出力してください。エラー箇所を特にに注意してください。"

            resp_alloy = gateway.call_llm_text(prompt_alloy)
            alloy_code = extract_code_block(resp_alloy, "alloy")

            # Post-process Alloy code
            alloy_code = re.sub(r"\b([a-zA-Z][a-zA-Z0-9_]*)'", r"\1_next", alloy_code)
            alloy_code = re.sub(r"^/-+$", r"--", alloy_code, flags=re.MULTILINE)

            # Save ALS
            als_path = INTERMEDIATE_DIR / f"verify_{vp_id}.als"
            save_text(als_path, alloy_code)
            print(f"  Generated {als_path.name}")

            # Run Check
            result = run_alloy_check(str(als_path))

            # Check if it's a syntax/compilation error
            if "error" in result:
                error_msg = result.get("stderr", "") or result.get("error", "")
                if (
                    "Syntax error" in error_msg
                    or "Type error" in error_msg
                    or "cannot be found" in error_msg
                ):
                    print(f"  ❌ Syntax/Type error detected, will retry...")
                    last_error = error_msg
                    continue  # Retry
                else:
                    # Other errors (not retriable)
                    print(f"  ❌ Non-retriable error: {result.get('error', '')[:100]}")
                    break
            else:
                # Success!
                print(f"  ✅ Alloy execution successful")
                last_error = ""
                break

        # Analyze Result
        status = "UNKNOWN"
        message = ""
        trace = {}

        # 3回失敗した場合のLLMフォールバック検証
        if last_error:
            print(
                f"  ⚠️ Alloy execution failed after {MAX_RETRIES} attempts. Falling back to LLM review..."
            )
            status = "ERROR"  # 一旦エラーにするが、LLMレビューで上書きされる可能性あり

            prompt_fallback_tmpl = load_text(PROMPT_LLM_FALLBACK)
            prompt_fallback = (
                prompt_fallback_tmpl.replace("{{viewpoint_name}}", vp_name)
                .replace("{{viewpoint_description}}", vp.get("description", ""))
                .replace("{{requirement_text}}", req_text[:5000])
            )

            resp_fallback = gateway.call_llm_text(prompt_fallback)
            fallback_result = extract_json_block(resp_fallback)

            if fallback_result:
                # LLMレビュー結果を採用
                llm_status = fallback_result.get("status", "UNCLEAR")
                # マッピング: LLMのPASSED -> PASSED, VIOLATION -> VIOLATION_FOUND
                if llm_status == "PASSED":
                    status = "PASSED"
                elif llm_status == "VIOLATION":
                    status = "VIOLATION_FOUND"
                else:
                    status = "UNKNOWN"  # UNCLEAR等

                message = f"[LLM Review] {fallback_result.get('summary', '')}\n\n"
                issues = fallback_result.get("issues", [])
                if issues:
                    message += "**Issues Found:**\n"
                    for issue in issues:
                        message += f"- {issue.get('description')} (Severity: {issue.get('severity')})\n"

                # 元のエラーも残しておく
                message += f"\n\n(Alloy Error: {last_error[:200]}...)"
                print(f"  Fallback Result: {status}")

        elif "error" in result:
            status = "ERROR"
            message = result.get("error", "Unknown error")
            if result.get("stderr"):
                message += f"\n詳細: {result.get('stderr', '')[:500]}"
            # If we retried, note that
            if last_error:
                message = f"[{MAX_RETRIES}回リトライ後も失敗] " + message
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
                "category": vp.get("category", ""),
                "status": status,
                "message": message,
                "trace": trace,
                "file": str(als_path),
                "alloy_code": alloy_code,
            }
        )

    # 5. Generate Final Report with LLM Analysis
    print("\nStep 4: Generating Analysis Report...")

    # Load analysis prompt template
    prompt_analyze_tmpl = load_text(PROMPT_ANALYZE_RESULTS)

    # Generate detailed analysis for each viewpoint
    detailed_analyses = []
    for res in results_summary:
        if res["status"] in ["VIOLATION_FOUND", "ERROR"]:
            print(f"  Analyzing {res['id']}...")
            prompt_analyze = (
                prompt_analyze_tmpl.replace(
                    "{{requirement_text}}", req_text[:5000]
                )  # Truncate for token limit
                .replace("{{viewpoint_name}}", res["name"])
                .replace("{{viewpoint_description}}", res["description"])
                .replace("{{alloy_code}}", res["alloy_code"][:3000])  # Truncate
                .replace("{{result_status}}", res["status"])
                .replace("{{result_message}}", res["message"])
                .replace(
                    "{{result_trace}}", json.dumps(res["trace"], ensure_ascii=False)
                )
            )
            analysis = gateway.call_llm_text(prompt_analyze)
            detailed_analyses.append(
                {"id": res["id"], "name": res["name"], "analysis": analysis}
            )

    # Build Report
    report_content = generate_final_report(results_summary, detailed_analyses, req_text)

    report_path = project_root / "poc" / "analysis_report.md"
    save_text(report_path, report_content)
    print(f"Report saved to {report_path}")


def generate_final_report(results: list, analyses: list, req_text: str) -> str:
    """簡潔で読みやすいレポートを生成"""
    from datetime import datetime

    report = "# AGV要件検証レポート\n\n"
    report += f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    # Summary counts
    passed = sum(1 for r in results if r["status"] == "PASSED")
    violations = sum(1 for r in results if r["status"] == "VIOLATION_FOUND")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    unknown = sum(1 for r in results if r["status"] == "UNKNOWN")
    total = len(results)

    # Executive Summary (簡潔に)
    report += "## エグゼクティブサマリー\n\n"
    if violations > 0:
        report += f"> [!WARNING]\n> **{violations}件の要件違反**が検出されました。詳細を確認してください。\n\n"
    elif errors > 0:
        report += f"> [!CAUTION]\n> **{errors}件の検証エラー**が発生しました。Alloyモデルの修正が必要です。\n\n"
    else:
        report += "> [!NOTE]\n> すべての検証が正常に完了しました。\n\n"

    # Compact Summary Table
    report += f"| 結果 | 件数 | 割合 |\n"
    report += f"| :--- | :---: | :---: |\n"
    if passed > 0:
        report += f"| ✅ 合格 | {passed} | {passed*100//total}% |\n"
    if violations > 0:
        report += f"| ⚠️ 問題検出 | {violations} | {violations*100//total}% |\n"
    if errors > 0:
        report += f"| ❌ エラー | {errors} | {errors*100//total}% |\n"
    if unknown > 0:
        report += f"| ❓ 不明 | {unknown} | {unknown*100//total}% |\n"
    report += f"| **合計** | **{total}** | 100% |\n\n"

    # Status icon mapping
    status_icons = {
        "PASSED": "✅",
        "VIOLATION_FOUND": "⚠️",
        "ERROR": "❌",
        "UNKNOWN": "❓",
    }

    # Results Table (コンパクト)
    report += "---\n\n## 検証結果一覧\n\n"
    report += "| ID | 観点 | 結果 |\n"
    report += "| :--- | :--- | :---: |\n"
    for res in results:
        icon = status_icons.get(res["status"], "❓")
        report += f"| {res['id']} | {res['name']} | {icon} |\n"
    report += "\n"

    # 問題があった観点のみ詳細表示
    problem_results = [
        r for r in results if r["status"] in ["VIOLATION_FOUND", "ERROR"]
    ]

    if problem_results:
        report += "---\n\n## 検出された問題\n\n"

        for res in problem_results:
            icon = status_icons.get(res["status"], "❓")
            report += f"### {icon} {res['id']}: {res['name']}\n\n"
            report += f"**結果**: {res['status']}\n\n"
            report += f"{res['description']}\n\n"

            # エラーメッセージを簡潔に
            if res["message"] and res["status"] == "ERROR":
                # エラーメッセージの最初の2行だけ表示
                error_lines = res["message"].split("\n")[:3]
                report += f"**エラー概要**:\n```\n{chr(10).join(error_lines)}\n```\n\n"

    # 詳細分析レポート（LLM生成内容をそのまま表示）
    # ユーザー要望：「問題点の概要、検証内容、結果、原因の考察、改善案」を含める
    if analyses:
        report += "---\n\n## 詳細分析レポート\n\n"
        for analysis in analyses:
            # 分析テキストをそのまま表示（Markdown形式）
            report += analysis["analysis"] + "\n\n"
            report += "---\n\n"

    # フッター
    report += "---\n\n"
    report += (
        "*詳細なAlloyモデルは `poc/intermediates/` フォルダを参照してください。*\n"
    )

    return report


if __name__ == "__main__":
    main()
