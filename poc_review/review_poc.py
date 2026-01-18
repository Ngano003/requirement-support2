"""
要件定義書レビュー PoC スクリプト

設計書: poc/review_poc_design.md
処理フロー:
  1. Section-wise Split: ドキュメントをセクション分割
  2. 各観点について:
     - Step 1 (Scan): セクション単位で候補抽出
     - Step 2 (Grounding): 全文で引用確認
     - Step 3 (Falsification): 全文で反証
  3. Cross-Reference Check: 欠陥間の関連性分析
"""

import sys
import sys
from datetime import datetime
import re
import json
from pathlib import Path
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.llm_gateway import LLMGatewayImpl


def safe_print(text: str) -> None:
    """Windows cp932互換のための安全なprint関数"""
    try:
        print(text)
    except UnicodeEncodeError:
        # エンコードできない文字を?に置換して出力
        print(text.encode("cp932", errors="replace").decode("cp932"))


class RequirementReviewer:
    """要件定義書レビュアー"""

    VIEWPOINTS = [
        "1_dead_ends",
        "2_missing_else",
        "3_orphan_states",
        "4_conflicting_outputs",
        "5_unstated_side_effects",
    ]

    def __init__(self):
        self.llm = LLMGatewayImpl()
        self.prompts_dir = Path(__file__).parent / "prompts"

    def load_prompt(self, filename: str) -> str:
        """プロンプトファイルを読み込む"""
        path = self.prompts_dir / filename
        return path.read_text(encoding="utf-8")

    def load_viewpoint(self, viewpoint: str) -> str:
        """観点定義ファイルを読み込む"""
        path = self.prompts_dir / "viewpoints" / f"{viewpoint}.md"
        return path.read_text(encoding="utf-8")

    def split_by_heading(
        self, text: str, level: int = 2, chunk_size: int = 300
    ) -> List[Dict[str, str]]:
        """Markdownをセクション分割し、指定行数になるべく近づけるように結合"""
        pattern = r"^(#{" + str(level) + r"})\s+(.+)$"
        raw_sections = []
        current_title = "Introduction"
        current_content = []

        # まず最小単位（見出し）で分割
        for line in text.split("\n"):
            match = re.match(pattern, line)
            if match:
                if current_content:
                    raw_sections.append(
                        {"title": current_title, "content": "\n".join(current_content)}
                    )
                current_title = match.group(2)
                current_content = [line]
            else:
                current_content.append(line)

        if current_content:
            raw_sections.append(
                {"title": current_title, "content": "\n".join(current_content)}
            )

        # 指定サイズになるまで結合
        merged_sections = []
        current_chunk_content = []
        current_chunk_titles = []
        current_chunk_len = 0

        for section in raw_sections:
            section_len = len(section["content"].split("\n"))

            # 最初のセクション、または追加してもサイズ超過しない場合は追加
            if current_chunk_len == 0 or (
                current_chunk_len + section_len <= chunk_size * 1.2
            ):  # 20%のバッファを許容
                current_chunk_content.append(section["content"])
                current_chunk_titles.append(section["title"])
                current_chunk_len += section_len
            else:
                # サイズ超過する場合は現在のチャンクを確定
                merged_sections.append(
                    {
                        "title": " + ".join(current_chunk_titles),
                        "content": "\n\n".join(current_chunk_content),
                    }
                )
                # 新しいチャンクを開始
                current_chunk_content = [section["content"]]
                current_chunk_titles = [section["title"]]
                current_chunk_len = section_len

        # 残りのチャンクを追加
        if current_chunk_content:
            merged_sections.append(
                {
                    "title": " + ".join(current_chunk_titles),
                    "content": "\n\n".join(current_chunk_content),
                }
            )

        return merged_sections

    def step1_scan(self, section_text: str, viewpoint: str) -> List[Dict[str, Any]]:
        """Step 1: 構造抽出と初期レビュー"""
        prompt_template = self.load_prompt("step1_scan.md")
        viewpoint_def = self.load_viewpoint(viewpoint)

        # Few-shot examplesは観点定義に含まれている
        prompt = prompt_template.replace("{viewpoint_definition}", viewpoint_def)
        prompt = prompt.replace(
            "{few_shot_examples}", "（上記の観点定義に含まれています）"
        )
        prompt = prompt.replace("{section_text}", section_text)

        result = self._call_llm(prompt, temperature=0.0)
        if isinstance(result, list):
            return result
        return []

    def step2_grounding(
        self, full_document: str, candidate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 2: 根拠確認"""
        prompt_template = self.load_prompt("step2_grounding.md")

        prompt = prompt_template.replace(
            "{target_text}", candidate.get("target_text", "")
        )
        prompt = prompt.replace("{reason}", candidate.get("reason", ""))
        prompt = prompt.replace("{id}", candidate.get("id", ""))
        prompt = prompt.replace("{full_document}", full_document)

        result = self._call_llm(prompt)
        if isinstance(result, dict):
            return result
        return {"id": candidate.get("id"), "is_grounded": False, "quote": ""}

    def step3_falsification(
        self, full_document: str, candidate: Dict[str, Any], quote: str
    ) -> Dict[str, Any]:
        """Step 3: 反証"""
        prompt_template = self.load_prompt("step3_falsification.md")

        prompt = prompt_template.replace(
            "{target_text}", candidate.get("target_text", "")
        )
        prompt = prompt_template.replace("{reason}", candidate.get("reason", ""))
        prompt = prompt.replace("{quote}", quote)
        prompt = prompt.replace("{id}", candidate.get("id", ""))
        prompt = prompt.replace("{full_document}", full_document)

        result = self._call_llm(prompt)
        if isinstance(result, dict):
            return result
        return {
            "id": candidate.get("id"),
            "is_valid": True,
            "final_reason": candidate.get("reason", ""),
        }

    def cross_reference_check(self, defects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """欠陥間の相互参照分析"""
        if not defects:
            return {
                "groups": [],
                "standalone_defects": [],
                "summary": "欠陥は検出されませんでした。",
            }

        prompt_template = self.load_prompt("step4_cross_reference.md")
        defect_list = json.dumps(defects, ensure_ascii=False, indent=2)
        prompt = prompt_template.replace("{defect_list}", defect_list)

        result = self._call_llm(prompt)
        if isinstance(result, dict):
            return result
        return {
            "groups": [],
            "standalone_defects": [d["id"] for d in defects],
            "summary": "分析できませんでした。",
        }

    def review_viewpoint(
        self, full_document: str, sections: List[Dict[str, str]], viewpoint: str
    ) -> List[Dict[str, Any]]:
        """1つの観点についてレビューを実行"""
        print(f"\n{'='*60}")
        print(f"観点: {viewpoint}")
        print(f"{'='*60}")

        all_candidates = []

        # Step 1: セクション単位でスキャン
        print("\n[Step 1: Scan]")
        for section in sections:
            print(f"  - セクション: {section['title']}")
            candidates = self.step1_scan(section["content"], viewpoint)
            for c in candidates:
                c["section"] = section["title"]
            all_candidates.extend(candidates)

        suspected = [c for c in all_candidates if c.get("status") == "Suspected"]
        print(f"  → 候補数: {len(suspected)}")

        if not suspected:
            return []

        # Step 2: Grounding
        print("\n[Step 2: Grounding]")
        grounded = []
        for candidate in suspected:
            result = self.step2_grounding(full_document, candidate)
            if result.get("is_grounded"):
                candidate["quote"] = result.get("quote", "")
                grounded.append(candidate)
                print(f"  [OK] {candidate['id']}: 根拠確認OK")
            else:
                print(f"  [NG] {candidate['id']}: 根拠なし (破棄)")

        if not grounded:
            return []

        # Step 3: Falsification
        print("\n[Step 3: Falsification]")
        confirmed = []
        for candidate in grounded:
            result = self.step3_falsification(
                full_document, candidate, candidate.get("quote", "")
            )
            if result.get("is_valid"):
                candidate["final_reason"] = result.get(
                    "final_reason", candidate.get("reason", "")
                )
                confirmed.append(candidate)
                print(f"  [OK] {candidate['id']}: 欠陥確定")
            else:
                print(f"  [NG] {candidate['id']}: 反証により無効化")

        return confirmed

    def review_document(self, document_path: str) -> Dict[str, Any]:
        """ドキュメント全体をレビュー"""
        print(f"\n{'#'*60}")
        print(f"# 要件定義書レビュー開始")
        print(f"# 対象: {document_path}")
        print(f"{'#'*60}")

        # ドキュメント読み込み
        full_document = Path(document_path).read_text(encoding="utf-8")

        # セクション分割
        sections = self.split_by_heading(full_document, level=2)
        print(f"\nセクション数: {len(sections)}")
        for s in sections:
            print(f"  - {s['title']}")

        # 各観点でレビュー
        all_defects = []
        for viewpoint in self.VIEWPOINTS:
            defects = self.review_viewpoint(full_document, sections, viewpoint)
            for d in defects:
                d["viewpoint"] = viewpoint
            all_defects.extend(defects)

        # Cross-Reference Check
        print(f"\n{'='*60}")
        print("Cross-Reference Check")
        print(f"{'='*60}")
        cross_ref = self.cross_reference_check(all_defects)

        return {
            "total_defects": len(all_defects),
            "defects": all_defects,
            "cross_reference": cross_ref,
        }

    def _call_llm(self, prompt: str, temperature: float = None) -> Any:
        """LLMを呼び出してJSON結果を取得"""
        try:
            response_text = self.llm._call_llm_generic(prompt, temperature=temperature)
            return self.llm._extract_json_block(response_text)
        except Exception as e:
            print(f"  [ERROR] LLM呼び出しエラー: {e}")
            return {}


class ReviewReporter:
    """レビュー結果からレポートを生成するクラス"""

    def generate_report(self, result: Dict[str, Any], output_path: str) -> None:
        """JSON結果からMarkdownレポートを生成"""

        lines = []
        lines.append("# 要件定義書レビュー結果レポート")
        lines.append(f"\n**実施日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**総検出数**: {result.get('total_defects', 0)}件")

        # サマリー
        cross_ref = result.get("cross_reference", {})
        if "summary" in cross_ref:
            lines.append("\n## 1. 全体サマリー")
            lines.append(cross_ref["summary"])

        # 観点別集計
        lines.append("\n## 2. 観点別検出状況")
        defects = result.get("defects", [])
        viewpoint_counts = {}
        for d in defects:
            vp = d.get("viewpoint", "unknown")
            viewpoint_counts[vp] = viewpoint_counts.get(vp, 0) + 1

        lines.append("| 観点 | 検出数 |")
        lines.append("|---|---|")
        for vp, count in viewpoint_counts.items():
            vp_name = vp.replace("_", " ").title()
            lines.append(f"| {vp_name} | {count} |")

        # 検出された主な欠陥（クロスリファレンスグループ）
        if "groups" in cross_ref and cross_ref["groups"]:
            lines.append("\n## 3. 主要な欠陥グループ (根本原因分析)")
            for group in cross_ref["groups"]:
                lines.append(f"\n### グループ {group.get('group_id')}")
                lines.append(f"- **根本原因**: {group.get('root_cause')}")
                lines.append(f"- **推奨対策**: {group.get('recommendation')}")
                lines.append(
                    f"- **関連する指摘ID**: {', '.join(group.get('defect_ids', []))}"
                )

        # 詳細リスト
        lines.append("\n## 4. 検出された詳細欠陥リスト")

        # 観点ごとにグルーピングして表示
        defects_by_vp = {}
        for d in defects:
            vp = d.get("viewpoint", "unknown")
            if vp not in defects_by_vp:
                defects_by_vp[vp] = []
            defects_by_vp[vp].append(d)

        for vp, items in defects_by_vp.items():
            vp_name = vp.replace("_", " ").title()
            lines.append(f"\n### {vp_name}")
            for item in items:
                lines.append(
                    f"\n#### [{item.get('id', 'NoID')}] {item.get('target_text', '')[:30]}..."
                )
                lines.append(f"- **理由**: {item.get('reason')}")
                if item.get("final_reason"):
                    lines.append(f"- **詳細分析**: {item.get('final_reason')}")
                lines.append(
                    f"- **引用**: \n> {item.get('quote', '').replace(chr(10), ' ')}"
                )

        # ファイル出力
        path = Path(output_path)
        path.write_text("\n".join(lines), encoding="utf-8")


def main():
    """メイン関数"""

    # 引数でJSONファイルが指定された場合はレポート生成のみ実行
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
        if json_path.exists() and json_path.suffix == ".json":
            print(f"JSONファイルからレポートを生成します: {json_path}")
            try:
                result = json.loads(json_path.read_text(encoding="utf-8"))
                reporter = ReviewReporter()
                report_path = json_path.parent / "review_report.md"
                reporter.generate_report(result, str(report_path))
                print(f"レポート生成完了: {report_path}")
                return
            except Exception as e:
                print(f"エラー: レポート生成に失敗しました。 {e}")
                return

    reviewer = RequirementReviewer()

    # サンプル要件定義書をレビュー
    sample_path = project_root / "requirements" / "agv_system_with_defects.md"
    result = reviewer.review_document(str(sample_path))

    # 結果出力
    print(f"\n{'#'*60}")
    print("# レビュー結果サマリー")
    print(f"{'#'*60}")
    print(f"\n検出された欠陥数: {result['total_defects']}")

    if result["defects"]:
        print("\n## 検出された欠陥一覧")
        for i, defect in enumerate(result["defects"], 1):
            print(f"\n### [{i}] {defect.get('viewpoint', 'unknown')}")
            print(f"- セクション: {defect.get('section', 'unknown')}")
            safe_print(f"- 対象: {defect.get('target_text', '')[:50]}...")
            safe_print(
                f"- 理由: {defect.get('final_reason', defect.get('reason', ''))}"
            )

    if result["cross_reference"].get("summary"):
        print(f"\n## 相互参照分析")
        safe_print(result["cross_reference"]["summary"])

    # JSONとしても出力
    output_path = project_root / "poc" / "review_result.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n詳細結果: {output_path}")

    # レポート生成
    reporter = ReviewReporter()
    report_path = project_root / "poc" / "review_report.md"
    reporter.generate_report(result, str(report_path))
    print(f"レポート生成: {report_path}")


if __name__ == "__main__":
    main()
