# 詳細設計書: インターフェースアダプター (Interface Adapters)

## 1. 概要
Interface Adapters層は、外部（UI, DB, Webなど）と内部（Use Cases, Entities）の相互変換を行う。入力データをUse Caseが理解できる形式に変換し、Use Caseからの出力データをUIやDBが扱いやすい形式に変換する。

## 2. Controllers (入力アダプター)

### 2.1 `StreamlitController`
Streamlit UIからのイベントを受け取り、適切なUse Caseを実行する。

#### メソッド
- `on_dashboard_load(query_params: Dict) -> None`
    - アプリ起動時の初期処理。URLパラメータに応じたプロジェクト読み込みなど。
- `on_project_create_submit(name: str, path: str) -> None`
    - プロジェクト作成ボタン押下時のハンドラ。
    - `ManageProjectUseCase.create_project` を呼び出し、成功したらセッション状態を更新してリロードを促す。
- `on_analyze_click(project_id: ProjectId) -> None`
    - 解析実行ボタン押下時のハンドラ。
    - 長時間処理になるため、`st.spinner` 等でUIをブロックしつつ、`AnalyzeRequirementsUseCase.execute` を呼び出す。
    - 進捗表示用のコールバックインスタンスを生成して渡す。

## 3. Presenters (出力アダプター)

### 3.1 `ResultPresenter`
`AnalysisResult` エンティティを受け取り、UI表示用のViewModel（または特定のライブラリ形式）に変換する。

#### メソッド
- `present_graph(graph: RequirementGraph) -> Dict[str, Any]`
    - `streamlit-agraph` または `pyvis` などで使用可能なConfig辞書（Nodes, Edgesリスト）を作成する。
    - 役割に応じてノードの色分け（Condition=黄色, Actor=青など）を行うスタイリングロジックをここに集約する。
    - **フィルタリング**: ノード数が閾値（例: 50）を超える場合、重要度（PageRankや次数中心性）の低いノードをデフォルトで非表示にするフラグを含める。UI側でのスライダー操作等により動的に変更可能な構造とする。
- `present_defects(defects: List[Defect]) -> pandas.DataFrame`
    - 検出された欠陥リストを、`st.dataframe` で表示しやすいPandas DataFrame形式に変換する。
    - 重要度順にソートしたり、フィルタリング用のカラムを追加する。
- `present_metrics(metrics: Dict[str, float]) -> Dict[str, str]`
    - 数値をフォーマット済み文字列（例: "123 nodes", "95.5%"）に変換する。

## 4. Gateways & Repositories (データアクセス/外部接続)

ここでは「インターフェースの実装」としてのロジックを記述する。具体的なライブラリ呼び出し（SQL発行、HTTPリクエストなど）は、さらに外側のFrameworks層のドライバを利用する形になるが、Pythonコードとしてはここに集約されることが多い。

### 4.1 `FileProjectRepository` (impl of ProjectRepository)
ローカルファイルシステムを使用してプロジェクト情報を管理する実装。

#### 責務
- インメモリの `Project` オブジェクトと、ディスク上のYAML/JSONファイルの相互変換。
- ディレクトリトラバーサルによるファイルリストアップ。

#### メソッド詳細
- `save(project: Project)`:
    - `project.yaml` に設定情報をダンプする。
- `save_result(project_id: ProjectId, result: AnalysisResult)`:
    - 結果を `projects/{id}/reports/{timestamp}/result.json` に保存する。
    - 循環参照を避けるため、カスタムエンコーダーを用いてJSON化する。

### 4.2 `LLMGatewayImpl` (impl of LLMGateway)
LLMプロバイダ（Google AI, OpenAI）への接続を抽象化する。

#### 責務
- プロンプトの構築（Prompt Engineering）。
- LLM APIの呼び出しとレスポンスのパース。
- エラーハンドリング（レートリミット時のWaitなど）。

#### メソッド詳細
- `extract_structure(text: str) -> Dict`:
    - **Prompt**: 「以下の要件定義書の一部を読み、ノードとエッジの関係をJSONリストで出力せよ...」
    - 出力フォーマットを強制するため、`response_format="json_object"` (OpenAI) や `Structured Output` (Gemini) 機能を利用する。
- `verify_condition_exhaustiveness(condition, outgoing_paths) -> Dict`:
    - **Prompt**: 「条件『{condition}』に対して、分岐先として『{paths}』が定義されています。これはMECEですか？不足しているケースがあれば列挙してください。」
    
### 4.3 `FileConverter` (File Conversion Gateway)
非Markdown形式のファイルをMarkdownテキストに変換するアダプター。

#### 責務
- `.xlsx`, `.docx`, `.pdf` などのバイナリフォーマットを読み込む。
- テキスト情報、表構造などを可能な限り保ったままMarkdown形式に変換する。
- 変換不可の要素（画像など）は代替テキストに置き換えるか削除する。

#### メソッド詳細
- `convert(file_path: str) -> str`:
    - 拡張子でライブラリを分岐:
        - PDF: `pypdf`, `pdfminer` 等を使用。
        - Excel: `pandas`, `openpyxl` を使用し、表をMarkdown Tableに変換。
        - Word: `python-docx` を使用。
    - エラー時は `FileConversionError` を送出する。

## 5. DTO (Data Transfer Objects)

層間のデータ受け渡しに使用する単純なデータクラス。

- `AnalysisViewModel`: Presenterが作成しViewが消費する表示データセット。
- `ProjectSummary`: プロジェクト一覧表示用の軽量オブジェクト。

