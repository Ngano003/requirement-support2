# Alloy連携機能 実装まとめ

## 1. 目的
Python製の要件定義支援アプリケーションから、形式手法ツール「Alloy Analyzer」を利用し、**デッドロック**や**孤立状態**などの構造的欠陥を自動検出する機能を構築すること。

## 2. 最終アーキテクチャ
検討の結果、独自のJavaランナーなどを介さず、Alloy 6標準のCLI機能を直接呼び出す最もシンプルな構成を採用しました。

### 構成要素
- **Pythonラッパー**: `alloy_wrapper.py`
  - アプリケーションからのインターフェース。
  - AlloyのJARをサブプロセスとして実行し、結果のJSONを解析してPython辞書として返します。
- **Alloy JAR**: `alloy/app/org.alloytools.alloy.dist.jar`
  - 検証エンジンの本体。
- **Java Runtime**: `java_runtime/`
  - ユーザー環境に依存しないポータブルな実行環境。

### ファイル構成
```
alloy_temp/
  ├── alloy/            # Alloy本体
  ├── java_runtime/     # OpenJDK
  ├── alloy_wrapper.py  # 連携用モジュール
  └── alloy_summary.md  # 本ドキュメント
```

## 3. 使い方
`alloy_wrapper.py` の `run_alloy_check` 関数に、検証したい `.als` ファイルのパスを渡します。

```python
from alloy_temp.alloy_wrapper import run_alloy_check

result = run_alloy_check("path/to/model.als")

if result.get("status") == "VIOLATION_FOUND":
    print("欠陥が見つかりました")
    trace = result.get("trace", {})
    # 例: trace['NoDeadlock_s'] -> ["Error$0"]
```

## 4. 検討の経緯 (History)

### Phase 1: Javaランナーの自作試行 (`AlloyRunner.java`)
当初はAlloyにCLI機能がないと想定し、Alloy APIを叩いてJSONを出力するJavaプログラム `AlloyRunner.java` を開発しました。
- **成果**: 検証結果のJSON化、反例データ（Trace）の抽出ロジック実装。
- **課題**: 独自のJavaソースコードを維持管理・コンパイルする手間が発生する。

### Phase 2: XML出力とPython解析の検討
Java側での複雑な解析を避け、Alloy標準のXMLエクスポート機能を利用しようと試みました。
- **成果**: XML出力には成功したが、Python側でのXMLパース処理の実装コストが残る。

### Phase 3: 標準CLI (`exec` command) の採用
Alloy 6以降には隠れた強力なCLI機能 `exec` があることが判明しました。
- **決定**: `AlloyRunner.java` を廃止。標準CLIで `receipt.json` を生成させ、それをPythonで読む構成に一本化。
- **メリット**: Javaコードレスで、最もメンテナンス性が高くシンプルな構成となった。

## 5. 参考: 汎用検証テンプレート (`common_checks.als`)
削除されたファイルに含まれていた、汎用的な検証用アサーションの定義です。必要に応じて `.als` ファイルにコピーして使用してください。

```alloy
module common_checks

/* 1. デッドロック（行き止まり）チェック */
pred NoDeadlockTemplate[nodes: set State, edges: State->State] {
    all x: nodes | some x.edges
}

/* 2. 決定性（分岐なし）チェック */
pred DeterministicTemplate[nodes: set State, edges: State->State] {
    all x: nodes | lone x.edges
}
```
