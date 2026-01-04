# 詳細設計書: ドメインモデル (Domain Model)

## 1. 概要
本ドキュメントでは、システムの中心となる重要概念（Entities, Value Objects）の詳細設計を定義する。これらのルールは外部のフレームワークやUIに依存せず、常に整合性を保つ必要がある。

## 2. 共通型定義 (Common Types)

### 2.1 Value Objects (識別子)
文字列の誤用を防ぐため、NewTypeを使用する。

- **`ProjectId`**: プロジェクトを一意に識別するID。
  - 実装: `NewType('ProjectId', str)`
  - 制約: ファイルシステム上で安全な文字列であること。
- **`NodeId`**: 要求ノードを一意に識別するID。
  - 実装: `NewType('NodeId', str)`
  - 生成規則: コンテンツのハッシュ値、または連番（インポート時に決定）。

### 2.2 Enums (列挙型)
システムの振る舞いを決定する定数セット。

#### `NodeType`
ノードの役割を分類する。
- `ACTOR`: アクター（ユーザー、システム等）。
- `ACTION`: アクション（動作、処理）。
- `CONDITION`: 条件（分岐点）。
- `TERMINATOR`: 終了点（ゴール、完了）。
- *備考*: 将来的に `OBJECT` (対象物) を追加する可能性があるが、初期リリースでは上記4つとする。

#### `EdgeType`
ノード間の関係性を定義する。
- `DEPENDS_ON`: 順序依存関係 (A -> B)。Aが完了後にBが可能。
- `CONTRADICTS`: 矛盾関係 (A <-> B)。AとBは両立しない。
- `REFINES`: 具体化関係 (A -|> B)。BはAの詳細化である。

#### `DefectType`
検出される欠陥の種類。
- `DEAD_END`: 行き止まり。完了していないのに次のステップがない。
- `CYCLE`: 循環参照。処理が終わらないループ。
- `MISSING_ELSE`: 条件漏れ。条件分岐の網羅性が不十分。
- `CONFLICT`: 矛盾。要件間で定義が衝突している。

#### `Severity`
欠陥の重大度。
- `HIGH`: 修正必須（論理破綻）。
- `MEDIUM`: 推奨修正（あいまいさ、保守性低下）。
- `LOW`: 参考情報（スタイル、軽微な指摘）。

## 3. エンティティ詳細 (Entity Details)

### 3.1 `Project` (Aggregate Root)
プロジェクトは解析のコンテキストを保持し、設定と入力ファイルを管理する。

#### 属性 (Attributes)
| 属性名 | 型 | 説明 |
| :--- | :--- | :--- |
| `id` | `ProjectId` | 一意な識別子。 |
| `name` | `str` | プロジェクト名（表示用）。 |
| `created_at` | `datetime` | 作成日時。 |
| `config` | `ProjectConfig` | 解析設定（除外設定など）。 |
| `input_files` | `List[str]` | 解析対象となるファイルパスのリスト。プロジェクトルートからの相対パスで管理。 |

#### メソッド (Methods)
- `add_file(path: str) -> None`: 解析対象ファイルを追加する。重複チェックを行う。
- `remove_file(path: str) -> None`: 解析対象ファイルを除外する。
- `update_config(config: ProjectConfig) -> None`: 設定を更新する。

### 3.2 `RequirementNode`
要件定義書から抽出された、最小単位の意味ブロック。

#### 属性 (Attributes)
| 属性名 | 型 | 説明 |
| :--- | :--- | :--- |
| `id` | `NodeId` | 一意な識別子。 |
| `content` | `str` | 要件のテキスト本文。 |
| `type` | `NodeType` | ノードの種類。 |
| `source_file` | `str` | 出典ファイル名。 |
| `line_number` | `int` | 出典ファイルの行番号（トレーサビリティ用）。 |
| `metadata` | `Dict[str, Any]` | 将来の拡張用（例: 担当者、優先度）。 |

