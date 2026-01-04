# 詳細設計書: インフラストラクチャ & UI (Frameworks & Drivers)

## 1. 概要
最外層であるインフラストラクチャ層では、特定の技術スタック（Streamlit, LLM SDK, File System）に依存した詳細な実装仕様を定義する。ここに記述される内容は、ライブラリのバージョンアップ等により最も変更を受けやすい。

## 2. ユーザーインターフェース (Streamlit Impl)

`app.py` をエントリーポイントとし、Streamlitのコンポーネントシステムを利用してUIを構築する。

### 2.1 画面レイアウト詳細

#### サイドバー (Sidebar)
- **Project Selection**: `st.selectbox`
    - 既存のプロジェクトフォルダを選択するドロップダウン。
    - 「新規作成...」オプションを含む。
- **File Management**: `st.expander`
    - 現在の対象ファイルリストを表示 (`st.checkbox` 付きで除外可能)。
    - 新規ファイルアップロード: `st.file_uploader` (accepts: .md, .txt, .pdf, .xlsx, .docx)。
    - **Note**: GUI上でのファイル内容編集機能は提供しない。編集が必要な場合はローカルで編集して再アップロードする。
- **Action**:
    - "Start Analyze" ボタン (Primary Action)。

#### メインエリア (Main Area)
アコーディオンやタブを用いて情報を整理する。

1. **Dashboard / Summary** (Top)
    - 最新の解析結果サマリ（Card表示）。
    - 欠陥数、ノード数、最終更新日時。
    - **"実行 (Analyze)" ボタン**: 目立つ位置に配置。

2. **Visualization Tab**
    - `streamlit-agraph` コンポーネントを使用。
    - **Config**:
        - `physics`: true (物理演算あり) / false (固定配置)
        - `directed`: true
        - `nodeHighlightBehavior`: true
    - **Interaction**:
        - ノードクリックでサイドパネル/モーダルに詳細情報を表示（Streamlitの制限上、クリックイベントを受け取り `st.session_state` を更新して再描画するフローになる可能性がある）。

3. **Defects & Details Tab**
    - `st.dataframe` または `st.table` で欠陥リストを表示。
    - フィルタリング機能: `st.multiselect` でSeverityやTypeによる絞り込み。
    - 各行に「詳細」ボタン、またはExpandable row（ライブラリ機能次第）。

4. **Raw Data / Logs Tab**
    - デバッグ用。JSON生データや、LLMとの通信ログを表示。

### 2.2 セッション状態管理 (Session State)
Streamlit特有の `st.session_state` を用いて、リクエストをまたぐデータを保持する。

- `current_project_id`: 選択中のプロジェクトID。
- `analysis_result`: 最新の解析結果オブジェクト（再描画のたびにロードしないようキャッシュ）。
- `graph_config`: グラフ表示の現在の設定（ズームレベル等は保持できないことが多いが、物理演算ON/OFF等は保持）。

## 3. データ永続化詳細 (Persistence Impl)

### 3.1 ディレクトリ構造
```
/project_root
  ├── .rs_config/          # システム用隠しディレクトリ (任意)
  ├── project.yaml         # プロジェクト設定ファイル
  └── reports/
      ├── 20231027_100000/
      │   ├── result.json  # 解析結果本体
      │   └── debug.log    # 実行ログ
      └── ...
```

### 3.2 ファイルフォーマット

#### `project.yaml`
```yaml
id: "prj_001"
name: "OrderSystem Requirement"
created_at: "2023-10-27T10:00:00"
config:
  exclude_patterns: ["*.bak", "temp/*"]
input_files:
  - "doc/requirements.md"
  - "doc/api_spec.md"
```

#### `result.json`
Pydanticの `.model_dump_json()` をベースにするが、可読性のためインデント付きで保存する。
Enum値は文字列として保存される。

## 4. LLM SDK 利用詳細

### 4.1 使用ライブラリ
- **Google Generative AI SDK** (`google-generativeai`)
    - モデル: `gemini-1.5-pro` (複雑な推論), `gemini-1.5-flash` (高速抽出)
    - 設定: `generation_config` でJSON出力を強制する。

- **OpenAI Utils** (Optional)
    - ユーザーがKeyを持っている場合のフォールバック。

### 4.2 APIキー管理
- 環境変数 `GOOGLE_API_KEY` (または `OPENAI_API_KEY`) から読み込む。
- `.env` ファイルのロードには `python-dotenv` を使用する。

## 5. ロギングとエラー監視
- 標準ライブラリ `logging` を使用。
- ログレベル:
    - `INFO`: 操作履歴、解析開始/終了。
    - `DEBUG`: LLMへのプロンプト内容、生レスポンス（機密情報に注意）。
    - `ERROR`: スタックトレースを含む例外情報。
- ログファイルは `logs/app.log` にローテーション付きで出力する。
