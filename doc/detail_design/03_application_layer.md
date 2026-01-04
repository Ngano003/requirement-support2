# 詳細設計書: アプリケーション層 (Use Cases)

## 1. 概要
アプリケーション層（Use Cases）は、システムのユーザー機能を実現するための調整役（Orchestrator）である。UI詳細や外部デバイスの実装には依存せず、EntitiesとInterface Adaptersの間のデータフローを制御する。

## 2. ユースケース詳細 (Use Case Details)

### 2.1 `AnalyzeRequirementsUseCase` (解析実行)

本システムのコア機能であり、ドキュメントの読み込みから解析、結果保存までの一連の流れを担当する。

#### 入力 (Input Data)
- `project_id`: ProjectId
    - 解析対象のプロジェクトID。
- `options`: AnalysisOptions
    - `force_graph_rebuild`: bool (キャッシュを無視してグラフ再構築を行うか)
    - `target_files`: List[str] (特定のファイルのみ解析する場合。指定なしなら全ファイル)

#### 出力 (Output Data)
- `AnalysisResult`: 解析結果オブジェクト。

#### 処理フロー (Main Success Scenario)
1. **プロジェクトロード**:
    - `ProjectRepository.find_by_id(project_id)` を呼び出し、プロジェクト情報を取得する。
    - 存在しない場合は `ProjectNotFoundError` を送出。
2. **ファイル読み込み**:
    - `Project.input_files` にリストされたファイルの生テキストを読み込む。
    - 拡張子 (.xlsx, .docx, .pdf) に応じて、`FileConverter` をリゾルブし、Markdownテキストに変換する。
3. **構造抽出 (Extraction)**:
    - ファイルごとにチャンク分割する。
    - `LLMGateway.extract_structure(chunk_text)` を呼び出し、ノードとエッジのJSONを取得する。
    - 取得したデータを `RequirementNode`, `RequirementEdge` オブジェクトに変換する。
4. **グラフ構築 (Construction)**:
    - 空の `RequirementGraph` を生成する。
    - 抽出されたノードとエッジを追加・統合する（ID重複時のマージ処理を含む）。
5. **構造解析 (Analysis - Structure)**:
    - `GraphAnalysisService` を使用して `DEAD_END`, `CYCLE` などの構造的欠陥を検出する。
6. **意味解析 (Analysis - Semantic)**:
    - `SemanticAnalysisService` を使用して `MISSING_ELSE`, `CONFLICT` などの意味的欠陥を検出する。
    - *パフォーマンス考慮*: 大規模グラフの場合、進捗状況（Progress Callback）を通知しながら実行する。
7. **結果保存**:
    - 現在時刻などで `AnalysisResult` を生成する。
    - `ProjectRepository.save_result(project_id, result)` を呼び出し、結果を保存する。
8. **結果返却**:
    - 呼び出し元へ `AnalysisResult` を返す。

#### 例外ケース (Exception Handling)
- **処理エラー**: ファイル読み込み失敗、解析エラーなど、いずれかの処理で例外が発生した場合は、速やかに処理を中断し、ユーザーにエラーを通知する（All-or-Nothing）。中途半端な解析結果は保存しない。

### 2.2 `ManageProjectUseCase` (プロジェクト管理)

プロジェクトの設定変更、ファイルの追加・削除などを管理する。

#### メソッド: `create_project`
- **入力**: `name` (str), `directory_path` (str)
- **処理**:
    - 新しい `ProjectId` を発行。
    - `Project` インスタンスを生成。
    - 指定ディレクトリ内のサポートファイル（.md, .txt等）を走査し、初期ファイルリストを作成。
    - `ProjectRepository.save(project)` で保存。
- **出力**: `Project`

#### メソッド: `add_files`
- **入力**: `project_id` (ProjectId), `file_paths` (List[str])
- **処理**:
    - Projectを取得。
    - ファイルパスの妥当性チェック。
    - `project.add_file()` を呼び出し。
    - 更新されたProjectを保存。
- **出力**: Updateされた `Project`

#### メソッド: `get_project_history`
- **入力**: `project_id` (ProjectId)
- **処理**:
    - `ProjectRepository` から過去の `AnalysisResult`(のサマリ) リストを取得する。
- **出力**: `List[AnalysisResultSummary]`

## 3. インターフェース定義 (Port Interfaces)

この層が利用する（依存する）インターフェース定義。実装はInterface Adapters層以降で行われる。

### 3.1 `ProjectRepository` (Output Port)
- `save(project: Project) -> None`
- `find_by_id(id: ProjectId) -> Optional[Project]`
- `save_result(project_id: ProjectId, result: AnalysisResult) -> None`
- `list_results(project_id: ProjectId) -> List[AnalysisResultSummary]`

### 3.2 `LLMGateway` (Output Port)
- `extract_structure(text: str) -> StructureDict`
- `verify_condition_exhaustiveness(...)`
- `check_text_contradiction(...)`

### 3.3 `AnalysisProgressCallback` (Output Port)
長時間かかる解析処理の進捗を通知するためのコールバックインターフェース。
- `on_progress(step: str, percentage: int) -> None`
- `on_log(message: str) -> None`

