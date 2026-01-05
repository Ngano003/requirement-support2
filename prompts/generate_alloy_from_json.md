あなたは形式手法Alloyのエキスパートです。
提供された「要件の構造化データ（JSON）」を元に、**指定された一つの検証観点**を検証するためのAlloy 6モデルを生成してください。

## 目標
検証観点: **{{viewpoint_name}}**
説明: {{viewpoint_description}}

この観点を検証するために必要最小限のモデル（State, Resource, Logic）のみ定義し、検証時間を短縮してください。無関係な要素は定義しないでください。

## タスク
1. **必要な要素の定義**:
   - `state_transition` から、この観点に関連する State, Event, Transition を定義。
   - `resource_concurrency` から、この観点に関連する Resource を定義。
   - `logic_guard` から、条件ロジックを定義。

2. **検証式の作成**:
   - 指定された観点に対応する `assert` 文を作成してください。
   - コマンド名は `check VerificationProperty` としてください。

## 特別な指示
- **SafeMode**: デッドロック検証の場合、SafeModeは除外してください。
- **Trace Model**: `ordering` モジュールを使ったTraceモデルを使用してください。
- **識別子**: 英数字のみ使用。

## 入力データ: 構造化データ
{{structure_json}}
