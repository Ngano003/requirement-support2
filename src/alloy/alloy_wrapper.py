import subprocess
import json
import os
import shutil
import tempfile
from typing import Dict, Any, Optional

# 設定: Java環境へのパス
# src/alloy/alloy_wrapper.py -> src/alloy -> src -> root
WORKSPACE_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
JAVA_BIN = os.path.join(
    WORKSPACE_ROOT, "java_runtime", "jdk-17.0.17+10", "bin", "java.exe"
)
ALLOY_JAR = os.path.join(
    WORKSPACE_ROOT, "alloy", "app", "org.alloytools.alloy.dist.jar"
)


def run_alloy_check(als_file_path: str) -> Dict[str, Any]:
    """
    指定された .als ファイルをAlloy CLI (exec) で検証し、結果を辞書形式で返す。
    Alloy 6.2+ のCLI機能を使用する。
    """
    if not os.path.exists(als_file_path):
        return {"error": f"File not found: {als_file_path}"}

    # 出力用の一時ディレクトリを作成
    # 実行ごとにクリーンな状態で結果を受け取るため
    output_dir = os.path.join(WORKSPACE_ROOT, "alloy_temp", "cli_output_tmp")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        JAVA_BIN,
        "-Djava.awt.headless=true",  # ヘッドレスモード必須
        "-jar",
        ALLOY_JAR,
        "exec",
        "-t",
        "json",
        "-f",  # 強制上書き
        "-o",
        output_dir,
        als_file_path,
    ]

    try:
        # Javaプロセス実行
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", check=False
        )

        # 標準出力/エラー出力のログ
        # print("--- STDOUT ---\n", result.stdout)
        # print("--- STDERR ---\n", result.stderr)

        if result.returncode != 0:
            # CLI自体がエラーで終了した場合（構文エラーなど）
            return {
                "error": "Alloy CLI execution failed",
                "stderr": result.stderr,
                "stdout": result.stdout,
            }

        # receipt.json の解析
        receipt_path = os.path.join(output_dir, "receipt.json")
        if not os.path.exists(receipt_path):
            return {"error": "receipt.json was not generated", "stderr": result.stderr}

        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt = json.load(f)

        return parse_receipt(receipt)

    except Exception as e:
        return {"error": str(e)}


def parse_receipt(receipt: dict) -> Dict[str, Any]:
    """
    receipt.json から必要な情報を抽出して整形する
    """
    results = []

    commands = receipt.get("commands", {})
    for cmd_name, cmd_data in commands.items():
        # コマンドごとの結果
        cmd_result = {
            "command": cmd_name,
            "status": "UNKNOWN",  # デフォルト
            "trace": {},
        }

        # solutionリストを確認（通常は1つ）
        solutions = cmd_data.get("solution", [])
        if not solutions:
            continue

        # 最初のソリューションを見る
        sol = solutions[0]

        # AlloyのCLIにおいて、checkコマンドで反例が見つかった(SAT)場合は instances が空でない
        # 安全側に倒して instances の有無で判定
        instances = sol.get("instances", [])

        if instances:
            # 反例あり (VIOLATION)
            cmd_result["status"] = "VIOLATION_FOUND"
            cmd_result["message"] = "Counterexample found. The model has a flaw."

            # Skolems (反例の特定要素) を抽出
            # 例: "$NoDeadlock_s": { "data": [["Error$0"]] }
            first_instance = instances[0]
            skolems = first_instance.get("skolems", {})
            trace_info = {}

            for skolem_name, skolem_val in skolems.items():
                # $NoDeadlock_s -> dead_ends のように分かりやすく変換できればベストだが
                # ここでは汎用的にそのまま出す
                data = skolem_val.get("data", [])
                # リストのリストになっているので平坦化 (1-arity前提)
                flat_data = [item[0] for item in data if item]

                # キー名をきれいにする ($NoDeadlock_s -> NoDeadlock_s)
                clean_name = skolem_name.lstrip("$")
                trace_info[clean_name] = flat_data

            cmd_result["trace"] = trace_info

        else:
            # 反例なし (PASSED) または UNSAT
            # checkコマンドならPASSED, runコマンドならUNSAT
            # typeフィールドで判別可能
            cmd_type = cmd_data.get("type", "check")
            if cmd_type == "check":
                cmd_result["status"] = "PASSED"
                cmd_result["message"] = "No counterexample found."
            else:
                cmd_result["status"] = "UNSATISFIABLE"
                cmd_result["message"] = "No instance found."

        results.append(cmd_result)

    return {"file": "parsed_from_receipt", "results": results}


if __name__ == "__main__":
    # テスト実行
    target_file = os.path.join(WORKSPACE_ROOT, "alloy_temp", "dead_end_gate.als")
    print(f"Testing with: {target_file}")

    result = run_alloy_check(target_file)
    print(json.dumps(result, indent=2, ensure_ascii=False))