#### 制約
- `content` は空であってはならない。
- `type` は必須。不明な場合はAIによる推論結果またはデフォルト値を用いるが、基本は確定させる。

### 3.3 `RequirementEdge`
ノード間の有向リンク。

#### 属性 (Attributes)
| 属性名 | 型 | 説明 |
| :--- | :--- | :--- |
| `source_id` | `NodeId` | 始点ノードID。 |
| `target_id` | `NodeId` | 終点ノードID。 |
| `type` | `EdgeType` | 関係性の種類。 |
| `attributes` | `Dict[str, Any]` | エッジ属性（例: "Yes"/"No" などの分岐ラベル）。 |

#### 制約
- 自己ループ（source == target）は、データ構造上は許可されるが、Cycle検出ロジックで欠陥として扱われる可能性がある。

### 3.4 `RequirementGraph`
`RequirementNode` と `RequirementEdge` の集合体であり、グラフ操作のドメインロジックを提供する。

#### 属性 (Attributes)
| 属性名 | 型 | 説明 |
| :--- | :--- | :--- |
| `nodes` | `Dict[NodeId, RequirementNode]` | IDをキーとしたノード辞書。 |
| `edges` | `List[RequirementEdge]` | エッジのリスト。 |

#### メソッド (Methods)
- `add_node(node: RequirementNode) -> None`
  - 既に同じIDが存在する場合は、後勝ちで更新するか、マージ戦略に従う（Use Case層で制御）。ここでは単純登録とする。
- `add_edge(edge: RequirementEdge) -> None`
  - 存在しないノードIDを指定したエッジの追加は、`ValueError` を送出する。
- `get_outgoing_edges(node_id: NodeId) -> List[RequirementEdge]`
  - 指定ノードから出るエッジを取得する。
- `get_incoming_edges(node_id: NodeId) -> List[RequirementEdge]`
  - 指定ノードへ入るエッジを取得する。
- `get_orphans() -> List[RequirementNode]`
  - 入出力エッジを持たない孤立ノードを取得する。
- `to_networkx() -> nx.DiGraph`
  - 解析ライブラリ `NetworkX` 形式へ変換するヘルパーメソッド。
  - ノード属性として `type`, `content`などを保持させる。

### 3.5 `Defect` (Value Object)
システムが検出した「要件の不備」。

#### 属性 (Attributes)
| 属性名 | 型 | 説明 |
| :--- | :--- | :--- |
| `type` | `DefectType` | 欠陥の種類。 |
| `severity` | `Severity` | 重大度。 |
| `related_node_ids` | `List[NodeId]` | 欠陥に関連するノード群（例: サイクルを構成するノード全て）。 |
| `description` | `str` | ユーザー向けの説明文。 |
| `suggestion` | `Optional[str]` | 修正提案（AI生成または定型文）。 |

### 3.6 `AnalysisResult`
1回の解析実行の成果物全体を表す。

#### 属性 (Attributes)
| 属性名 | 型 | 説明 |
| :--- | :--- | :--- |
| `project_id` | `ProjectId` | 対象プロジェクト。 |
| `timestamp` | `datetime` | 実行完了時刻。 |
| `graph` | `RequirementGraph` | 構築されたグラフモデル。 |
| `defects` | `List[Defect]` | 検出された欠陥リスト。 |
| `metrics` | `Dict[str, float]` | 統計情報（ノード数、複雑度など）。 |

#### メソッド
- `has_critical_defects() -> bool`
  - HIGHレベルの欠陥が含まれているか判定する。

## 4. データのライフサイクル
1. **生成**: `AnalyzeRequirementsUseCase` 内で、LLMからの出力をパースして `RequirementNode/Edge` が生成される。
2. **加工**: `RequirementGraph` に集約され、結合処理が行われる。
3. **検査**: Domain Service (`GraphAnalysisService` 等) に渡され、`Defect` が生成される。
4. **保存**: `AnalysisResult` として集約され、Repository経由でJSON等にシリアライズされ永続化される。
