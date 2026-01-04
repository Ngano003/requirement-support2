# 詳細設計書: ドメインサービス (Domain Services)

## 1. 概要
ドメインサービスは、複数のエンティティにまたがるロジックや、特定のエンティティに収まらない複雑な計算処理を担当する。本システムでは主に「構造解析」と「意味解析」の2つのサービスを提供する。

## 2. GraphAnalysisService (構造解析)

純粋なグラフ理論に基づき、ネットワーク構造の欠陥を検出するサービス。外部APIやLLMには依存せず、メモリ上の計算のみで完結する。

### 2.1 メソッド詳細

#### `detect_dead_ends(graph: RequirementGraph) -> List[Defect]`
「行き止まり」を検出する。

- **入力**: `RequirementGraph`
- **出力**: `List[Defect]` (Type: `DEAD_END`)
- **アルゴリズム**:
    1. グラフ内の全ノード $n$ についてループ。
    2. $n$ の出次数 (Out-Degree) を確認。
    3. 出次数が 0 かつ、$n$.`type` が `TERMINATOR` ではない場合、欠陥候補とする。
    4. **除外条件**: 
        - プロジェクト全体として意図的に分割されている場合などは考慮が必要だが、現状は厳密に判定する。
    5. `Defect` 生成:
        - `severity`: `HIGH`
        - `description`: "ノード '{content}' は終了ノードではないに行き止まりになっています。"

#### `detect_cycles(graph: RequirementGraph) -> List[Defect]`
「循環参照」を検出する。

- **入力**: `RequirementGraph`
- **出力**: `List[Defect]` (Type: `CYCLE`)
- **アルゴリズム**:
    1. `networkx.simple_cycles(graph.to_networkx())` を使用して、全サイクルを列挙する。
    2. 各サイクル $C = [n_1, n_2, ..., n_k]$ について:
        - 自己ループ ($k=1$ かつ $n_1 \to n_1$) の場合:
            - エッジ属性などを確認し、意図的な待機状態（Polling等）であれば除外するロジックを挟む余地があるが、基本は `MEDIUM` 程度の欠陥とする。
        - 相互ループ ($k > 1$) の場合:
            - 原則として論理的矛盾の可能性が高いため `Defect` とする。
    3. `Defect` 生成:
        - `severity`: `HIGH`
        - `description`: "ノード群 {ids} 間で循環依存が発生しています。処理が完了しない恐れがあります。"

#### `calculate_node_importance(graph: RequirementGraph) -> Dict[NodeId, float]`
ノードの重要度（フィルタリング用）を計算する。

- **入力**: `RequirementGraph`
- **出力**: `Dict[NodeId, float]` (0.0〜1.0)
- **アルゴリズム**:
    1. `networkx.pagerank` を使用してPageRankを算出する。
    2. または、次数中心性 (Degree Centrality) を使用する。
    3. 結果を正規化して返す。このスコアは、UI側での「重要度フィルタ」に使用される。

## 3. SemanticAnalysisService (意味解析)

自然言語の意味内容に踏み込んだ解析を行う。LLMの推論能力を利用するため、`LLMGatewayInterface` に依存する。

### 3.1 依存関係
- `llm_gateway: LLMGatewayInterface` (Constructor Injection)

### 3.2 メソッド詳細

#### `detect_missing_else(graph: RequirementGraph) -> List[Defect]`
条件分岐の網羅性（MECE）を確認する。

- **入力**: `RequirementGraph`
- **出力**: `List[Defect]` (Type: `MISSING_ELSE`)
- **アルゴリズム**:
    1. グラフから `type == CONDITION` であるノード群 $N_{cond}$ を抽出する。
    2. 各 $n \in N_{cond}$ について:
        - $n$ から出るエッジ $E_{out}$ を取得する。
        - エッジラベル（属性）のリスト $L = [e.label \text{ for } e \in E_{out}]$ を作成する。
        - **Gateway呼び出し**: `llm_gateway.verify_condition_exhaustiveness(condition_text=n.content, outgoing_paths=L)`
    3. Gatewayからの応答が「不完全 (Not Exhaustive)」の場合:
        - 欠落しているケース（例: "Noの場合", "異常系"）がレスポンスに含まれていれば、それをsuggestionに含める。
    4. `Defect` 生成:
        - `severity`: 条件の重要度によるが、デフォルトは `MEDIUM`。
        - `description`: "条件 '{content}' に対する分岐が網羅されていません。'{missing_case}' のケースが考慮されていません。"

#### `detect_conflicts(graph: RequirementGraph) -> List[Defect]`
要件間の矛盾を検出する。
*注意: 全組み合わせの比較は $O(N^2)$ となりコストが高いため、関連性の高いノードペアに絞る必要がある。*

- **入力**: `RequirementGraph`
- **出力**: `List[Defect]` (Type: `CONFLICT`)
- **アルゴリズム**:
    1. **ペア選定**:
        - 直接接続されているノードペア（`DEPENDS_ON` 関係）や、共通の親を持つ兄弟ノードなど、矛盾が発生しやすい箇所をヒューリスティックに選定する。
        - または、類似ベクトル検索（Embedding）を用いて意味的に近いが記述が異なるものをピックアップする（将来拡張）。
        - *V1実装*: `CONTRADICTS` エッジが明示的に抽出されている場合は、それをそのまま欠陥として計上する。また、近傍ノード（距離1）についてのみチェックを行う。
    2. 各ペア $(n_a, n_b)$ について:
        - **Gateway呼び出し**: `llm_gateway.check_text_contradiction(text_a=n_a.content, text_b=n_b.content)`
    3. Gatewayからの応答が「矛盾あり (Contradiction)」かつ確信度が高い場合:
        - `Defect` 生成。
        - `severity`: `HIGH` (論理矛盾は深刻)。
        - `description`: "ノード '{a}' と '{b}' の内容が矛盾しています。理由: {reason}"

## 4. エラーハンドリング
- ドメインサービス内での計算エラー（ZeroDivisionなど）は、原則として呼び出し元へ例外を送出し、処理を中断させるか、その項目のみスキップしてログ出力する。
- LLM Gateway呼び出しのエラー（タイムアウト等）は、`SemanticAnalysisService` 内で捕捉し、その項目の解析を「判定不能」としてスキップする（欠陥とはしない）。エラーログは残す。

